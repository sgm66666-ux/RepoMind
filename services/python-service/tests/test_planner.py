import asyncio
from pathlib import Path

import httpx

from app.agent.loop import AgentLoop
from app.agent.planner import TaskPlanner
from app.agent.provider import BaseLLMProvider, LLMResponse, ToolCall
from app.agent.tools import build_tool_registry
from app.main import app, index
from app.repository.index import AnalysisIndex


def test_runtime_error_plan_uses_exception_evidence_path() -> None:
    plan = TaskPlanner().plan("为什么OrderService.createOrder出现NullPointerException？")
    assert plan.task_type == "RUNTIME_ERROR"
    assert plan.target_keywords == ["createOrder"]
    assert plan.target_source == "QUERY"
    assert plan.preferred_tools == ["searchSymbol", "findCallers", "findCallees", "readFile"]
    assert "error_value_origin" in plan.required_evidence


def test_business_logic_plan_marks_inferred_keyword_as_unverified() -> None:
    plan = TaskPlanner().plan("为什么订单价格计算错误？")
    assert plan.task_type == "BUSINESS_LOGIC_ERROR"
    assert plan.target_keywords == ["calculatePrice", "price"]
    assert plan.target_source == "HEURISTIC"
    assert plan.preferred_tools == ["searchSymbol", "findCallers", "readFile"]
    assert {"input_origin", "return_value_impact"}.issubset(plan.required_evidence)


def test_call_chain_and_configuration_plans() -> None:
    planner = TaskPlanner()
    call_plan = planner.plan("追踪用户注册失败调用路径")
    assert call_plan.task_type == "CALL_CHAIN_ANALYSIS"
    assert call_plan.preferred_tools == ["searchSymbol", "findCallers", "findCallees"]
    assert call_plan.target_source == "UNSPECIFIED"
    config_plan = planner.plan("为什么数据库配置缺失？")
    assert config_plan.task_type == "CONFIGURATION_ERROR"
    assert "findReferences" in config_plan.preferred_tools


def test_planned_agent_loop_passes_plan_and_observations_without_executing_planner_tools() -> None:
    pricing = Path(__file__).parents[3] / "demo" / "repomind-agent-test-demo" / "logic-bug-demo"
    analyzed = AnalysisIndex().analyze(pricing)
    target = next(symbol for symbol in analyzed.symbols.values() if symbol.qualifiedName == "PriceService.calculatePrice")

    class RecordingProvider(BaseLLMProvider):
        name = "TEST PROVIDER"

        def __init__(self) -> None:
            self.messages: list[list[dict]] = []
            self.calls = iter([
                ToolCall("searchSymbol", {"name": "calculatePrice"}),
                ToolCall("findCallers", {"symbolId": target.id}),
                ToolCall("readFile", {"filePath": "src/PriceService.java", "startLine": 1, "endLine": 9}),
                ToolCall("readFile", {"filePath": "src/OrderService.java", "startLine": 1, "endLine": 8}),
            ])

        def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
            self.messages.append(list(messages))
            call = next(self.calls, None)
            return LLMResponse(toolCall=call) if call else LLMResponse(text="TEST PROVIDER: source inspected")

    plan = TaskPlanner().plan("为什么订单价格计算错误？")
    provider = RecordingProvider()
    result = AgentLoop(provider, build_tool_registry(analyzed)).run("为什么订单价格计算错误？", 7, 5, plan)
    assert result["status"] == "COMPLETED"
    assert result["plan"] == plan.as_dict()
    assert [step["tool"] for step in result["trace"]] == ["searchSymbol", "findCallers", "readFile", "readFile"]
    assert all(step["success"] for step in result["trace"])
    assert "BUSINESS_LOGIC_ERROR" in provider.messages[0][0]["content"]
    assert "OrderService.createOrder" in provider.messages[2][-1]["content"]
    assert "priceService.calculatePrice" in provider.messages[-1][-1]["content"]


def test_agent_api_returns_actual_plan_with_test_provider(monkeypatch) -> None:
    from app.agent.provider import DeterministicTestProvider

    index.analyze(Path(__file__).parents[3] / "demo" / "repomind-agent-test-demo" / "logic-bug-demo")
    target = next(symbol for symbol in index.symbols.values() if symbol.qualifiedName.endswith("PriceService.calculatePrice"))
    provider = DeterministicTestProvider(
        [ToolCall("searchSymbol", {"name": "calculatePrice"}), ToolCall("findCallers", {"symbolId": target.id})],
        "TEST PROVIDER: observations collected",
    )
    monkeypatch.setattr("app.main.create_llm_provider", lambda: provider)

    async def request() -> httpx.Response:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/agent/chat", json={"question": "为什么订单价格计算错误？", "maxSteps": 5})

    response = asyncio.run(request())
    assert response.status_code == 200
    data = response.json()
    assert data["plan"]["task_type"] == "BUSINESS_LOGIC_ERROR"
    assert data["provider"] == "TEST PROVIDER"
    assert [step["tool"] for step in data["trace"]] == ["searchSymbol", "findCallers"]
