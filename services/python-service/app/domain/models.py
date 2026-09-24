from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class Language(str, Enum):
    JAVA = "JAVA"
    PYTHON = "PYTHON"


class SymbolType(str, Enum):
    CLASS = "CLASS"
    INTERFACE = "INTERFACE"
    METHOD = "METHOD"
    FUNCTION = "FUNCTION"


class RelationType(str, Enum):
    IMPORTS = "IMPORTS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    CALLS = "CALLS"
    REFERENCES = "REFERENCES"


@dataclass(frozen=True)
class SourceFile:
    filePath: str
    language: Language
    content: str


@dataclass(frozen=True)
class Symbol:
    id: str
    name: str
    qualifiedName: str
    type: SymbolType
    language: Language
    filePath: str
    startLine: int
    endLine: int
    parentSymbolId: str | None = None
    signature: str | None = None
    module: str | None = None


@dataclass(frozen=True)
class Relation:
    id: str
    sourceSymbolId: str | None
    targetSymbolId: str | None
    targetName: str
    type: RelationType
    filePath: str
    line: int
    resolved: bool
    evidence: str
    resolutionMethod: str | None = None


@dataclass(frozen=True)
class RequestedRange:
    startLine: int
    endLine: int


@dataclass(frozen=True)
class FileReadResult:
    filePath: str
    language: Language
    requestedRange: RequestedRange
    content: str


@dataclass(frozen=True)
class StackFrame:
    className: str | None
    methodName: str | None
    fileName: str | None
    lineNumber: int | None
    raw: str
    projectFrame: bool = True


@dataclass(frozen=True)
class ParsedStackTrace:
    exceptionType: str
    message: str | None
    frames: list[StackFrame]
    raw: str


@dataclass(frozen=True)
class FaultLocalizationResult:
    exception: ParsedStackTrace
    targetFile: str | None
    targetSymbol: Symbol | None
    lineRange: RequestedRange | None
    stackFrame: StackFrame | None
    callers: list[dict]
    callees: list[dict]
    references: list[Relation]
    evidence: list[dict]
    suspectedCause: str
    confidence: str
    status: str


def to_dict(value: Any) -> Any:
    """Convert domain dataclasses and enums to JSON-friendly values."""
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {key: to_dict(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [to_dict(item) for item in value]
    if isinstance(value, dict):
        return {key: to_dict(item) for key, item in value.items()}
    return value
