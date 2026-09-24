from dataclasses import dataclass
from typing import Any, Callable

from app.domain.models import to_dict


@dataclass(frozen=True)
class Observation:
    """Structured observation returned to the Agent Loop after tool execution."""

    tool: str
    success: bool
    data: Any = None
    error: dict | None = None
    text: str = ""


@dataclass(frozen=True)
class ToolResult:
    success: bool
    data: Any = None
    error: dict | None = None
    observation: str = ""
    observationModel: Observation | None = None


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    inputSchema: dict
    executor: Callable[[dict], Any]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"Tool already registered: {definition.name}")
        self._tools[definition.name] = definition

    def definitions(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def execute(self, name: str, arguments: dict | None) -> ToolResult:
        definition = self._tools.get(name)
        if definition is None:
            message = f"Unknown tool: {name}"
            observation = Observation(name, False, error={"code": "UNKNOWN_TOOL", "message": message}, text=message)
            return ToolResult(False, error=observation.error, observation=observation.text, observationModel=observation)
        if not isinstance(arguments, dict):
            message = "Invalid tool arguments"
            error = {"code": "INVALID_ARGUMENTS", "message": "Tool arguments must be an object"}
            observation = Observation(name, False, error=error, text=message)
            return ToolResult(False, error=error, observation=message, observationModel=observation)
        try:
            data = definition.executor(arguments)
            normalized = to_dict(data)
            message = f"{definition.name} executed successfully"
            observation = Observation(definition.name, True, data=normalized, text=message)
            return ToolResult(True, normalized, observation=message, observationModel=observation)
        except (KeyError, ValueError, FileNotFoundError) as exc:
            error = {"code": "TOOL_EXECUTION_ERROR", "message": str(exc)}
            message = f"{definition.name} failed: {exc}"
            observation = Observation(definition.name, False, error=error, text=message)
            return ToolResult(False, error=error, observation=message, observationModel=observation)
        except Exception as exc:  # pragma: no cover - defensive boundary for agent calls
            error = {"code": "TOOL_EXECUTION_ERROR", "message": "Unexpected tool failure"}
            observation = Observation(definition.name, False, error=error, text=f"{definition.name} failed")
            return ToolResult(False, error=error, observation=observation.text, observationModel=observation)


def build_tool_registry(index) -> ToolRegistry:
    registry = ToolRegistry()
    registry.analysis_index = index  # Internal graph context; no new Tool definition.

    def search(arguments: dict):
        return index.search_symbols(
            name=arguments.get("name"),
            qualified_name=arguments.get("qualifiedName"),
            symbol_type=arguments.get("type"),
            language=arguments.get("language"),
        )

    def read(arguments: dict):
        file_path = arguments.get("filePath")
        if not file_path:
            raise ValueError("filePath is required")
        return index.read_file(file_path, arguments.get("startLine"), arguments.get("endLine"))

    def symbol_argument(arguments: dict):
        symbol_id = arguments.get("symbolId")
        if not symbol_id:
            raise ValueError("symbolId is required")
        if index.get_symbol(symbol_id) is None:
            raise KeyError(f"Symbol not found: {symbol_id}")
        return symbol_id

    registry.register(ToolDefinition("searchSymbol", "Search structured code Symbols.", {"type": "object", "properties": {"name": {"type": "string"}, "qualifiedName": {"type": "string"}, "type": {"type": "string"}, "language": {"type": "string"}}}, search))
    registry.register(ToolDefinition("readFile", "Read a bounded source range inside the analyzed repository.", {"type": "object", "required": ["filePath"]}, read))
    registry.register(ToolDefinition("findReferences", "Find resolved references to a Symbol.", {"type": "object", "required": ["symbolId"]}, lambda args: index.references_for(symbol_argument(args))))
    registry.register(ToolDefinition("findCallers", "Find resolved callers of a Symbol.", {"type": "object", "required": ["symbolId"]}, lambda args: index.callGraph.findCallers(symbol_argument(args)) if index.callGraph else []))
    registry.register(ToolDefinition("findCallees", "Find resolved callees of a Symbol.", {"type": "object", "required": ["symbolId"]}, lambda args: index.callGraph.findCallees(symbol_argument(args)) if index.callGraph else []))
    return registry
