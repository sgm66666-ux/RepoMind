"""Projection tests use real indexed Demo Tools; synthetic cases test ambiguity/depth only."""

import json
from pathlib import Path

from app.agent.evidence import VerifiedEvidenceStore, normalize_source_code
from app.agent.execution_policy import AgentExecutionState
from app.agent.planner import TaskPlanner
from app.agent.projection import project_final_diagnosis
from app.agent.tools import build_tool_registry
from app.domain.models import to_dict
from app.repository.index import AnalysisIndex


ROOT = Path(__file__).parents[3]


def setup(repository: str, question: str):
    index = AnalysisIndex().analyze(ROOT / repository)
    state = AgentExecutionState(question, TaskPlanner().plan(question))
    return index, state, build_tool_registry(index), []


def observe(state, registry, trace, tool, arguments):
    result = registry.execute(tool, arguments)
    observation = to_dict(result.observationModel)
    step = len(trace) + 1
    state.observe(tool, arguments, observation, step)
    trace.append({"step": step, "tool": tool, "input": arguments,
                  "success": result.success, "observation": observation})
    return observation


def draft(task, location, evidence, chain=(), root="模型推断，需核查"):
    return json.dumps({"issue_type": task, "summary": "源码调查", "location": location,
                       "root_cause": root, "evidence": evidence, "call_chain": list(chain),
                       "fix_suggestion": "核查源码和输入", "uncertainty": "仅依据静态证据"}, ensure_ascii=False)


def test_store_accepts_only_successful_tool_observations_and_deduplicates() -> None:
    _, state, registry, trace = setup("demo/order-demo", "为什么InventoryService.checkStock出现NullPointerException？")
    assert not state.evidence_store.symbols  # Planner keyword is not a verified Symbol.
    observation = observe(state, registry, trace, "searchSymbol", {"name": "checkStock"})
    store = state.evidence_store
    assert len(store.symbols) == 1
    store.ingest("searchSymbol", {"name": "checkStock"}, observation, 2)
    store.ingest("searchSymbol", {}, {"success": False, "data": [{"id": "fake"}]}, 3)
    assert len(store.symbols) == 1
    assert store.resolve_symbol("InventoryService.checkStock") is not None
    assert store.resolve_symbol("Imagined.method") is None  # Model claim cannot be ingested.
    observe(state, registry, trace, "readFile", {"filePath": "InventoryService.java"})
    count = len(store.source_lines)
    store.ingest("readFile", {"filePath": "InventoryService.java"}, trace[-1]["observation"], 4)
    assert len(store.source_lines) == count
    assert len(store.source_provenance[("InventoryService.java", 11)]) == 2


def test_python_local_assignment_call_and_return_source_are_bounded_and_observed() -> None:
    index, state, registry, trace = setup("demo/repomind-agent-test-demo/python-bug-demo",
                                          "为什么UserService.login出现TypeError异常？请检查返回值来源。")
    observe(state, registry, trace, "searchSymbol", {"name": "login", "language": "PYTHON"})
    observe(state, registry, trace, "readFile", {"filePath": "service.py"})
    flow = state.runtime_facts()
    assert flow["assignment"]["code"] == "user = self.repo.get_user(user_id)"
    assert flow["assignment"]["evidence_type"] == "ASSIGNMENT"
    assert flow["trigger_operation"]["code"] == 'return user["name"]'
    assert flow["trigger_operation"]["evidence_type"] == "DEREFERENCE"
    assert flow["invalid_value_origin"] is None
    assert "searchSymbol(name='get_user')" in state.feedback()
    observe(state, registry, trace, "searchSymbol", {"name": "get_user", "language": "PYTHON"})
    assert "repository.py" in state.feedback() and "readFile" in state.feedback()
    observe(state, registry, trace, "readFile", {"filePath": "repository.py"})
    flow = state.runtime_facts()
    assert flow["invalid_value_origin"]["code"] == "return None"
    assert flow["source_to_usage_linkage"] == "OBSERVED_OWNER_TYPE"
    assert not state.evidence_store.edges  # Textual owner/type link is not a fake CALLS edge.
    assert state.completion_decision() == "COMPLETE"
    callees = index.callGraph.findCallees(next(s.id for s in index.symbols.values() if s.name == "login"))
    assert [item["symbol"].name for item in callees] == ["get_user"]
    assert callees[0]["relation"].resolutionMethod == "IMPORTED_CONSTRUCTOR_ASSIGNMENT"


def test_inventory_runtime_projection_uses_real_line_and_preserves_inference() -> None:
    index, state, registry, trace = setup("demo/order-demo", "为什么InventoryService.checkStock出现NullPointerException？")
    target = next(symbol for symbol in index.symbols.values() if symbol.name == "checkStock")
    observe(state, registry, trace, "searchSymbol", {"name": "checkStock"})
    observe(state, registry, trace, "findCallees", {"symbolId": target.id})
    observe(state, registry, trace, "readFile", {"filePath": "InventoryService.java"})
    observe(state, registry, trace, "readFile", {"filePath": "InventoryRepository.java"})
    flow = state.runtime_facts()
    assert flow["source_to_usage_linkage"] == "RESOLVED_CALL_EDGE"
    assert [flow[key]["line"] for key in ("invalid_value_origin", "assignment", "trigger_operation")] == [5, 11, 12]
    raw = draft("RUNTIME_ERROR", {"file": "InventoryService.java", "line": 11,
                                  "symbol": "demo.order.InventoryService.checkStock"},
                [{"file": "InventoryService.java", "line": 11,
                  "symbol": "demo.order.InventoryService.checkStock",
                  "code": "Inventory stock = inventoryRepository.findStock();", "reason": "源码"}],
                root="可能由空值解引用引起")
    result = project_final_diagnosis(raw, state.plan, trace, state)
    assert result["diagnosisStatus"] == "VALID"
    diagnosis = result["finalDiagnosis"]
    assert diagnosis["root_cause"] == "可能由空值解引用引起"
    assert diagnosis["location"]["line"] == 12
    assert any(item["code"] == "return null;" and item["source_tool"] == "readFile"
               for item in diagnosis["evidence"])
    assert any(item["code"] == "if (stock.available) {" for item in diagnosis["evidence"])
    assert any(issue.startswith("MODEL_LINE_MISMATCH") for issue in result["diagnosisIssues"])


def test_resolved_graph_path_is_separate_from_actual_tool_trace() -> None:
    index, state, registry, trace = setup(
        "demo/repomind-agent-test-demo/call-chain-demo",
        "追踪UserService.register到ConfigRepository.getTemplate的调用路径。")
    start = next(item for item in index.symbols.values() if item.name == "register")
    observe(state, registry, trace, "searchSymbol", {"name": "register"})
    state.complete_verified_graph_path(index)
    assert [item["tool"] for item in trace] == ["searchSymbol"]
    assert len(state.graph_path_evidence) == 3
    assert state.completion_decision() == "COMPLETE"
    assert state.verified_chain() == ["UserService.register", "EmailService.sendEmail",
                                      "TemplateService.render", "ConfigRepository.getTemplate"]
    assert all(edge["source"] == "AST_RESOLVED_CALL_GRAPH" and edge["relationId"]
               for edge in state.graph_path_evidence)
    raw = draft("CALL_CHAIN_ANALYSIS",
                {"file": start.filePath, "line": start.startLine, "symbol": start.qualifiedName},
                [{"file": start.filePath, "line": start.startLine,
                  "symbol": start.qualifiedName, "code": None, "reason": "Symbol 索引"}],
                chain=state.verified_chain())
    result = project_final_diagnosis(raw, state.plan, trace, state)
    assert result["diagnosisStatus"] == "VALID"
    assert result["finalDiagnosis"]["call_chain"] == state.verified_chain()
    assert not any(item["source_tool"] == "resolved_call_graph"
                   for item in result["finalDiagnosis"]["evidence"])
    graph_edge = state.graph_path_evidence[0]
    graph_only_draft = draft("CALL_CHAIN_ANALYSIS",
                             {"file": None, "line": None, "symbol": None},
                             [{"file": graph_edge["filePath"], "line": graph_edge["line"],
                               "symbol": start.qualifiedName, "code": graph_edge["evidence"],
                               "reason": "模型从静态图看到的调用边"}],
                             chain=state.verified_chain())
    graph_only_result = project_final_diagnosis(graph_only_draft, state.plan, trace, state)
    assert graph_only_result["diagnosisStatus"] == "VALID"
    assert all(item["source_tool"] == "searchSymbol"
               for item in graph_only_result["finalDiagnosis"]["evidence"])
    assert result["rawModelOutput"] == raw


def test_call_chain_is_projected_only_from_complete_verified_edges() -> None:
    index, state, registry, trace = setup("demo/repomind-agent-test-demo/call-chain-demo",
                                          "追踪UserService.register到ConfigRepository.getTemplate的调用路径。")
    names = ("register", "sendEmail", "render")
    symbols = {name: next(symbol for symbol in index.symbols.values() if symbol.name == name) for name in names}
    observe(state, registry, trace, "searchSymbol", {"name": "register"})
    observe(state, registry, trace, "findCallees", {"symbolId": symbols["register"].id})
    observe(state, registry, trace, "findCallees", {"symbolId": symbols["sendEmail"].id})
    evidence = [{"file": "src/UserService.java", "line": 6, "symbol": "UserService.register",
                 "code": "emailService.sendEmail(email)", "reason": "调用关系"}]
    raw = draft("CALL_CHAIN_ANALYSIS", {"file": "src/UserService.java", "line": 6,
                                        "symbol": "UserService.register"}, evidence,
                ["UserService.register", "EmailService.sendEmail"], root="模型对路径的推断")
    partial = project_final_diagnosis(raw, state.plan, trace, state)
    assert partial["finalDiagnosis"]["call_chain"] == ["UserService.register", "EmailService.sendEmail"]
    assert state.completion_decision() == "PARTIAL"
    observe(state, registry, trace, "findCallees", {"symbolId": symbols["render"].id})
    for path in ("src/UserService.java", "src/EmailService.java", "src/TemplateService.java"):
        observe(state, registry, trace, "readFile", {"filePath": path})
    complete = project_final_diagnosis(raw, state.plan, trace, state)
    assert complete["diagnosisStatus"] == "VALID"
    diagnosis = complete["finalDiagnosis"]
    assert diagnosis["call_chain"] == ["UserService.register", "EmailService.sendEmail",
                                       "TemplateService.render", "ConfigRepository.getTemplate"]
    assert diagnosis["root_cause"] == "模型对路径的推断"
    assert len(state.evidence_store.edges) == 3
    assert len({(item["file"], item["line"], item["code"], item["symbol"])
                for item in diagnosis["evidence"]}) == len(diagnosis["evidence"])
    assert any(issue == "CALL_CHAIN_PROJECTED_FROM_VERIFIED_EDGES" for issue in complete["diagnosisIssues"])


def test_canonicalization_does_not_merge_overloads_or_same_short_name() -> None:
    store = VerifiedEvidenceStore()
    base = {"qualifiedName": "a.Service.run", "filePath": "A.java", "startLine": 1,
            "endLine": 2, "type": "METHOD", "language": "JAVA"}
    for symbol_id, signature in (("one", "run(int)"), ("two", "run(String)")):
        store.ingest("searchSymbol", {}, {"success": True, "data": [base | {"id": symbol_id,
                                                                            "signature": signature}]}, 1)
    assert store.resolve_symbol("Service.run") is None
    assert store.canonical_name("one") != store.canonical_name("two")
    other = base | {"id": "three", "qualifiedName": "b.Service.run", "filePath": "B.java"}
    store.ingest("searchSymbol", {}, {"success": True, "data": [other]}, 2)
    assert store.resolve_symbol("Service.run") is None
    assert store.resolve_symbol("b.Service.run").symbol_id == "three"


def test_return_source_depth_limit_and_code_normalization_preserve_tokens() -> None:
    store = VerifiedEvidenceStore()
    for number in range(4):
        name = f"m{number}"
        symbol = {"id": name, "qualifiedName": f"Repo.{name}", "filePath": f"{name}.py",
                  "startLine": 1, "endLine": 1, "type": "METHOD", "language": "PYTHON"}
        store.ingest("searchSymbol", {}, {"success": True, "data": [symbol]}, number + 1)
        code = f"return self.m{number + 1}()" if number < 3 else "return None"
        store.ingest("readFile", {}, {"success": True, "data": {"filePath": f"{name}.py",
                      "requestedRange": {"startLine": 1}, "content": code}}, number + 1)
    assert store._return_source(store.symbols["m0"], 3, set()) is None
    assert store._return_source(store.symbols["m0"], 4, set()).code == "return None"
    assert normalize_source_code('  return  "a  b";  \r\n') == 'return  "a  b";'
    assert normalize_source_code("  x+y  ") != normalize_source_code(" x-y ")


def test_projection_does_not_invent_source_from_model_claim() -> None:
    index, state, registry, trace = setup("demo/order-demo", "为什么InventoryService.checkStock出现NullPointerException？")
    target = next(symbol for symbol in index.symbols.values() if symbol.name == "checkStock")
    observe(state, registry, trace, "searchSymbol", {"name": "checkStock"})
    observe(state, registry, trace, "findCallees", {"symbolId": target.id})
    observe(state, registry, trace, "readFile", {"filePath": "InventoryService.java"})
    fake = "return imaginary_fix();"
    raw = draft("RUNTIME_ERROR", {"file": "InventoryService.java", "line": 99,
                                  "symbol": "demo.order.InventoryService.checkStock"},
                [{"file": "InventoryService.java", "line": 99,
                  "symbol": "demo.order.InventoryService.checkStock", "code": fake,
                  "reason": "模型声称"}])
    result = project_final_diagnosis(raw, state.plan, trace, state)
    assert result["diagnosisStatus"] == "VALID"
    assert all(item["code"] != fake for item in result["finalDiagnosis"]["evidence"])
    assert any("证据未见于成功 Observation" in issue for issue in result["diagnosisIssues"])
