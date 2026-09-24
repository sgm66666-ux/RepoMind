from pathlib import Path
import time

from app.agent.loop import AgentLoop
from app.agent.provider import BaseLLMProvider, DeterministicTestProvider, LLMResponse, ToolCall
from app.agent.planner import TaskPlanner
from app.agent.tools import build_tool_registry
from app.fault.localizer import FaultLocalizer
from app.fault.stacktrace_parser import StackTraceParser
from app.repository.index import AnalysisIndex


STACK_TRACE = """java.lang.NullPointerException: stock is null
    at demo.order.InventoryService.checkStock(InventoryService.java:12)
    at demo.order.OrderService.createOrder(OrderService.java:11)
    at demo.order.OrderController.createOrder(OrderController.java:11)
"""


def test_java_stack_trace_parser_extracts_frames() -> None:
    parsed = StackTraceParser().parse(STACK_TRACE)
    assert parsed.exceptionType == "java.lang.NullPointerException"
    assert parsed.message == "stock is null"
    assert parsed.frames[0].className == "demo.order.InventoryService"
    assert parsed.frames[0].methodName == "checkStock"
    assert parsed.frames[0].fileName == "InventoryService.java"
    assert parsed.frames[0].lineNumber == 12
    assert parsed.frames[0].projectFrame is True


def test_fault_localizer_returns_deterministic_evidence() -> None:
    index = AnalysisIndex().analyze(Path(__file__).parents[3] / "demo" / "order-demo")
    result = FaultLocalizer(index).localize(STACK_TRACE)
    assert result.status == "LOCATED"
    assert result.targetFile == "InventoryService.java"
    assert result.targetSymbol.qualifiedName == "demo.order.InventoryService.checkStock"
    assert result.stackFrame.lineNumber == 12
    assert result.callees[0]["symbol"]["qualifiedName"].endswith("InventoryRepository.findStock")
    assert result.evidence[0]["type"] == "stackTrace"
    assert "evidence-based suspicion" in result.suspectedCause


def test_agent_loop_performs_multiple_tool_calls_and_stops_with_final_answer() -> None:
    index = AnalysisIndex().analyze(Path(__file__).parents[3] / "demo" / "order-demo")
    target = next(symbol for symbol in index.symbols.values() if symbol.qualifiedName.endswith("OrderController.createOrder"))
    provider = DeterministicTestProvider(
        [
            ToolCall("searchSymbol", {"qualifiedName": "demo.order.OrderController.createOrder"}),
            ToolCall("findCallees", {"symbolId": target.id}),
            ToolCall("readFile", {"filePath": "OrderController.java", "startLine": 10, "endLine": 12}),
        ],
        "TEST PROVIDER: call path and source evidence collected.",
    )
    result = AgentLoop(provider, build_tool_registry(index)).run("Trace createOrder", maxSteps=5, timeoutSeconds=5)
    assert result["status"] == "COMPLETED"
    assert result["provider"] == "TEST PROVIDER"
    assert len(result["trace"]) == 3
    assert [item["tool"] for item in result["trace"]] == ["searchSymbol", "findCallees", "readFile"]
    assert result["trace"][1]["observation"]["tool"] == "findCallees"
    assert result["trace"][1]["observation"]["success"] is True
    assert result["answer"].startswith("TEST PROVIDER:")


def test_agent_loop_enforces_max_steps() -> None:
    index = AnalysisIndex().analyze(Path(__file__).parents[3] / "demo" / "order-demo")
    provider = DeterministicTestProvider([ToolCall("searchSymbol", {"name": "Order"})] * 3, "never reached")
    result = AgentLoop(provider, build_tool_registry(index)).run("search", maxSteps=2, timeoutSeconds=5)
    assert result["status"] == "MAX_STEPS"
    assert len(result["trace"]) == 2


def test_config_capability_check_stops_before_wasting_tool_steps() -> None:
    index = AnalysisIndex().analyze(Path(__file__).parents[3] / "demo" / "repomind-agent-test-demo" / "config-demo")
    provider = DeterministicTestProvider([ToolCall("searchSymbol", {"name": "DatabaseService"})] * 2,
                                         "never reached")
    plan = TaskPlanner().plan("为什么application.yml配置没有生效？")
    result = AgentLoop(provider, build_tool_registry(index)).run("为什么application.yml配置没有生效？",
                                                                  maxSteps=2, timeoutSeconds=5, plan=plan)
    assert result["status"] == "UNSUPPORTED"
    assert result["diagnosisStatus"] == "UNSUPPORTED"
    assert result["finalDiagnosis"] is None
    assert result["trace"] == []
    assert "无法读取并关联配置文件" in result["userMessage"]


def test_agent_loop_returns_timeout_when_provider_blocks() -> None:
    class SlowProvider(BaseLLMProvider):
        name = "TEST PROVIDER"

        def complete(self, messages, tools):
            time.sleep(0.2)
            return LLMResponse(text="late")

    index = AnalysisIndex().analyze(Path(__file__).parents[3] / "demo" / "order-demo")
    result = AgentLoop(SlowProvider(), build_tool_registry(index)).run("timeout", maxSteps=2, timeoutSeconds=0.001)
    assert result["status"] == "TIMEOUT"
    assert result["trace"] == []
