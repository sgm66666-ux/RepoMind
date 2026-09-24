import json
from pathlib import Path

from app.agent.diagnosis import parse_final_diagnosis, validate_evidence_against_trace
from app.agent.planner import TaskPlanner
from app.agent.tools import build_tool_registry
from app.domain.models import to_dict
from app.repository.index import AnalysisIndex


def price_trace() -> list[dict]:
    index = AnalysisIndex().analyze(Path(__file__).parents[3] / "demo" / "repomind-agent-test-demo" / "logic-bug-demo")
    target = next(symbol for symbol in index.symbols.values() if symbol.name == "calculatePrice")
    registry = build_tool_registry(index)
    trace = []
    for number, (tool, arguments) in enumerate([
        ("searchSymbol", {"name": "calculatePrice"}),
        ("findCallers", {"symbolId": target.id}),
        ("readFile", {"filePath": "src/OrderService.java", "startLine": 1, "endLine": 8}),
        ("readFile", {"filePath": "src/PriceService.java", "startLine": 1, "endLine": 9}),
    ], 1):
        result = registry.execute(tool, arguments)
        trace.append({"step": number, "tool": tool, "success": result.success,
                      "observation": to_dict(result.observationModel)})
    return trace


def price_diagnosis() -> dict:
    return {
        "issue_type": "BUSINESS_LOGIC_ERROR",
        "summary": "已定位订单价格计算实现，结果是否错误仍需业务规则确认",
        "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"},
        "root_cause": "当前计算将 price 与 quantity * discount 相加，可能不符合预期。",
        "evidence": [{"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice",
                      "code": "return price + quantity * discount;", "reason": "当前源码表达式"}],
        "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"],
        "fix_suggestion": "先核对订单计价规则，再修改表达式。",
        "uncertainty": "仓库中未提供正确公式的业务需求。",
    }


def parse(value: dict | str, trace: list[dict] | None = None) -> dict:
    raw = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return parse_final_diagnosis(raw, TaskPlanner().plan("为什么订单价格计算错误？"), trace or price_trace())


def test_schema_parses_and_binds_source_and_call_relation() -> None:
    result = parse(price_diagnosis())
    assert result["diagnosisStatus"] == "VALID"
    diagnosis = result["finalDiagnosis"]
    assert diagnosis["issue_type"] == "BUSINESS_LOGIC_ERROR"
    assert diagnosis["location"] == {"file": "src/PriceService.java", "line": 8,
                                      "symbol": "PriceService.calculatePrice"}
    assert diagnosis["evidence"][0]["source_tool"] == "readFile"
    assert diagnosis["evidence"][0]["kind"] == "FACT"
    assert diagnosis["call_chain"] == ["OrderService.createOrder", "PriceService.calculatePrice"]
    assert diagnosis["root_cause_kind"] == "INFERENCE"


def test_null_evidence_and_location_lines_stay_null() -> None:
    value = price_diagnosis()
    value["location"]["line"] = None
    value["evidence"][0]["line"] = None
    result = parse(value)
    assert result["diagnosisStatus"] == "VALID"
    assert result["finalDiagnosis"]["location"]["line"] is None
    assert result["finalDiagnosis"]["evidence"][0]["line"] is None


def test_invalid_json_and_missing_schema_fields_fall_back_without_a_diagnosis() -> None:
    malformed = parse('{"issue_type":')
    assert malformed["diagnosisStatus"] == "INVALID_FORMAT"
    assert malformed["finalDiagnosis"] is None
    assert malformed["rawModelOutput"] == '{"issue_type":'
    missing = price_diagnosis()
    del missing["evidence"]
    assert parse(missing)["finalDiagnosis"] is None


def test_missing_or_invented_evidence_is_not_converted_into_a_normal_diagnosis() -> None:
    empty = price_diagnosis()
    empty["evidence"] = []
    assert parse(empty)["diagnosisStatus"] == "INSUFFICIENT_EVIDENCE"
    invented = price_diagnosis()
    invented["evidence"][0]["code"] = "return price * quantity * discount;"
    result = parse(invented)
    assert result["finalDiagnosis"] is None
    assert result["diagnosisStatus"] == "INSUFFICIENT_EVIDENCE"


def test_heuristic_planner_target_is_not_evidence() -> None:
    plan = TaskPlanner().plan("为什么订单价格计算错误？")
    assert plan.target_source == "HEURISTIC"
    value = price_diagnosis()
    value["evidence"] = [{"file": "missing.java", "line": 1, "symbol": "calculatePrice",
                          "code": "return 1;", "reason": "Planner 猜测"}]
    result = parse_final_diagnosis(json.dumps(value), plan, [])
    assert result["diagnosisStatus"] == "INSUFFICIENT_EVIDENCE"
    assert result["finalDiagnosis"] is None


def test_unverified_business_formula_is_replaced_with_explicit_inference() -> None:
    value = price_diagnosis()
    value["root_cause"] = "The correct formula should be price * quantity * discount."
    result = parse(value)
    assert result["diagnosisStatus"] == "VALID"
    assert "正确公式需要需求或测试用例确认" in result["finalDiagnosis"]["root_cause"]
    assert any("正确业务公式" in issue for issue in result["diagnosisIssues"])
    assert "price * quantity * discount" in result["rawModelOutput"]


def test_unverified_formula_in_fix_suggestion_is_not_shown_as_known_rule() -> None:
    value = price_diagnosis()
    value["root_cause"] = "价格计算公式错误"
    value["fix_suggestion"] = "修正价格计算公式为 return price * quantity * discount;"
    result = parse(value)
    assert result["diagnosisStatus"] == "VALID"
    assert "price * quantity * discount" not in result["finalDiagnosis"]["fix_suggestion"]
    assert "正确公式需要需求或测试用例确认" in result["finalDiagnosis"]["root_cause"]
    assert any("正确业务公式" in issue for issue in result["diagnosisIssues"])


def test_unobserved_location_and_call_chain_are_not_presented_as_facts() -> None:
    value = price_diagnosis()
    value["location"] = {"file": "src/Missing.java", "line": 200, "symbol": "Imagined.calculatePrice"}
    value["call_chain"] = ["Imagined.createOrder", "PriceService.calculatePrice"]
    result = parse(value)
    assert result["diagnosisStatus"] == "VALID"
    assert result["finalDiagnosis"]["location"] == {"file": None, "line": None, "symbol": None}
    assert result["finalDiagnosis"]["call_chain"] == []


def test_benchmark_can_recheck_grounding_without_trusting_model_fields() -> None:
    evidence = price_diagnosis()["evidence"]
    valid, issues = validate_evidence_against_trace(evidence, price_trace())
    assert len(valid) == 1 and not issues
    valid, issues = validate_evidence_against_trace(evidence, [])
    assert not valid and issues


def test_real_model_style_fenced_json_short_symbols_and_wrong_line_are_grounded() -> None:
    value = price_diagnosis()
    value["location"] = {"file": "src/PriceService.java", "line": 6, "symbol": "calculatePrice"}
    value["evidence"][0].update(line=6, symbol="calculatePrice")
    value["root_cause"] = "正确公式应该是 price * quantity * discount。"
    value["fix_suggestion"] = "改为return price * quantity * discount;"
    value["uncertainty"] = "0"
    result = parse("```json\n" + json.dumps(value, ensure_ascii=False) + "\n```")
    assert result["diagnosisStatus"] == "VALID"
    diagnosis = result["finalDiagnosis"]
    assert diagnosis["evidence"][0]["line"] == 8
    assert diagnosis["evidence"][0]["symbol"] == "PriceService.calculatePrice"
    assert diagnosis["location"] == {"file": "src/PriceService.java", "line": 8,
                                      "symbol": "PriceService.calculatePrice"}
    assert "price * quantity * discount" not in diagnosis["root_cause"]
    assert diagnosis["uncertainty"] != "0"
    assert any("行号" in issue for issue in result["diagnosisIssues"])


def test_prose_wrapped_json_remains_invalid() -> None:
    raw = "I found this: " + json.dumps(price_diagnosis(), ensure_ascii=False)
    assert parse(raw)["diagnosisStatus"] == "INVALID_FORMAT"


def test_configuration_answer_cannot_claim_deployed_values_without_config_observation() -> None:
    value = price_diagnosis()
    value["issue_type"] = "CONFIGURATION_ERROR"
    value["root_cause"] = "数据库 URL 一定为空"
    plan = TaskPlanner().plan("为什么数据库配置错误？")
    result = parse_final_diagnosis(json.dumps(value, ensure_ascii=False), plan, price_trace())
    assert result["diagnosisStatus"] == "UNSUPPORTED"
    assert result["finalDiagnosis"] is None
    assert "无法读取并关联配置文件" in result["userMessage"]


def test_call_chain_cannot_claim_success_after_unobserved_edges_are_removed() -> None:
    value = price_diagnosis()
    value["issue_type"] = "CALL_CHAIN_ANALYSIS"
    value["root_cause"] = "调用路径已成功追踪"
    value["call_chain"] = ["Imagined.start", "PriceService.calculatePrice"]
    plan = TaskPlanner().plan("追踪OrderService.createOrder到PriceService.calculatePrice的调用路径")
    result = parse_final_diagnosis(json.dumps(value, ensure_ascii=False), plan, price_trace())
    assert result["diagnosisStatus"] == "INSUFFICIENT_EVIDENCE"
    assert result["finalDiagnosis"] is None


def test_call_chain_short_names_are_normalized_only_when_all_edges_are_observed() -> None:
    index = AnalysisIndex().analyze(Path(__file__).parents[3] / "demo" / "order-demo")
    symbols = {symbol.name: symbol for symbol in index.symbols.values()
               if symbol.name in {"checkStock", "findStock"}}
    controller = next(symbol for symbol in index.symbols.values()
                      if symbol.qualifiedName.endswith("OrderController.createOrder"))
    order = next(symbol for symbol in index.symbols.values()
                 if symbol.qualifiedName.endswith("OrderService.createOrder"))
    registry = build_tool_registry(index)
    trace = []
    for number, (tool, arguments) in enumerate([
        ("searchSymbol", {"qualifiedName": "OrderController.createOrder"}),
        ("findCallees", {"symbolId": controller.id}),
        ("findCallees", {"symbolId": order.id}),
        ("findCallees", {"symbolId": symbols["checkStock"].id}),
    ], 1):
        result = registry.execute(tool, arguments)
        trace.append({"step": number, "tool": tool, "success": result.success,
                      "observation": to_dict(result.observationModel)})
    diagnosis = {"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "调用链已发现",
                 "location": {"file": "InventoryRepository.java", "line": 4, "symbol": "findStock"},
                 "root_cause": "按已解析边追踪调用链", "evidence": [{
                     "file": "OrderController.java", "line": 11, "symbol": "OrderController.createOrder",
                     "code": "orderService.createOrder()", "reason": "调用边"}],
                 "call_chain": ["OrderController.createOrder", "OrderService.createOrder",
                                "InventoryService.checkStock", "InventoryRepository.findStock"],
                 "fix_suggestion": "无", "uncertainty": "仅静态已解析边"}
    plan = TaskPlanner().plan("追踪OrderController.createOrder到InventoryRepository.findStock的调用路径")
    result = parse_final_diagnosis(json.dumps(diagnosis), plan, trace)
    assert result["diagnosisStatus"] == "VALID"
    assert len(result["finalDiagnosis"]["call_chain"]) == 4
    assert result["finalDiagnosis"]["call_chain"][0] == "demo.order.OrderController.createOrder"
    assert result["finalDiagnosis"]["location"]["symbol"] == "demo.order.InventoryRepository.findStock"

    partial = parse_final_diagnosis(json.dumps(diagnosis), plan, trace[:-1])
    assert partial["diagnosisStatus"] == "VALID"
    assert len(partial["finalDiagnosis"]["call_chain"]) == 3
    assert partial["finalDiagnosis"]["summary"] == "仅核验了部分调用路径"
    assert "后续关系仍缺少" in partial["finalDiagnosis"]["root_cause"]
