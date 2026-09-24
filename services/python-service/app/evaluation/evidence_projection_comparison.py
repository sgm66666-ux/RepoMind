"""Read-only evidence/projection comparison of saved real API responses."""

import json
from collections import Counter

from app.agent.evidence import VerifiedEvidenceStore, normalize_source_code
from app.agent.execution_policy import AgentExecutionState, query_symbol_hints
from app.agent.planner import ExecutionPlan


def evidence_metrics(result: dict) -> dict:
    response = result.get("full_response") or {}
    plan_data = response.get("plan") or result.get("execution_plan")
    plan = ExecutionPlan(**plan_data) if isinstance(plan_data, dict) and plan_data else None
    state = AgentExecutionState(result.get("user_query") or "", plan)
    for step in response.get("trace") or []:
        if step.get("toolExecuted") is False:
            continue
        state.observe(step.get("tool"), step.get("input") or {}, step.get("observation") or {},
                      step.get("step") or 0)
    store: VerifiedEvidenceStore = state.evidence_store
    expected = result.get("evidence_found") or []
    observed_snippets = sum(any(fact.file == item.get("file") and
                                normalize_source_code(item.get("code") or "") in normalize_source_code(fact.code)
                                for fact in store.source_lines.values()) for item in expected)
    projected_expected = sum(bool(item.get("in_diagnosis")) for item in expected)
    flow = state.runtime_facts() if plan and plan.task_type == "RUNTIME_ERROR" else None
    complete_runtime = bool(flow and all(flow.get(key) for key in
                                         ("assignment", "invalid_value_origin", "trigger_operation",
                                          "source_to_usage_linkage")))
    hints = query_symbol_hints(state.question)
    path = store.call_path(hints[0], hints[-1]) if plan and plan.task_type == "CALL_CHAIN_ANALYSIS" and len(hints) >= 2 else []
    diagnosis = response.get("finalDiagnosis") or {}
    final_chain = diagnosis.get("call_chain") or []
    complete_chain = bool(path and len(path) == len(final_chain) and all(
        (match := store.resolve_symbol(name)) is not None and match.symbol_id == symbol.symbol_id
        for name, symbol in zip(final_chain, path)))
    issues = response.get("diagnosisIssues") or []
    return {
        "verified_symbols": len(store.symbols), "verified_source_lines": len(store.source_lines),
        "verified_call_edges": len(store.edges),
        "observed_expected_snippets": observed_snippets,
        "projected_expected_evidence": projected_expected,
        "expected_evidence_total": len(expected),
        "data_flow_chain": flow,
        "complete_runtime_evidence": complete_runtime,
        "verified_call_path": [store.canonical_name(symbol.symbol_id) for symbol in path],
        "complete_final_call_chain": complete_chain,
        "canonical_symbols": [{"raw": symbol.raw_name, "canonical": store.canonical_name(symbol.symbol_id),
                               "signature": symbol.signature, "id": symbol.symbol_id}
                              for symbol in store.symbols.values()],
        "model_claim": (response.get("evidenceProjection") or {}).get("modelClaim"),
        "system_corrected_result": (response.get("evidenceProjection") or {}).get("systemResult"),
        "projected_fact_count": (response.get("evidenceProjection") or {}).get("systemResult", {}).get("projected_fact_count", 0),
        # Count affected runs, not duplicated parser/projection diagnostics for one claim.
        "symbol_mismatch": int(any("MODEL_SYMBOL_MISMATCH" in issue or "定位 Symbol 未见" in issue
                                   for issue in issues)),
        "line_mismatch": int(any("MODEL_LINE_MISMATCH" in issue or "行号" in issue for issue in issues)),
        "unsupported_claims": int(any(any(marker in issue for marker in (
            "证据未见于", "调用链含有", "模型声称确定", "EVIDENCE_NOT_FOUND",
            "UNSUPPORTED_CLAIM_REMOVED", "禁用断言")) for issue in issues)),
        "diagnosis_issues": issues,
        "valid_final_diagnosis": bool(result.get("diagnosis_valid")),
        "evidence_grounding": bool(result.get("evidence_grounding_pass")),
    }


def aggregate(results: list[dict]) -> dict:
    metrics = [evidence_metrics(result) for result in results]
    return {"runs": len(results), "valid_final_diagnosis": sum(item["valid_final_diagnosis"] for item in metrics),
            "evidence_grounding": sum(item["evidence_grounding"] for item in metrics),
            "complete_runtime_evidence": sum(item["complete_runtime_evidence"] for item in metrics),
            "complete_final_call_chains": sum(item["complete_final_call_chain"] for item in metrics),
            "observed_expected_snippets": sum(item["observed_expected_snippets"] for item in metrics),
            "projected_expected_evidence": sum(item["projected_expected_evidence"] for item in metrics),
            "projected_fact_count": sum(item["projected_fact_count"] for item in metrics),
            "symbol_mismatch": sum(item["symbol_mismatch"] for item in metrics),
            "line_mismatch": sum(item["line_mismatch"] for item in metrics),
            "unsupported_claims": sum(item["unsupported_claims"] for item in metrics),
            "status_counts": dict(Counter(result.get("final_status") for result in results))}


def compare_evidence(before: dict, after: dict) -> dict:
    old = {item["scenario_id"]: item for item in before["results"] if item.get("run_group") == "baseline"}
    new = {item["scenario_id"]: item for item in after["results"] if item.get("run_group") == "baseline"}
    rows = []
    for scenario_id, current in new.items():
        previous = old.get(scenario_id)
        if not previous:
            continue
        rows.append({"scenario_id": scenario_id,
                     "previous_status": previous["final_status"], "new_status": current["final_status"],
                     "previous_tool_trace": previous.get("tool_trace"), "new_tool_trace": current.get("tool_trace"),
                     "before": evidence_metrics(previous), "after": evidence_metrics(current),
                     "previous_final_diagnosis": previous.get("final_diagnosis"),
                     "new_final_diagnosis": current.get("final_diagnosis"),
                     "new_evidence_found": current.get("evidence_found"),
                     "previous_evidence_found": previous.get("evidence_found"),
                     "diagnosis_issues": (current.get("full_response") or {}).get("diagnosisIssues") or []})
    old_baseline = [item for item in before["results"] if item.get("run_group") == "baseline"]
    new_baseline = [item for item in after["results"] if item.get("run_group") == "baseline"]
    return {"baseline_before": aggregate(old_baseline), "baseline_after": aggregate(new_baseline),
            "all_runs_before": aggregate(before["results"]),
            "all_runs_after": aggregate(after["results"]), "scenarios": rows}


def render_evidence_comparison(comparison: dict) -> str:
    lines = ["## Verified Evidence / Projection 对比（冻结 v2 → 本轮）", "",
             "旧结果仅从已保存的真实 Trace 重放 Observation；不重跑模型，也不把期望答案送入 Agent。",
             "`observed_expected_snippets` 统计真实源码行中逐字出现的评测片段；"
             "`projected_expected_evidence` 仍按最终诊断的完整代码文本比较，二者不可混同。"
             "Symbol/Line mismatch 与 unsupported_claims 按受影响运行数统计，不把同一问题的中英文诊断重复计数。", "",
             "| 指标 | v2 | 本轮 |", "|---|---:|---:|"]
    old, new = comparison["baseline_before"], comparison["baseline_after"]
    for key in ("valid_final_diagnosis", "evidence_grounding", "complete_runtime_evidence",
                "complete_final_call_chains", "observed_expected_snippets", "projected_expected_evidence",
                "projected_fact_count", "symbol_mismatch", "line_mismatch", "unsupported_claims"):
        lines.append(f"| {key} | {old[key]} | {new[key]} |")
    lines.extend(["", "### 每个基线场景", ""])
    for row in comparison["scenarios"]:
        before, after = row["before"], row["after"]
        lines.extend([f"#### {row['scenario_id']} · {row['previous_status']} → {row['new_status']}", "",
                      f"- 旧 Trace：`{' → '.join(item['tool'] for item in row['previous_tool_trace']) or '无'}`",
                      f"- 新 Trace：`{' → '.join(item['tool'] for item in row['new_tool_trace']) or '无'}`",
                      f"- Verified Evidence Before：`{json.dumps(row['previous_evidence_found'], ensure_ascii=False)}`",
                      f"- Verified Evidence After：`{json.dumps(row['new_evidence_found'], ensure_ascii=False)}`",
                      f"- Data-flow Chain Before：`{json.dumps(before['data_flow_chain'], ensure_ascii=False)}`",
                      f"- Data-flow Chain After：`{json.dumps(after['data_flow_chain'], ensure_ascii=False)}`",
                      f"- Canonical Symbols：`{json.dumps(after['canonical_symbols'], ensure_ascii=False)}`",
                      f"- Verified Call Chain / Projection：`{json.dumps(after['verified_call_path'], ensure_ascii=False)}` / "
                      f"`{json.dumps((row['new_final_diagnosis'] or {}).get('call_chain'), ensure_ascii=False)}`",
                      f"- Model Claim：`{json.dumps(after['model_claim'], ensure_ascii=False)}`",
                      f"- System Corrected Result：`{json.dumps(after['system_corrected_result'], ensure_ascii=False)}`",
                      f"- Diagnosis Issues：`{json.dumps(row['diagnosis_issues'], ensure_ascii=False)}`",
                      f"- FinalDiagnosis：`{json.dumps(row['new_final_diagnosis'], ensure_ascii=False)}`", ""])
    return "\n".join(lines)
