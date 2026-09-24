from app.agent.planner import TaskPlanner
from app.evaluation.execution_policy_comparison import aggregate_metrics, build_comparison, result_metrics


def sample_result(block_second: bool) -> dict:
    plan = TaskPlanner().plan("为什么UserService.login出现TypeError？").as_dict()
    first = {"step": 1, "tool": "searchSymbol", "input": {"name": "login", "language": "JAVA"},
             "success": True, "observation": {"success": True, "data": []}}
    second = {"step": 2, "tool": "searchSymbol", "input": {"name": "login", "language": "JAVA"},
              "success": not block_second, "toolExecuted": not block_second,
              "observation": {"success": not block_second, "data": [] if not block_second else None}}
    return {"scenario_id": "runtime-python-login", "run_group": "baseline", "user_query":
            "为什么UserService.login出现TypeError？", "final_status": "FAIL", "tools_used": ["searchSymbol"] * 2,
            "evidence_found": [], "diagnosis_valid": False, "evidence_grounding_pass": False,
            "call_chain_pass": False, "unsupported_claims": [], "final_diagnosis": None, "notes": "test",
            "full_response": {"plan": plan, "trace": [first, second], "status": "NO_PROGRESS" if block_second else "MAX_STEPS",
                              "diagnosisIssues": []}}


def test_metrics_distinguish_duplicate_execution_from_policy_block() -> None:
    old = result_metrics(sample_result(False))
    new = result_metrics(sample_result(True))
    assert old["duplicate_attempts"] == new["duplicate_attempts"] == 1
    assert old["actual_tool_executions"] == 2
    assert new["actual_tool_executions"] == 1
    assert old["max_steps_hit"] and not new["max_steps_hit"]
    assert aggregate_metrics([sample_result(False), sample_result(True)])["average_tool_steps"] == 2


def test_before_after_comparison_keeps_each_saved_result_separate() -> None:
    before = {"results": [sample_result(False)]}
    after = {"results": [sample_result(True)]}
    comparison = build_comparison(before, after)
    assert comparison["baseline_before"]["max_steps_hits"] == 1
    assert comparison["baseline_after"]["max_steps_hits"] == 0
    assert comparison["scenarios"][0]["previous_status"] == "FAIL"
    assert comparison["scenarios"][0]["new_metrics"]["actual_tool_executions"] == 1
