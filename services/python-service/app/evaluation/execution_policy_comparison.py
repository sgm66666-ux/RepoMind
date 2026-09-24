"""Read-only before/after comparison over saved real API responses."""

import json
from collections import Counter

from app.agent.execution_policy import AgentExecutionState
from app.agent.planner import ExecutionPlan


def result_metrics(result: dict) -> dict:
    response = result.get("full_response") or {}
    plan_data = response.get("plan") or result.get("execution_plan")
    plan = ExecutionPlan(**plan_data) if isinstance(plan_data, dict) and plan_data else None
    state = AgentExecutionState(result.get("user_query") or "", plan)
    trace = response.get("trace") or []
    duplicate_attempts = executed_no_progress = actual_executions = 0
    for step in trace:
        tool, arguments = step.get("tool"), step.get("input") or {}
        if not isinstance(tool, str):
            continue
        if state.already_called(tool, arguments):
            duplicate_attempts += 1
        if step.get("toolExecuted") is False:
            state.record_duplicate(tool, arguments, step.get("step") or 0)
            continue
        actual_executions += 1
        progress, _ = state.observe(tool, arguments, step.get("observation") or {}, step.get("step") or 0)
        if not progress:
            executed_no_progress += 1
    diagnosis = response.get("finalDiagnosis")
    issues = response.get("diagnosisIssues") or []
    return {
        "steps": len(trace), "actual_tool_executions": actual_executions,
        "duplicate_attempts": duplicate_attempts,
        "no_progress_calls": state.no_progress_calls,
        "executed_no_progress_calls": executed_no_progress,
        "max_steps_hit": response.get("status") == "MAX_STEPS",
        "observation_completion": state.completion_decision(),
        "complete_final_call_chain": bool(diagnosis and diagnosis.get("issue_type") == "CALL_CHAIN_ANALYSIS" and
                                          result.get("call_chain_pass") and len(diagnosis.get("call_chain") or []) >= 2 and
                                          not any("调用链含有" in issue for issue in issues)),
        "invalid_call_edges": sum("调用链含有" in issue for issue in issues),
        "valid_final_diagnosis": bool(diagnosis and result.get("diagnosis_valid")),
        "evidence_grounding_pass": bool(result.get("evidence_grounding_pass")),
        "unsupported": result.get("final_status") == "UNSUPPORTED",
    }


def aggregate_metrics(results: list[dict]) -> dict:
    metrics = [result_metrics(item) for item in results]
    count = len(metrics)
    return {
        "runs": count,
        "average_tool_steps": round(sum(item["steps"] for item in metrics) / count, 2) if count else 0,
        "actual_tool_executions": sum(item["actual_tool_executions"] for item in metrics),
        "duplicate_attempts": sum(item["duplicate_attempts"] for item in metrics),
        "no_progress_calls": sum(item["no_progress_calls"] for item in metrics),
        "executed_no_progress_calls": sum(item["executed_no_progress_calls"] for item in metrics),
        "max_steps_hits": sum(item["max_steps_hit"] for item in metrics),
        "complete_observation_checklists": sum(item["observation_completion"] == "COMPLETE" for item in metrics),
        "partial_observation_checklists": sum(item["observation_completion"] == "PARTIAL" for item in metrics),
        "complete_final_call_chains": sum(item["complete_final_call_chain"] for item in metrics),
        "unsupported_tasks": sum(item["unsupported"] for item in metrics),
        "invalid_call_edges": sum(item["invalid_call_edges"] for item in metrics),
        "valid_final_diagnosis": sum(item["valid_final_diagnosis"] for item in metrics),
        "evidence_grounding_pass": sum(item["evidence_grounding_pass"] for item in metrics),
        "status_counts": dict(Counter(item["final_status"] for item in results)),
    }


def build_comparison(before_report: dict, after_report: dict) -> dict:
    old = {item["scenario_id"]: item for item in before_report["results"]
           if item.get("run_group") == "baseline"}
    new = {item["scenario_id"]: item for item in after_report["results"]
           if item.get("run_group") == "baseline"}
    scenarios = []
    for scenario_id, current in new.items():
        previous = old.get(scenario_id)
        if not previous:
            continue
        scenarios.append({
            "scenario_id": scenario_id,
            "previous_status": previous["final_status"], "new_status": current["final_status"],
            "previous_tool_trace": previous["tools_used"], "new_tool_trace": current["tools_used"],
            "previous_steps": len(previous["tools_used"]), "new_steps": len(current["tools_used"]),
            "evidence_before": previous.get("evidence_found"), "evidence_after": current.get("evidence_found"),
            "previous_metrics": result_metrics(previous), "new_metrics": result_metrics(current),
            "duplicate_calls": result_metrics(current)["duplicate_attempts"],
            "no_progress_events": (current.get("full_response") or {}).get("executionState", {}).get("policy_events", []),
            "final_diagnosis": current.get("final_diagnosis"),
            "unsupported_claims": current.get("unsupported_claims"),
            "notes": current.get("notes"),
        })
    old_baseline = [item for item in before_report["results"] if item.get("run_group") == "baseline"]
    new_baseline = [item for item in after_report["results"] if item.get("run_group") == "baseline"]
    return {"baseline_before": aggregate_metrics(old_baseline), "baseline_after": aggregate_metrics(new_baseline),
            "all_runs_before": aggregate_metrics(before_report["results"]),
            "all_runs_after": aggregate_metrics(after_report["results"]),
            "scenarios": scenarios}


def render_comparison(comparison: dict) -> str:
    lines = ["## 冻结 Baseline vs Execution Policy", "",
             "以下 BEFORE 来自原始保存的真实 API 报告；AFTER 来自本轮真实 API 报告。比较时重放 Observation 计算进展，未重跑或改写旧响应。",
             "", "### 总体指标（8 个基线场景）", "",
             "| 指标 | BEFORE | AFTER |", "|---|---:|---:|"]
    before, after = comparison["baseline_before"], comparison["baseline_after"]
    for key in ("average_tool_steps", "duplicate_attempts", "no_progress_calls", "executed_no_progress_calls",
                "max_steps_hits", "complete_observation_checklists", "partial_observation_checklists",
                "complete_final_call_chains", "unsupported_tasks", "invalid_call_edges",
                "valid_final_diagnosis", "evidence_grounding_pass"):
        lines.append(f"| {key} | {before[key]} | {after[key]} |")
    lines.extend(["", "### 逐场景变化", ""])
    for item in comparison["scenarios"]:
        lines.extend([f"#### {item['scenario_id']} · {item['previous_status']} → {item['new_status']}", "",
                      f"- Tool Trace：`{' → '.join(item['previous_tool_trace']) or '无'}` → "
                      f"`{' → '.join(item['new_tool_trace']) or '无'}`",
                      f"- 步数：{item['previous_steps']} → {item['new_steps']}；重复调用："
                      f"{item['previous_metrics']['duplicate_attempts']} → {item['new_metrics']['duplicate_attempts']}；"
                      f"无进展：{item['previous_metrics']['no_progress_calls']} → {item['new_metrics']['no_progress_calls']}。",
                      f"- Evidence Before：`{json.dumps(item['evidence_before'], ensure_ascii=False)}`",
                      f"- Evidence After：`{json.dumps(item['evidence_after'], ensure_ascii=False)}`",
                      f"- No-progress / Policy Events：`{json.dumps(item['no_progress_events'], ensure_ascii=False)}`",
                      f"- FinalDiagnosis：`{json.dumps(item['final_diagnosis'], ensure_ascii=False)}`",
                      f"- Unsupported Claims / 校验问题：`{json.dumps(item['unsupported_claims'], ensure_ascii=False)}`",
                      f"- 备注：{item['notes']}", ""])
    return "\n".join(lines)
