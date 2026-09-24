import json
import os
import re
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict


@dataclass(frozen=True)
class LLMResponse:
    text: str | None = None
    toolCall: ToolCall | None = None
    toolCallContent: str | None = None


class BaseLLMProvider:
    name = "base"

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        raise NotImplementedError


class ProviderConfigurationError(RuntimeError):
    pass


class ProviderRequestError(RuntimeError):
    pass


OLLAMA_SYSTEM_PROMPT = """You are RepoMind's code-investigation Agent. The repository is not in your prompt.
Use only the supplied code-analysis Tools and their Observations as evidence. Never guess source code, call
relationships, file paths, line numbers, or root causes. Do not ask for the whole repository.

First understand the user's task type and review the supplied Execution Plan. The Plan is a deterministic hypothesis,
not a Tool result or proof that its target keyword exists. Second, adapt that plan after each Observation. Third,
call one Tool per turn using IDs and file ranges from observed results. Fourth, answer only from code evidence.
If a search is empty, try a broader observed search or report that the target could not be located; do not invent it.
The AgentLoop supplies Observation-derived execution memory on every turn. Compare its evidence checklist and
missing_evidence before finishing. Never repeat an identical Tool Call after it returned no new evidence or was
blocked as DUPLICATE_CALL. If searchSymbol returns no Symbol, remove restrictive filters, try the method name
without a class/module prefix, and consider the language indicated by the error type; stop after limited fallbacks.
If a Symbol is found but source evidence is missing, prefer readFile over repeated Symbol searches. If a caller or
callee relation is found but source context is missing, inspect the observed file rather than traversing the same
edge again. Tool selection remains yours; policy suggestions are not Tool results or proof of a bug.

For RUNTIME_ERROR, inspect the exception location, caller/callee chain and the origin of the null or error state.
Prefer searchSymbol, findCallers, findCallees, then readFile for the target and relevant callee. A call alone does
not prove NullPointerException. For BUSINESS_LOGIC_ERROR, inspect the target method implementation, its callers,
input parameter origins and return-value impact; prefer searchSymbol, findCallers, then readFile of the target and
relevant caller. Do not assume a runtime failure when the user asks about a wrong business result. For
CALL_CHAIN_ANALYSIS, use resolved caller/callee observations or the separately labelled AST_RESOLVED_CALL_GRAPH
path supplied by execution memory, not a generic bug diagnosis. Verify EVERY edge against one of those evidence
sources; the graph path is static-analysis evidence, not a Tool Call or runtime proof. If only a path prefix is verified,
report that prefix and identify the missing edge; do not call it a complete chain. For CONFIGURATION_ERROR, inspect code that reads the setting and its callers; do not assert a deployed
configuration value from source alone.

Return only one Tool Call per turn. After sufficient evidence, answer with the file path, Symbol, relevant code
location, observed call relationship, diagnosis, and uncertainty. Use requestedRange.startLine and returned source
lines for exact locations. Explicitly distinguish Observation facts from inference; if evidence is insufficient,
say so instead of guessing.

During the Tool phase, emit a Tool Call as usual. During the FINAL phase, emit ONLY one JSON object using this
FinalDiagnosis schema (no Markdown):
{"issue_type":"BUSINESS_LOGIC_ERROR","summary":"...","location":{"file":"...","line":null,"symbol":"..."},
"root_cause":"...","evidence":[{"file":"...","line":null,"symbol":"...","code":"exact observed source line","reason":"..."}],
"call_chain":["Caller.method","Target.method"],"fix_suggestion":"...","uncertainty":"..."}.
Use the actual task type from the Plan. Every evidence item must match a successful Tool Observation exactly; use
null for unknown file, line, Symbol, or code. For call_chain, include only resolved CALLS edges from Tool Observations
or the explicitly labelled AST graph path. The evidence
array describes FACTS, while root_cause is an INFERENCE. For business logic, source proves the current formula but
does not prove the correct business formula unless a requirement or test was observed. Do not claim a specific
replacement formula without such evidence. If evidence is insufficient, use an empty evidence array and say so.
For runtime errors, find both the invalid value's source and the operation triggering the exception; include both
exact observed source lines in evidence when available. Planner target keywords, including HEURISTIC targets, are
never evidence. Do not finish early while an actionable evidence gap remains and a fresh Tool can close it.
FinalDiagnosis JSON must not contain a Tool Call name or arguments object.

Tool enum values are uppercase: language is JAVA or PYTHON; type is CLASS, INTERFACE, METHOD, or FUNCTION. Omit a
filter rather than inventing its value. If the runtime cannot emit a native Tool Call, output only one exact JSON
object in this form, without Markdown: {"name":"toolName","arguments":{...}}. Never mix a Tool Call with prose.
"""


def _tool_arguments(value: Any) -> dict:
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("LLM returned invalid JSON tool arguments") from exc
    if not isinstance(value, dict):
        raise ProviderRequestError("LLM tool arguments must be a JSON object")
    for enum_key in ("language", "type"):
        if isinstance(value.get(enum_key), str):
            value[enum_key] = value[enum_key].upper()
    return value


class OpenAICompatibleProvider(BaseLLMProvider):
    name = "openai-compatible"

    def __init__(self, base_url: str | None = None, model: str | None = None, api_key: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("REPOMIND_LLM_BASE_URL", "")).rstrip("/")
        self.model = model or os.getenv("REPOMIND_LLM_MODEL", "")
        self.api_key = api_key or os.getenv("REPOMIND_LLM_API_KEY", "")

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        if not self.base_url or not self.model or not self.api_key:
            raise RuntimeError("OpenAI-compatible provider requires REPOMIND_LLM_BASE_URL, REPOMIND_LLM_MODEL and REPOMIND_LLM_API_KEY")
        payload = json.dumps({"model": self.model, "messages": messages, "tools": tools}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
        message = body["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        if calls:
            call = calls[0]["function"]
            return LLMResponse(toolCall=ToolCall(call["name"], json.loads(call.get("arguments") or "{}")))
        return LLMResponse(text=message.get("content") or "")


class OllamaProvider(BaseLLMProvider):
    """Real local LLM provider using Ollama's native /api/chat Tool Calling."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        request_timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "")).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", "")
        timeout_value = (
            request_timeout_seconds
            if request_timeout_seconds is not None
            else float(os.getenv("OLLAMA_REQUEST_TIMEOUT_SECONDS", "120"))
        )
        if timeout_value <= 0:
            raise ProviderConfigurationError("OLLAMA_REQUEST_TIMEOUT_SECONDS must be positive")
        self.request_timeout_seconds = timeout_value
        self.name = f"ollama:{self.model}" if self.model else "ollama"

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        if not self.configured:
            raise ProviderConfigurationError("Ollama provider requires OLLAMA_BASE_URL and OLLAMA_MODEL")
        normalized_messages = self._messages(messages)
        if not tools:
            normalized_messages.insert(1, {"role": "system", "content":
                                       "FINAL-ONLY TURN. The Tool budget is exhausted. No Tool Call is permitted. "
                                       "Do not output {\"name\":...} or tool_calls. Use only existing Observations and "
                                       "return one FinalDiagnosis JSON object; explicitly state evidence gaps."})
        payload = json.dumps(
            {
                "model": self.model,
                "messages": normalized_messages,
                "tools": tools,
                "stream": False,
                "options": {"temperature": 0},
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderRequestError(f"Ollama returned HTTP {exc.code}: {detail[:500]}") from exc
        except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
            raise ProviderRequestError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProviderRequestError("Ollama returned an invalid JSON response") from exc

        message = body.get("message")
        if not isinstance(message, dict):
            raise ProviderRequestError("Ollama response is missing message")
        calls = message.get("tool_calls") or []
        if calls:
            function = calls[0].get("function") or {}
            name = function.get("name")
            if not isinstance(name, str) or not name:
                raise ProviderRequestError("Ollama returned a Tool Call without a function name")
            return LLMResponse(toolCall=ToolCall(name, _tool_arguments(function.get("arguments"))))
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ProviderRequestError("Ollama returned neither a Tool Call nor a final answer")
        compatibility_call = self._json_compatibility_call(content, tools)
        if compatibility_call is not None:
            self.name = f"ollama:{self.model}:json-tool-compat"
            return LLMResponse(toolCall=compatibility_call, toolCallContent=content)
        return LLMResponse(text=content)

    @staticmethod
    def _json_compatibility_call(content: str, tools: list[dict]) -> ToolCall | None:
        """Parse an exact JSON object or single JSON code block when Ollama omits native tool_calls."""

        candidate_text = content.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", candidate_text, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            candidate_text = fenced.group(1)
        try:
            candidate = json.loads(candidate_text)
        except json.JSONDecodeError:
            return None
        if not isinstance(candidate, dict):
            return None
        function = candidate.get("function") if isinstance(candidate.get("function"), dict) else candidate
        name = function.get("name")
        if not isinstance(name, str) or not name:
            return None
        allowed_names = {
            tool.get("function", {}).get("name")
            for tool in tools
            if isinstance(tool, dict) and isinstance(tool.get("function"), dict)
        }
        if name not in allowed_names:
            raise ProviderRequestError(f"Ollama requested an unknown Tool: {name}")
        return ToolCall(name, _tool_arguments(function.get("arguments")))

    @staticmethod
    def _messages(messages: list[dict]) -> list[dict]:
        normalized: list[dict] = [{"role": "system", "content": OLLAMA_SYSTEM_PROMPT}]
        for message in messages:
            role = message.get("role")
            if role == "assistant" and isinstance(message.get("tool_call"), dict):
                call = message["tool_call"]
                if isinstance(message.get("tool_call_content"), str):
                    normalized.append({"role": "assistant", "content": message["tool_call_content"]})
                    continue
                normalized.append(
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": call.get("name"),
                                    "arguments": call.get("arguments") or {},
                                }
                            }
                        ],
                    }
                )
            elif role == "tool":
                normalized.append(
                    {
                        "role": "tool",
                        "content": str(message.get("content") or ""),
                        "tool_name": message.get("name"),
                    }
                )
            else:
                normalized.append({"role": role, "content": str(message.get("content") or "")})
        return normalized

def create_llm_provider() -> BaseLLMProvider | None:
    """Select a configured real provider without ever falling back to the test provider."""

    requested = os.getenv("REPOMIND_LLM_PROVIDER", "").strip().lower()
    ollama_configured = bool(os.getenv("OLLAMA_BASE_URL", "") or os.getenv("OLLAMA_MODEL", ""))
    openai_configured = bool(
        os.getenv("REPOMIND_LLM_BASE_URL", "")
        or os.getenv("REPOMIND_LLM_MODEL", "")
        or os.getenv("REPOMIND_LLM_API_KEY", "")
    )

    if requested not in {"", "ollama", "openai-compatible"}:
        raise ProviderConfigurationError(f"Unsupported REPOMIND_LLM_PROVIDER: {requested}")
    if requested == "ollama" or (not requested and ollama_configured):
        provider = OllamaProvider()
        if not provider.configured:
            raise ProviderConfigurationError("Ollama provider requires OLLAMA_BASE_URL and OLLAMA_MODEL")
        return provider
    if requested == "openai-compatible" or (not requested and openai_configured):
        provider = OpenAICompatibleProvider()
        if not provider.base_url or not provider.model or not provider.api_key:
            raise ProviderConfigurationError(
                "OpenAI-compatible provider requires REPOMIND_LLM_BASE_URL, REPOMIND_LLM_MODEL and REPOMIND_LLM_API_KEY"
            )
        return provider
    return None


class DeterministicTestProvider(BaseLLMProvider):
    """Test-only provider; never presented as a real LLM."""

    name = "TEST PROVIDER"

    def __init__(self, calls: list[ToolCall], final_text: str) -> None:
        self.calls = list(calls)
        self.final_text = final_text

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        if self.calls:
            return LLMResponse(toolCall=self.calls.pop(0))
        return LLMResponse(text=self.final_text)
