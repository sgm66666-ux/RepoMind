"""Reproducible multi-step Agent Trace using the explicitly marked TEST PROVIDER."""

import json
from pathlib import Path

from app.agent.loop import AgentLoop
from app.agent.provider import DeterministicTestProvider, ToolCall
from app.agent.tools import build_tool_registry
from app.repository.index import AnalysisIndex


def main() -> None:
    repository = Path(__file__).parents[1] / "demo" / "order-demo"
    index = AnalysisIndex().analyze(repository)
    target = next(
        symbol for symbol in index.symbols.values()
        if symbol.qualifiedName.endswith("OrderController.createOrder")
    )
    provider = DeterministicTestProvider(
        [
            ToolCall("searchSymbol", {"qualifiedName": target.qualifiedName}),
            ToolCall("findCallees", {"symbolId": target.id}),
            ToolCall("readFile", {"filePath": "InventoryService.java", "startLine": 10, "endLine": 13}),
        ],
        "TEST PROVIDER: collected symbol, call-graph, and source observations.",
    )
    result = AgentLoop(provider, build_tool_registry(index)).run(
        "Trace the order creation path and inspect the stock check.",
        maxSteps=5,
        timeoutSeconds=5,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
