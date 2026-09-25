"""Enterprise-only evidence checks; frozen benchmark fixtures are unchanged."""

import json
from pathlib import Path

from app.agent.execution_policy import AgentExecutionState
from app.agent.planner import TaskPlanner
from app.agent.projection import project_final_diagnosis
from app.agent.tools import build_tool_registry
from app.domain.models import RelationType, to_dict
from app.repository.index import AnalysisIndex


ROOT = Path(__file__).parents[3]
ALLOCATOR = "src/main/java/com/repomind/showcase/domain/inventory/StockAllocator.java"
REPOSITORY = "src/main/java/com/repomind/showcase/infrastructure/repository/InMemoryInventoryRepository.java"
QUESTION = "为什么 StockAllocator.allocate 可能出现 NullPointerException？"


def _observe(state, registry, trace, tool, arguments):
    result = registry.execute(tool, arguments)
    observation = to_dict(result.observationModel)
    step = len(trace) + 1
    state.observe(tool, arguments, observation, step)
    trace.append({"step": step, "tool": tool, "input": arguments,
                  "success": result.success, "observation": observation})
    assert result.success


def test_enterprise_cross_file_chain_requires_both_observed_sources() -> None:
    index = AnalysisIndex().analyze(ROOT / "demo/enterprise-order-showcase")
    state = AgentExecutionState(QUESTION, TaskPlanner().plan(QUESTION), analysis_index=index)
    registry = build_tool_registry(index)
    trace = []
    _observe(state, registry, trace, "searchSymbol", {"name": "allocate"})
    _observe(state, registry, trace, "readFile", {"filePath": ALLOCATOR})
    assert not state.cross_file_evidence()["complete"]
    assert "invalid_return_observed" in state.cross_file_evidence()["missing"]
    _observe(state, registry, trace, "searchSymbol", {"name": "findAvailableStock"})
    _observe(state, registry, trace, "readFile", {"filePath": REPOSITORY})
    chain = state.cross_file_evidence()
    assert chain["complete"]
    assert [item["type"] for item in chain["chain"]] == [
        "CALL_EDGE", "IMPLEMENTS", "RETURN_VALUE", "ASSIGNMENT", "DEREFERENCE"]
    assert chain["runtime_execution_proven"] is False
    assert state.runtime_facts()["related_call_edge"]["source_tool"] == "indexed_call_graph"

    raw = json.dumps({"issue_type": "RUNTIME_ERROR", "summary": "库存空值风险",
                      "location": {"file": ALLOCATOR, "line": 8, "symbol": "StockAllocator.allocate"},
                      "root_cause": "仓储可能返回空值，随后解引用存在异常风险",
                      "evidence": [{"file": ALLOCATOR, "line": 8, "symbol": "StockAllocator.allocate",
                                    "evidence": "Stock stock = repository.findAvailableStock(sku);"},
                                   {"file": REPOSITORY, "line": 10, "symbol": "findAvailableStock",
                                    "evidence": "return invented();"}],
                      "suggestion": "检查仓储返回值",
                      "uncertainty": "仅静态风险"}, ensure_ascii=False)
    diagnosis = project_final_diagnosis(raw, state.plan, trace, state)
    assert diagnosis["diagnosisStatus"] == "VALID"
    assert diagnosis["crossFileEvidence"]["final_diagnosis_complete"]
    assert diagnosis["finalDiagnosis"]["summary"] == "发现潜在空值解引用风险（静态证据）"
    assert "可能触发" in diagnosis["finalDiagnosis"]["root_cause"]
    evidence = diagnosis["finalDiagnosis"]["evidence"]
    assert [name.rsplit(".", 2)[-2:] for name in diagnosis["finalDiagnosis"]["call_chain"]] == [
        ["StockAllocator", "allocate"], ["InventoryRepository", "findAvailableStock"]]
    assert {item["file"] for item in evidence if item["source_tool"] == "readFile"} == {ALLOCATOR, REPOSITORY}
    assert {item["evidence_type"] for item in evidence} >= {"RETURN_VALUE", "ASSIGNMENT", "DEREFERENCE"}
    assert all(item["symbol"] and item["source_step"] and item["kind"] == "FACT" for item in evidence)
    assert all(item["code"] != "return invented();" for item in evidence)
    assert any(item.startswith("STRUCTURAL_COMPATIBILITY") for item in diagnosis["diagnosisIssues"])
    assert "未观察到运行时输入" in diagnosis["finalDiagnosis"]["uncertainty"]


def test_multiple_interface_implementations_do_not_select_a_runtime_target(tmp_path) -> None:
    repository = tmp_path / "sample"
    repository.mkdir()
    (repository / "Repository.java").write_text("interface Repository {\n  Object find();\n}\n", encoding="utf-8")
    (repository / "One.java").write_text(
        "class One implements Repository {\n  public Object find() { return null; }\n}\n", encoding="utf-8")
    (repository / "Two.java").write_text(
        "class Two implements Repository {\n  public Object find() { return null; }\n}\n", encoding="utf-8")
    (repository / "Service.java").write_text(
        "class Service {\n  private Repository repository;\n  void run() {\n    Object value = repository.find();\n    value.toString();\n  }\n}\n",
        encoding="utf-8")
    index = AnalysisIndex().analyze(repository)
    question = "为什么 Service.run 出现 NullPointerException？"
    state = AgentExecutionState(question, TaskPlanner().plan(question), analysis_index=index)
    registry = build_tool_registry(index)
    trace = []
    _observe(state, registry, trace, "searchSymbol", {"name": "run"})
    _observe(state, registry, trace, "readFile", {"filePath": "Service.java"})
    _observe(state, registry, trace, "searchSymbol", {"name": "find"})
    _observe(state, registry, trace, "readFile", {"filePath": "One.java"})
    assert state.runtime_facts()["ambiguous_implementations"]
    assert state.runtime_facts()["implementation_candidate"] is None
    assert not state.cross_file_evidence()["complete"]
    assert "unique_implementation_relation" in state.cross_file_evidence()["missing"]
    assert any(relation.type == RelationType.CALLS and relation.targetName == "find" and relation.resolved
               for relation in index.relations)
