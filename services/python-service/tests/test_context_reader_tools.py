from pathlib import Path

import pytest

from app.agent.tools import build_tool_registry
from app.analysis.context_builder import CodeContextBuilder
from app.repository.index import AnalysisIndex


@pytest.fixture()
def analyzed_index() -> AnalysisIndex:
    return AnalysisIndex().analyze(Path(__file__).parents[3] / "demo" / "order-demo")


def test_read_file_returns_bounded_source_and_rejects_escape(analyzed_index: AnalysisIndex) -> None:
    result = analyzed_index.read_file("OrderService.java", 10, 12)
    assert result.filePath == "OrderService.java"
    assert result.requestedRange.startLine == 10
    assert "inventoryService.checkStock" in result.content
    with pytest.raises(ValueError):
        analyzed_index.read_file("..\\python-service\\app\\main.py")
    with pytest.raises(ValueError):
        analyzed_index.read_file("OrderService.java", 1, 100)
    with pytest.raises(ValueError):
        analyzed_index.read_file("README.md")


def test_search_symbol_supports_structured_filters(analyzed_index: AnalysisIndex) -> None:
    results = analyzed_index.search_symbols(qualified_name="demo.order.OrderService.createOrder", symbol_type="METHOD", language="JAVA")
    assert len(results) == 1
    assert results[0].filePath == "OrderService.java"
    assert analyzed_index.search_symbols(name="checkStock")[0].qualifiedName.endswith("InventoryService.checkStock")


def test_context_builder_contains_source_graph_and_evidence(analyzed_index: AnalysisIndex) -> None:
    target = next(symbol for symbol in analyzed_index.symbols.values() if symbol.qualifiedName.endswith("OrderService.createOrder"))
    context = CodeContextBuilder(analyzed_index).build(target.id)
    assert context["targetSymbol"]["qualifiedName"] == "demo.order.OrderService.createOrder"
    assert "inventoryService.checkStock" in context["sourceSnippet"]["content"]
    assert context["callees"][0]["symbol"]["qualifiedName"].endswith("InventoryService.checkStock")
    assert context["evidence"][0]["relationType"] == "CALLS"


def test_tools_are_real_registry_executions_and_validate_errors(analyzed_index: AnalysisIndex) -> None:
    registry = build_tool_registry(analyzed_index)
    assert {item.name for item in registry.definitions()} == {"searchSymbol", "readFile", "findReferences", "findCallers", "findCallees"}
    result = registry.execute("searchSymbol", {"qualifiedName": "demo.order.OrderController.createOrder"})
    assert result.success is True
    assert result.observationModel.tool == "searchSymbol"
    assert result.observationModel.success is True
    symbol_id = result.data[0]["id"]
    callees = registry.execute("findCallees", {"symbolId": symbol_id})
    assert callees.success is True
    assert callees.data[0]["symbol"]["qualifiedName"].endswith("OrderService.createOrder")
    invalid = registry.execute("readFile", {})
    assert invalid.success is False
    assert invalid.error["code"] == "TOOL_EXECUTION_ERROR"
    unknown = registry.execute("notRegistered", {})
    assert unknown.error["code"] == "UNKNOWN_TOOL"
