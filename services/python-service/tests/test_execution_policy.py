"""Execution-policy unit tests use real indexed demo Tools, never a fake benchmark Trace."""

import json
from pathlib import Path

from app.agent.diagnosis import parse_final_diagnosis
from app.agent.execution_policy import (
    AgentExecutionState, complete_final_evidence, has_configuration_capability,
    normalized_call, query_symbol_hints,
)
from app.agent.loop import AgentLoop
from app.agent.planner import TaskPlanner
from app.agent.provider import DeterministicTestProvider, ToolCall
from app.agent.tools import build_tool_registry
from app.domain.models import to_dict
from app.repository.index import AnalysisIndex


ROOT = Path(__file__).parents[3]


def setup_state(repository: str, question: str):
    index = AnalysisIndex().analyze(ROOT / repository)
    state = AgentExecutionState(question, TaskPlanner().plan(question))
    return index, state, build_tool_registry(index), []


def execute(state, registry, trace, tool: str, arguments: dict):
    step = len(trace) + 1
    result = registry.execute(tool, arguments)
    observation = to_dict(result.observationModel)
    progress, new_evidence = state.observe(tool, arguments, observation, step)
    trace.append({"step": step, "tool": tool, "input": arguments, "success": result.success,
                  "observation": observation, "progress": progress})
    return progress, new_evidence


def test_normalized_duplicate_calls_and_different_arguments() -> None:
    first = normalized_call("searchSymbol", {"name": "Login", "language": "python", "qualifiedName": ""})
    assert first == normalized_call("searchSymbol", {"language": "PYTHON", "name": "login"})
    assert first != normalized_call("searchSymbol", {"name": "get_user", "language": "PYTHON"})
    _, state, registry, trace = setup_state("demo/repomind-agent-test-demo/python-bug-demo",
                                             "为什么UserService.login出现TypeError？")
    execute(state, registry, trace, "searchSymbol", {"name": "login", "language": "PYTHON"})
    assert state.already_called("searchSymbol", {"name": "Login", "language": "python"})
    assert not state.already_called("searchSymbol", {"name": "get_user", "language": "PYTHON"})


def test_progress_counts_new_symbols_files_edges_and_resets_after_empty_or_repeat() -> None:
    index, state, registry, trace = setup_state("demo/order-demo",
                                                "为什么InventoryService.checkStock出现NullPointerException？")
    target = next(value for value in index.symbols.values() if value.name == "checkStock")
    assert execute(state, registry, trace, "searchSymbol", {"name": "unfindable"})[0] is False
    assert state.consecutive_no_progress == 1 and len(state.failed_searches) == 1
    assert execute(state, registry, trace, "searchSymbol", {"name": "checkStock"})[0] is True
    assert state.consecutive_no_progress == 0 and state.last_progress_step == 2
    assert execute(state, registry, trace, "searchSymbol", {"name": "checkStock"})[0] is False
    assert state.consecutive_no_progress == 1
    progress, new = execute(state, registry, trace, "findCallees", {"symbolId": target.id})
    assert progress and any(item.startswith("CallEdges:") for item in new)
    assert state.consecutive_no_progress == 0
    assert execute(state, registry, trace, "readFile", {"filePath": "InventoryService.java"})[0] is True
    assert "InventoryService.java" in state.discovered_files
    assert execute(state, registry, trace, "readFile", {"filePath": "InventoryService.java"})[0] is False


def test_runtime_checklist_requires_null_origin_and_dereference_not_just_a_call() -> None:
    index, state, registry, trace = setup_state("demo/order-demo",
                                                "为什么InventoryService.checkStock出现NullPointerException？")
    target = next(value for value in index.symbols.values() if value.name == "checkStock")
    execute(state, registry, trace, "searchSymbol", {"name": "checkStock"})
    execute(state, registry, trace, "findCallees", {"symbolId": target.id})
    execute(state, registry, trace, "readFile", {"filePath": "InventoryService.java", "startLine": 10, "endLine": 11})
    execute(state, registry, trace, "readFile", {"filePath": "InventoryRepository.java", "startLine": 4, "endLine": 6})
    checks = state.checklist()
    assert checks["invalid_value_origin"] and checks["related_call_edge"]
    assert not checks["trigger_operation"]
    assert state.completion_decision() == "PARTIAL"
    assert "trigger_operation" in state.missing_evidence()
    execute(state, registry, trace, "readFile", {"filePath": "InventoryService.java", "startLine": 12, "endLine": 12})
    assert state.checklist()["trigger_operation"]
    assert state.completion_decision() == "COMPLETE"


def test_business_checklist_keeps_missing_business_expectation_partial() -> None:
    index, state, registry, trace = setup_state("demo/repomind-agent-test-demo/logic-bug-demo",
                                                "为什么订单价格计算错误？")
    target = next(value for value in index.symbols.values() if value.name == "calculatePrice")
    execute(state, registry, trace, "searchSymbol", {"name": "calculatePrice"})
    execute(state, registry, trace, "findCallers", {"symbolId": target.id})
    execute(state, registry, trace, "readFile", {"filePath": "src/PriceService.java"})
    assert "related_call_context" in state.missing_evidence()
    execute(state, registry, trace, "readFile", {"filePath": "src/OrderService.java"})
    assert state.checklist()["related_call_context"]
    assert not state.checklist()["business_expectation"]
    assert state.missing_evidence() == ["business_expectation"]
    assert state.completion_decision() == "PARTIAL"
    assert not state.should_block_final(remaining_turns=2)


def test_call_tracker_requires_each_observed_edge_and_keeps_provenance() -> None:
    index, state, registry, trace = setup_state("demo/repomind-agent-test-demo/call-chain-demo",
                                                "追踪UserService.register到ConfigRepository.getTemplate的调用路径。")
    start = next(value for value in index.symbols.values() if value.name == "register")
    end = next(value for value in index.symbols.values() if value.name == "getTemplate")
    execute(state, registry, trace, "searchSymbol", {"name": "register"})
    execute(state, registry, trace, "searchSymbol", {"name": "getTemplate"})
    execute(state, registry, trace, "findCallees", {"symbolId": start.id})
    email = next(value for value in index.symbols.values() if value.name == "sendEmail")
    execute(state, registry, trace, "findCallees", {"symbolId": email.id})
    assert state.verified_chain() == []
    assert state.partial_chain() == ["UserService.register", "EmailService.sendEmail", "TemplateService.render"]
    assert state.completion_decision() == "PARTIAL"
    template = next(value for value in index.symbols.values() if value.name == "render")
    execute(state, registry, trace, "findCallees", {"symbolId": template.id})
    assert state.verified_chain() == ["UserService.register", "EmailService.sendEmail",
                                      "TemplateService.render", "ConfigRepository.getTemplate"]
    assert state.completion_decision() == "COMPLETE"
    assert all(edge["source_tool"] == "findCallees" and edge["source_step"] >= 3
               for edge in state.call_tracker.edge_records())
    assert end.id in state.call_tracker.nodes


def test_complete_graph_path_survives_redundant_tool_calls_and_reaches_final() -> None:
    question = "追踪UserService.register到ConfigRepository.getTemplate的调用路径。"
    index = AnalysisIndex().analyze(ROOT / "demo/repomind-agent-test-demo/call-chain-demo")
    start = next(item for item in index.symbols.values() if item.name == "register")
    email = next(item for item in index.symbols.values() if item.name == "sendEmail")
    template = next(item for item in index.symbols.values() if item.name == "render")
    final = json.dumps({"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "静态调用路径",
                        "location": {"file": start.filePath, "line": start.startLine,
                                     "symbol": start.qualifiedName},
                        "root_cause": "已解析的调用关系形成路径",
                        "evidence": [{"file": start.filePath, "line": start.startLine,
                                      "symbol": start.qualifiedName, "code": None, "reason": "Symbol"}],
                        "call_chain": ["UserService.register", "EmailService.sendEmail",
                                       "TemplateService.render", "ConfigRepository.getTemplate"],
                        "fix_suggestion": "无需修复", "uncertainty": "仅证明静态调用边"}, ensure_ascii=False)
    provider = DeterministicTestProvider([
        ToolCall("searchSymbol", {"name": "register"}),
        ToolCall("findCallers", {"symbolId": start.id}),
        ToolCall("findCallees", {"symbolId": start.id}),
        ToolCall("findCallees", {"symbolId": email.id}),
        ToolCall("findCallees", {"symbolId": template.id}),
    ], final)
    result = AgentLoop(provider, build_tool_registry(index)).run(question, 8, 5, TaskPlanner().plan(question))
    assert result["status"] == "COMPLETED"
    assert result["diagnosisStatus"] == "VALID"
    assert len(result["executionState"]["graph_path_evidence"]) == 3
    assert [item["tool"] for item in result["trace"]] == ["searchSymbol", "findCallers",
                                                          "findCallees", "findCallees", "findCallees"]


def test_python_method_search_fallback_is_generic_and_finite() -> None:
    _, state, registry, trace = setup_state("demo/repomind-agent-test-demo/python-bug-demo",
                                             "为什么UserService.login出现TypeError异常？")
    assert query_symbol_hints(state.question) == ["UserService.login"]
    execute(state, registry, trace, "searchSymbol",
            {"name": "login", "qualifiedName": "UserService.login", "language": "JAVA", "type": "METHOD"})
    assert len(state.failed_searches) == 1
    feedback = state.feedback()
    assert "name='login'" in feedback and "language=PYTHON" in feedback
    assert "Do not repeat those exact filters" in feedback
    progress, found = execute(state, registry, trace, "searchSymbol", {"name": "login", "language": "PYTHON"})
    assert progress and any("service.UserService.login" in item for item in found)
    assert state.completion_decision() == "PARTIAL"


def test_duplicate_observation_does_not_count_as_progress_and_stops_loop_early() -> None:
    index = AnalysisIndex().analyze(ROOT / "demo/repomind-agent-test-demo/python-bug-demo")
    provider = DeterministicTestProvider([ToolCall("searchSymbol", {"name": "missing"})] * 8, "never reached")
    question = "为什么UserService.login出现TypeError异常？"
    result = AgentLoop(provider, build_tool_registry(index)).run(question, 8, 5, TaskPlanner().plan(question))
    assert result["status"] == "NO_PROGRESS"
    assert len(result["trace"]) == 4  # stops before maxSteps
    assert result["trace"][0]["toolExecuted"] is True
    assert all(step["toolExecuted"] is False and step["policyStatus"] == "DUPLICATE_CALL"
               for step in result["trace"][1:])
    assert result["executionState"]["duplicate_calls"] == 3
    assert result["diagnosisStatus"] == "INSUFFICIENT_EVIDENCE"


def test_same_tool_different_args_executes_normally() -> None:
    index = AnalysisIndex().analyze(ROOT / "demo/repomind-agent-test-demo/python-bug-demo")
    provider = DeterministicTestProvider([
        ToolCall("searchSymbol", {"name": "login", "language": "JAVA"}),
        ToolCall("searchSymbol", {"name": "login", "language": "PYTHON"}),
    ], "not JSON")
    question = "为什么UserService.login出现TypeError异常？"
    result = AgentLoop(provider, build_tool_registry(index)).run(question, 3, 5, TaskPlanner().plan(question))
    assert [step["toolExecuted"] for step in result["trace"]] == [True, True]
    assert result["trace"][1]["progress"] is True


def test_runtime_final_evidence_is_completed_only_from_real_read_file_observations() -> None:
    index, state, registry, trace = setup_state("demo/order-demo",
                                                "为什么InventoryService.checkStock出现NullPointerException？")
    target = next(value for value in index.symbols.values() if value.name == "checkStock")
    execute(state, registry, trace, "searchSymbol", {"name": "checkStock"})
    execute(state, registry, trace, "findCallees", {"symbolId": target.id})
    execute(state, registry, trace, "readFile", {"filePath": "InventoryService.java"})
    execute(state, registry, trace, "readFile", {"filePath": "InventoryRepository.java"})
    raw = json.dumps({"issue_type": "RUNTIME_ERROR", "summary": "发现空值返回与使用",
                      "location": {"file": "InventoryService.java", "line": 11,
                                   "symbol": "demo.order.InventoryService.checkStock"},
                      "root_cause": "可能解引用了空值", "evidence": [
                          {"file": "InventoryRepository.java", "line": 5,
                           "symbol": "demo.order.InventoryRepository.findStock",
                           "code": "return null;", "reason": "源码"}],
                      "call_chain": [], "fix_suggestion": "检查空值", "uncertainty": "仅依据当前源码"}, ensure_ascii=False)
    result = parse_final_diagnosis(raw, state.plan, trace)
    assert result["diagnosisStatus"] == "VALID"
    assert len(result["finalDiagnosis"]["evidence"]) == 1
    completed = complete_final_evidence(result, state, trace)
    assert any(item["file"] == "InventoryService.java" and item["line"] == 12 and
               item["code"] == "if (stock.available) {" and item["source_tool"] == "readFile"
               for item in completed["finalDiagnosis"]["evidence"])
    assert completed["finalDiagnosis"]["location"]["line"] == 12
    assert any("异常触发操作修正" in issue for issue in completed["diagnosisIssues"])
    assert any("非模型原文" in issue for issue in completed["diagnosisIssues"])


def test_capability_check_reports_configuration_unsupported_before_tool_use() -> None:
    assert not has_configuration_capability({"searchSymbol", "readFile", "findCallers"})
    assert has_configuration_capability({"searchSymbol", "readConfig"})
    index = AnalysisIndex().analyze(ROOT / "demo/repomind-agent-test-demo/config-demo")
    provider = DeterministicTestProvider([ToolCall("searchSymbol", {})], "should not be used")
    question = "为什么application.yml中的database.username配置没有生效？"
    result = AgentLoop(provider, build_tool_registry(index)).run(question, 8, 5, TaskPlanner().plan(question))
    assert result["status"] == "UNSUPPORTED" and result["trace"] == []
    assert provider.calls  # not consumed


def test_premature_final_is_deferred_while_fresh_evidence_is_available() -> None:
    # A model may still decide to stop; the policy must request more evidence without inventing a Tool result.
    index = AnalysisIndex().analyze(ROOT / "demo/order-demo")
    target = next(value for value in index.symbols.values() if value.name == "checkStock")

    class ScriptedProvider:
        name = "TEST PROVIDER"

        def __init__(self):
            self.responses = iter([
                ToolCall("searchSymbol", {"name": "checkStock"}),
                None,  # premature final
                ToolCall("readFile", {"filePath": "InventoryService.java"}),
                ToolCall("findCallees", {"symbolId": target.id}),
                ToolCall("readFile", {"filePath": "InventoryRepository.java"}),
                None,
            ])

        def complete(self, messages, tools):
            from app.agent.provider import LLMResponse
            item = next(self.responses)
            return LLMResponse(toolCall=item) if item else LLMResponse(text="not JSON")

    question = "为什么InventoryService.checkStock出现NullPointerException？"
    result = AgentLoop(ScriptedProvider(), build_tool_registry(index)).run(question, 7, 5, TaskPlanner().plan(question))
    assert result["status"] == "COMPLETED"
    assert [step["tool"] for step in result["trace"]] == ["searchSymbol", "readFile", "findCallees", "readFile"]
    assert any(event["status"] == "EVIDENCE_GAP" for event in result["executionState"]["policy_events"])
    assert result["completionDecision"] == "COMPLETE"


def test_tool_budget_allows_one_final_only_turn_without_a_ninth_tool_execution() -> None:
    index = AnalysisIndex().analyze(ROOT / "demo/order-demo")
    provider = DeterministicTestProvider([
        ToolCall("searchSymbol", {"name": "checkStock"}),
        ToolCall("readFile", {"filePath": "InventoryService.java"}),
    ], "final-only model text")
    question = "为什么InventoryService.checkStock出现NullPointerException？"
    result = AgentLoop(provider, build_tool_registry(index)).run(question, 2, 5, TaskPlanner().plan(question))
    assert result["status"] == "COMPLETED"
    assert len(result["trace"]) == 2
    assert any(item["status"] == "FINAL_ONLY" for item in result["executionState"]["policy_events"])
    assert result["diagnosisStatus"] == "INVALID_FORMAT"  # model text is not fabricated into JSON


def test_final_call_chain_edges_are_completed_from_real_relation_observations() -> None:
    index, state, registry, trace = setup_state("demo/repomind-agent-test-demo/call-chain-demo",
                                                "追踪UserService.register到ConfigRepository.getTemplate的调用路径。")
    start = next(value for value in index.symbols.values() if value.name == "register")
    email = next(value for value in index.symbols.values() if value.name == "sendEmail")
    template = next(value for value in index.symbols.values() if value.name == "render")
    execute(state, registry, trace, "searchSymbol", {"name": "register"})
    execute(state, registry, trace, "findCallees", {"symbolId": start.id})
    execute(state, registry, trace, "findCallees", {"symbolId": email.id})
    execute(state, registry, trace, "findCallees", {"symbolId": template.id})
    raw = json.dumps({"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "路径",
                      "location": {"file": "src/TemplateService.java", "line": 6,
                                   "symbol": "TemplateService.render"},
                      "root_cause": "已追踪部分路径", "evidence": [{
                          "file": "src/UserService.java", "line": 6, "symbol": "UserService.register",
                          "code": "emailService.sendEmail(email)", "reason": "调用"}],
                      "call_chain": ["UserService.register", "EmailService.sendEmail"],
                      "fix_suggestion": "无", "uncertainty": "静态调用图"}, ensure_ascii=False)
    result = parse_final_diagnosis(raw, state.plan, trace)
    assert result["diagnosisStatus"] == "VALID"
    assert len(result["finalDiagnosis"]["evidence"]) == 1
    completed = complete_final_evidence(result, state, trace)
    assert completed["finalDiagnosis"]["call_chain"] == state.verified_chain()
    assert len(completed["finalDiagnosis"]["evidence"]) == 3
    assert all(item["source_tool"] == "call_relation" for item in completed["finalDiagnosis"]["evidence"])
    assert all(item["source_step"] in {2, 3, 4} for item in completed["finalDiagnosis"]["evidence"])


def test_call_edge_completion_prefers_exact_read_file_line_when_observed() -> None:
    index, state, registry, trace = setup_state("demo/repomind-agent-test-demo/call-chain-demo",
                                                "追踪UserService.register到ConfigRepository.getTemplate的调用路径。")
    start = next(value for value in index.symbols.values() if value.name == "register")
    email = next(value for value in index.symbols.values() if value.name == "sendEmail")
    template = next(value for value in index.symbols.values() if value.name == "render")
    execute(state, registry, trace, "searchSymbol", {"name": "register"})
    execute(state, registry, trace, "findCallees", {"symbolId": start.id})
    execute(state, registry, trace, "findCallees", {"symbolId": email.id})
    execute(state, registry, trace, "findCallees", {"symbolId": template.id})
    execute(state, registry, trace, "readFile", {"filePath": "src/UserService.java"})
    raw = json.dumps({"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "路径",
                      "location": {"file": "src/UserService.java", "line": 6, "symbol": "UserService.register"},
                      "root_cause": "已观察到调用", "evidence": [{"file": "src/UserService.java", "line": 6,
                          "symbol": "UserService.register", "code": "emailService.sendEmail(email)",
                          "reason": "调用"}],
                      "call_chain": ["UserService.register", "EmailService.sendEmail"],
                      "fix_suggestion": "无", "uncertainty": "静态调用图"}, ensure_ascii=False)
    completed = complete_final_evidence(parse_final_diagnosis(raw, state.plan, trace), state, trace)
    evidence = completed["finalDiagnosis"]["evidence"]
    assert any(item["code"] == "emailService.sendEmail(email);" and
               item["source_tool"] == "readFile" for item in evidence)
