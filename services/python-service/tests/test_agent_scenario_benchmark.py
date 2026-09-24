"""Evaluator unit tests. The real benchmark never uses these fixture responses."""

import json
from collections import Counter
from pathlib import Path

from app.agent.diagnosis import parse_final_diagnosis
from app.agent.planner import TaskPlanner
from app.agent.tools import build_tool_registry
from app.domain.models import to_dict
from app.evaluation.agent_scenario_benchmark import evaluate_scenario, summarize
from app.evaluation.scenario_models import REPETITION_IDS, SCENARIOS
from app.repository.index import AnalysisIndex


def test_eight_real_scenarios_and_repetition_selection() -> None:
    assert len(SCENARIOS) == 8
    assert dict(Counter(item.task_type_expected for item in SCENARIOS)) == {
        "RUNTIME_ERROR": 2, "BUSINESS_LOGIC_ERROR": 2,
        "CALL_CHAIN_ANALYSIS": 2, "CONFIGURATION_ERROR": 2,
    }
    assert len(REPETITION_IDS) == 4
    assert all((Path(__file__).parents[3] / item.repository_path).is_dir() for item in SCENARIOS)
    assert "runtime-python-login" in REPETITION_IDS  # config is unsupported


def price_response() -> dict:
    scenario = next(item for item in SCENARIOS if item.id == "business-price")
    index = AnalysisIndex().analyze(Path(__file__).parents[3] / scenario.repository_path)
    target = next(symbol for symbol in index.symbols.values() if symbol.name == "calculatePrice")
    registry = build_tool_registry(index)
    trace = []
    for number, (name, args) in enumerate([
        ("searchSymbol", {"name": "calculatePrice"}),
        ("findCallers", {"symbolId": target.id}),
        ("readFile", {"filePath": "src/PriceService.java"}),
        ("readFile", {"filePath": "src/OrderService.java"}),
    ], 1):
        result = registry.execute(name, args)
        trace.append({"step": number, "tool": name, "input": args, "success": result.success,
                      "observation": to_dict(result.observationModel)})
    plan = TaskPlanner().plan(scenario.user_query)
    raw = json.dumps({
        "issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格表达式",
        "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"},
        "root_cause": "当前实现与预期规则可能不符。",
        "evidence": [
            {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice",
             "code": "return price + quantity * discount;", "reason": "源码"},
            {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder",
             "code": "return priceService.calculatePrice(100, 3);", "reason": "源码"},
        ],
        "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"],
        "fix_suggestion": "核对业务规则后修改。", "uncertainty": "没有正确公式需求。",
    }, ensure_ascii=False)
    return {"status": "COMPLETED", "provider": "ollama:qwen2.5-coder:14b:json-tool-compat",
            "plan": plan.as_dict(), "trace": trace, **parse_final_diagnosis(raw, plan, trace)}


def test_evaluator_scores_grounded_response_and_detects_unverified_claim() -> None:
    scenario = next(item for item in SCENARIOS if item.id == "business-price")
    response = price_response()
    result = evaluate_scenario(scenario, response)
    assert result["final_status"] == "PASS"
    assert result["evidence_grounding_pass"] and result["expected_evidence_pass"]
    response["finalDiagnosis"]["root_cause"] = "正确公式一定是 price * quantity * discount"
    result = evaluate_scenario(scenario, response)
    assert result["final_status"] == "FAIL"
    assert any("禁用断言" in issue for issue in result["unsupported_claims"])


def test_evaluator_distinguishes_unsupported_config_from_failure() -> None:
    scenario = next(item for item in SCENARIOS if item.id == "config-database-url")
    response = {"status": "COMPLETED", "provider": "ollama:qwen2.5-coder:14b:json-tool-compat",
                "plan": TaskPlanner().plan(scenario.user_query).as_dict(), "trace": [],
                "diagnosisStatus": "UNSUPPORTED", "finalDiagnosis": None,
                "userMessage": "当前工具链无法读取配置文件。"}
    result = evaluate_scenario(scenario, response)
    assert result["final_status"] == "UNSUPPORTED"
    response["status"] = "MAX_STEPS"
    assert evaluate_scenario(scenario, response)["final_status"] == "UNSUPPORTED"
    response["status"] = "UNSUPPORTED"
    assert evaluate_scenario(scenario, response)["final_status"] == "UNSUPPORTED"
    response["userMessage"] = None
    assert evaluate_scenario(scenario, response)["final_status"] == "FAIL"


def test_summary_counts_all_baselines_but_retains_repeat_errors() -> None:
    result = evaluate_scenario(next(item for item in SCENARIOS if item.id == "business-price"), price_response())
    result["run_group"] = "baseline"
    repeated = dict(result, run_group="repeat", http_error="HTTP 502")
    summary = summarize([result, repeated])
    assert summary["scenario_count"] == 1
    assert summary["total_agent_calls"] == 2
    assert summary["ollama_error"] == 1


def test_target_detection_accepts_observed_package_qualified_symbol() -> None:
    scenario = next(item for item in SCENARIOS if item.id == "runtime-inventory-npe")
    response = {"status": "MAX_STEPS", "provider": "ollama:qwen2.5-coder:14b",
                "plan": TaskPlanner().plan(scenario.user_query).as_dict(),
                "trace": [{"step": 1, "tool": "searchSymbol", "success": True,
                           "observation": {"data": [{"qualifiedName": "demo.order.InventoryService.checkStock",
                                                     "name": "checkStock"}]}}]}
    assert evaluate_scenario(scenario, response)["target_found"] is True
