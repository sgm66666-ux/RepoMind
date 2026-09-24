import json
from pathlib import Path

from app.agent.loop import AgentLoop
import pytest

from app.agent.provider import (
    OllamaProvider,
    OpenAICompatibleProvider,
    ProviderConfigurationError,
    ProviderRequestError,
    ToolCall,
    create_llm_provider,
)
from app.agent.tools import build_tool_registry
from app.repository.index import AnalysisIndex


class FakeResponse:
    def __init__(self, body: dict) -> None:
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self) -> bytes:
        return json.dumps(self.body).encode("utf-8")


def test_ollama_provider_uses_native_tool_calling(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "searchSymbol", "arguments": {"name": "InventoryService"}}}
                    ],
                }
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OllamaProvider("http://localhost:11434", "qwen2.5-coder:14b", 15)
    response = provider.complete(
        [{"role": "user", "content": "Find InventoryService"}],
        [{"type": "function", "function": {"name": "searchSymbol", "parameters": {"type": "object"}}}],
    )

    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["timeout"] == 15
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["messages"][0]["role"] == "system"
    assert captured["payload"]["tools"][0]["function"]["name"] == "searchSymbol"
    assert response.toolCall == ToolCall("searchSymbol", {"name": "InventoryService"})


def test_provider_selection_prefers_configured_ollama(monkeypatch) -> None:
    for name in (
        "REPOMIND_LLM_PROVIDER",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "REPOMIND_LLM_BASE_URL",
        "REPOMIND_LLM_MODEL",
        "REPOMIND_LLM_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    assert create_llm_provider() is None

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5-coder:14b")
    provider = create_llm_provider()
    assert isinstance(provider, OllamaProvider)
    assert provider.name == "ollama:qwen2.5-coder:14b"


def test_provider_selection_keeps_openai_compatible_and_rejects_partial_ollama(monkeypatch) -> None:
    for name in (
        "REPOMIND_LLM_PROVIDER",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "REPOMIND_LLM_BASE_URL",
        "REPOMIND_LLM_MODEL",
        "REPOMIND_LLM_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("REPOMIND_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    with pytest.raises(ProviderConfigurationError, match="OLLAMA_MODEL"):
        create_llm_provider()

    monkeypatch.setenv("REPOMIND_LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("REPOMIND_LLM_BASE_URL", "http://localhost:9999/v1")
    monkeypatch.setenv("REPOMIND_LLM_MODEL", "test-model")
    monkeypatch.setenv("REPOMIND_LLM_API_KEY", "test-key")
    assert isinstance(create_llm_provider(), OpenAICompatibleProvider)


def test_ollama_provider_rejects_empty_response(monkeypatch) -> None:
    monkeypatch.setattr("urllib.request.urlopen", lambda request, timeout: FakeResponse({"message": {"content": ""}}))
    provider = OllamaProvider("http://localhost:11434", "qwen2.5-coder:14b")
    with pytest.raises(ProviderRequestError, match="neither a Tool Call nor a final answer"):
        provider.complete([{"role": "user", "content": "Why?"}], [])


def test_ollama_provider_marks_strict_json_tool_compatibility(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse(
            {
                "message": {
                    "content": '{"name":"searchSymbol","arguments":{"name":"checkStock","type":"method"}}'
                }
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OllamaProvider("http://localhost:11434", "qwen2.5-coder:14b")
    response = provider.complete(
        [{"role": "user", "content": "Find checkStock"}],
        [{"type": "function", "function": {"name": "searchSymbol", "parameters": {"type": "object"}}}],
    )

    assert response.toolCall == ToolCall("searchSymbol", {"name": "checkStock", "type": "METHOD"})
    assert provider.name == "ollama:qwen2.5-coder:14b:json-tool-compat"
    assert response.toolCallContent == '{"name":"searchSymbol","arguments":{"name":"checkStock","type":"method"}}'
    history = provider._messages([
        {"role": "assistant", "tool_call": {"name": response.toolCall.name, "arguments": response.toolCall.arguments}, "tool_call_content": response.toolCallContent},
        {"role": "tool", "name": "searchSymbol", "content": '{"observation":{"success":true}}'},
    ])
    assert history[1]["content"] == response.toolCallContent
    assert "tool_calls" not in history[1]


def test_ollama_provider_accepts_only_a_complete_fenced_json_call(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse(
            {
                "message": {
                    "content": '```json\n{"name":"findCallees","arguments":{"symbolId":"symbol-1"}}\n```'
                }
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OllamaProvider("http://localhost:11434", "qwen2.5-coder:14b")
    response = provider.complete(
        [{"role": "user", "content": "Find callees"}],
        [{"type": "function", "function": {"name": "findCallees", "parameters": {"type": "object"}}}],
    )

    assert response.toolCall == ToolCall("findCallees", {"symbolId": "symbol-1"})


def test_ollama_provider_drives_agent_tool_flow(monkeypatch) -> None:
    index = AnalysisIndex().analyze(Path(__file__).parents[3] / "demo" / "order-demo")
    target = next(
        symbol for symbol in index.symbols.values() if symbol.qualifiedName == "demo.order.InventoryService.checkStock"
    )
    responses = iter(
        [
            {"message": {"tool_calls": [{"function": {"name": "searchSymbol", "arguments": {"qualifiedName": target.qualifiedName}}}]}},
            {"message": {"tool_calls": [{"function": {"name": "findCallees", "arguments": {"symbolId": target.id}}}]}},
            {"message": {"tool_calls": [{"function": {"name": "readFile", "arguments": {"filePath": "InventoryService.java", "startLine": 10, "endLine": 15}}}]}},
            {"message": {"content": "InventoryService.java:12 dereferences stock returned by InventoryRepository.findStock."}},
        ]
    )
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(json.loads(request.data.decode("utf-8")))
        return FakeResponse(next(responses))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    provider = OllamaProvider("http://localhost:11434", "qwen2.5-coder:14b")
    result = AgentLoop(provider, build_tool_registry(index)).run(
        "Why does InventoryService.checkStock throw NullPointerException?", maxSteps=6, timeoutSeconds=5
    )

    assert result["status"] == "COMPLETED"
    assert result["provider"] == "ollama:qwen2.5-coder:14b"
    assert [step["tool"] for step in result["trace"]] == ["searchSymbol", "findCallees", "readFile"]
    assert any(target.id in message.get("content", "") for message in requests[1]["messages"])
    assert requests[1]["messages"][-1]["content"].startswith("Execution memory")
    assert any("InventoryRepository.findStock" in message.get("content", "") for message in requests[2]["messages"])
    assert any("stock.available" in message.get("content", "") for message in requests[3]["messages"])
    assert "InventoryService.java:12" in result["answer"]
