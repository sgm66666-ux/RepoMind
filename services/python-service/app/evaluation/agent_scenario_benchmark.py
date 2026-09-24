"""Score actual FastAPI Agent responses; expected evidence is never sent to the model."""

import json
from collections import Counter

from app.agent.diagnosis import FinalDiagnosis, validate_evidence_against_trace
from app.agent.evidence import VerifiedEvidenceStore, normalize_source_code
from app.evaluation.scenario_models import AgentScenario


def evaluate_scenario(scenario: AgentScenario, response: dict | None, error: str | None = None) -> dict:
    response = response or {}
    trace = response.get("trace") or []
    verified_store = VerifiedEvidenceStore()
    for step in trace:
        verified_store.ingest(step.get("tool"), step.get("input") or {}, step.get("observation") or {},
                              step.get("step") or 0)
    plan = response.get("plan") or {}
    diagnosis = response.get("finalDiagnosis")
    tools = [step.get("tool") for step in trace]
    observed_symbols = [symbol for step in trace if step.get("success") and step.get("tool") == "searchSymbol"
                        for symbol in (step.get("observation", {}).get("data") or []) if isinstance(symbol, dict)]
    target_found = any(symbol.get("qualifiedName") == scenario.expected_target or
                       str(symbol.get("qualifiedName") or "").endswith("." + scenario.expected_target) or
                       symbol.get("name") == scenario.expected_target for symbol in observed_symbols)
    actual_evidence = diagnosis.get("evidence", []) if isinstance(diagnosis, dict) else []
    grounded, grounding_issues = validate_evidence_against_trace(actual_evidence, trace)
    evidence_grounding_pass = bool(actual_evidence) and len(grounded) == len(actual_evidence) and not grounding_issues
    evidence_found = [
        {"file": expected.file, "code": expected.code,
         "in_trace": any(step.get("success") and step.get("tool") == "readFile" and
                         step.get("observation", {}).get("data", {}).get("filePath") == expected.file and
                         expected.code in step.get("observation", {}).get("data", {}).get("content", "")
                         for step in trace),
         "in_diagnosis": any(item.get("file") == expected.file and isinstance(item.get("code"), str) and
                             normalize_source_code(item["code"]) == normalize_source_code(expected.code)
                             for item in actual_evidence)}
        for expected in scenario.expected_evidence
    ]
    unsupported_claims = list(grounding_issues)
    unsupported_claims.extend(response.get("diagnosisIssues") or [])
    if diagnosis:
        public_text = " ".join(str(diagnosis.get(key, "")) for key in
                               ("summary", "root_cause", "fix_suggestion", "uncertainty"))
        unsupported_claims.extend(f"禁用断言出现于用户诊断：{phrase}" for phrase in scenario.forbidden_conclusions
                                  if phrase in public_text)
    else:
        public_text = str(response.get("userMessage") or "")
    try:
        diagnosis_valid = diagnosis is not None and FinalDiagnosis.model_validate(diagnosis) is not None
    except Exception:
        diagnosis_valid = False
    user_output_valid = bool(public_text.strip()) and not public_text.lstrip().startswith(("{", "```"))
    planner_pass = plan.get("task_type") == scenario.task_type_expected
    real_provider = str(response.get("provider") or "").startswith("ollama:qwen2.5-coder:14b")
    tool_family_pass = all(name in tools for name in scenario.expected_tool_family)
    chain = diagnosis.get("call_chain") if diagnosis else []
    chain_pass = not scenario.expected_call_chain or (
        len(chain) == len(scenario.expected_call_chain) and all(
            actual == expected or (
                (actual_symbol := verified_store.resolve_symbol(actual)) is not None and
                (expected_symbol := verified_store.resolve_symbol(expected)) is not None and
                actual_symbol.symbol_id == expected_symbol.symbol_id)
            for actual, expected in zip(chain, scenario.expected_call_chain)))
    expected_evidence_pass = bool(evidence_found) and all(item["in_diagnosis"] for item in evidence_found)
    is_config = scenario.task_type_expected == "CONFIGURATION_ERROR"
    declared_unsupported = response.get("diagnosisStatus") in {"UNSUPPORTED", "INSUFFICIENT_EVIDENCE"}
    error_text = (error or "").lower()
    error_flags = {
        "http_502": "http 502" in error_text,
        "empty_response": "neither a tool call nor a final answer" in error_text or "empty response" in error_text,
        "invalid_json": response.get("diagnosisStatus") == "INVALID_FORMAT" or "invalid json" in error_text,
        "tool_call_parse_error": "tool call" in error_text or "tool arguments" in error_text,
    }
    if error or not planner_pass or not real_provider:
        status = "FAIL"
    elif is_config:
        status = "UNSUPPORTED" if (declared_unsupported and not diagnosis and user_output_valid and
                                   response.get("status") in {"COMPLETED", "MAX_STEPS", "UNSUPPORTED"}) else "FAIL"
    elif response.get("status") != "COMPLETED":
        status = "FAIL"
    elif (diagnosis_valid and evidence_grounding_pass and expected_evidence_pass and target_found and
          tool_family_pass and chain_pass and not unsupported_claims and user_output_valid):
        status = "PASS"
    elif diagnosis_valid and evidence_grounding_pass and user_output_valid and not any(
        issue.startswith("禁用断言") for issue in unsupported_claims):
        status = "PARTIAL"
    else:
        status = "FAIL"
    return {
        "scenario_id": scenario.id, "user_query": scenario.user_query,
        "repository_path": scenario.repository_path, "expected_target": scenario.expected_target,
        "target_found": target_found,
        "planner_expected": scenario.task_type_expected, "planner_actual": plan.get("task_type"),
        "planner_pass": planner_pass, "execution_plan": plan,
        "tools_used": tools, "tool_trace": [{"step": step.get("step"), "tool": step.get("tool"),
                                      "input": step.get("input"), "success": step.get("success"),
                                      "error": step.get("error"), "progress": step.get("progress"),
                                      "policy_status": step.get("policyStatus"),
                                      "tool_executed": step.get("toolExecuted", True)} for step in trace],
        "tool_family_expected": list(scenario.expected_tool_family), "tool_family_pass": tool_family_pass,
        "evidence_found": evidence_found, "evidence_grounding_pass": evidence_grounding_pass,
        "expected_evidence_pass": expected_evidence_pass, "call_chain_expected": list(scenario.expected_call_chain),
        "call_chain_actual": chain, "call_chain_pass": chain_pass,
        "canonical_symbols": [{"raw": symbol.raw_name, "canonical": verified_store.canonical_name(symbol.symbol_id),
                                "id": symbol.symbol_id} for symbol in verified_store.symbols.values()],
        "unsupported_claims": unsupported_claims, "diagnosis_valid": diagnosis_valid,
        "diagnosis_status": response.get("diagnosisStatus"), "user_output_valid": user_output_valid,
        "final_diagnosis": diagnosis, "user_message": response.get("userMessage"),
        "agent_status": response.get("status"), "provider": response.get("provider"),
        "real_provider": real_provider,
        "http_error": error, "raw_model_output": response.get("rawModelOutput"),
        "error_flags": error_flags,
        "full_response": response, "final_status": status, "notes": scenario.notes,
    }


def summarize(results: list[dict]) -> dict:
    baseline = [item for item in results if item.get("run_group") == "baseline"]
    return {
        "scenario_count": len(baseline),
        "task_type_counts": dict(Counter(item["planner_expected"] for item in baseline)),
        "planner_pass": sum(item["planner_pass"] for item in baseline),
        "evidence_grounding_pass": sum(item["evidence_grounding_pass"] for item in baseline),
        "valid_final_diagnosis": sum(item["diagnosis_valid"] for item in baseline),
        "status_counts": dict(Counter(item["final_status"] for item in baseline)),
        "ollama_error": sum(bool(item["http_error"]) or item["diagnosis_status"] == "INVALID_FORMAT"
                            for item in results),
        "total_agent_calls": len(results),
    }


def render_markdown(report: dict) -> str:
    summary = report["summary"]
    lines = ["# RepoMind 真实 Ollama Agent Scenario Benchmark", "",
             f"生成时间：{report['generated_at']}。FastAPI Agent API：`{report['api_base_url']}`；模型：`{report['model']}`。",
             "", "说明：8 个基线场景及代表场景的重复运行均调用真实 API；期望仅用于事后评估，未注入 Prompt。",
             "配置场景当前工具链不支持 YAML/properties 读取及关联，UNSUPPORTED 不是成功定位。", "",
             "## 总体", "",
             f"基线场景 {summary['scenario_count']}；实际 Agent 调用 {summary['total_agent_calls']}；"
             f"Planner 通过 {summary['planner_pass']}；Evidence Grounding 通过 {summary['evidence_grounding_pass']}；"
             f"有效 FinalDiagnosis {summary['valid_final_diagnosis']}；Ollama/格式错误 {summary['ollama_error']}。", "",
             f"任务类型：{json.dumps(summary['task_type_counts'], ensure_ascii=False)}。",
             f"状态：{json.dumps(summary['status_counts'], ensure_ascii=False)}。", "",
             "## 逐场景真实结果", ""]
    for result in report["results"]:
        lines.extend([f"### {result['scenario_id']} · {result['run_group']} #{result['run_index']} · {result['final_status']}", "",
                      f"- 问题：{result['user_query']}",
                      f"- Planner：期望 `{result['planner_expected']}`；实际 `{result['planner_actual']}`；"
                      f"{'通过' if result['planner_pass'] else '失败'}。",
                      f"- Plan：`{json.dumps(result['execution_plan'], ensure_ascii=False)}`",
                      f"- Tool Trace：`{' → '.join(result['tools_used']) or '无'}`",
                      f"- 目标 Symbol：`{result['expected_target']}`；"
                      f"{'已由 searchSymbol 确认' if result['target_found'] else '未由 searchSymbol 确认'}。",
                      f"- 工具族：期望 `{', '.join(result['tool_family_expected'])}`；"
                      f"{'覆盖' if result['tool_family_pass'] else '未覆盖'}。",
                      f"- 证据：{json.dumps(result['evidence_found'], ensure_ascii=False)}",
                      f"- FinalDiagnosis：{json.dumps(result['final_diagnosis'], ensure_ascii=False)}",
                      f"- 不支持/校验问题：{json.dumps(result['unsupported_claims'], ensure_ascii=False)}",
                      f"- Agent 状态：`{result['agent_status']}`；诊断状态：`{result['diagnosis_status']}`；"
                      f"用户提示：{result['user_message'] or '无'}。",
                      f"- 错误：{result['http_error'] or '无'}；"
                      f"类别：`{json.dumps(result['error_flags'], ensure_ascii=False)}`。备注：{result['notes']}", ""])
    return "\n".join(lines)
