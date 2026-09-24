from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from app.domain.models import RelationType, to_dict
from app.agent.loop import AgentLoop
from app.agent.planner import TaskPlanner
from app.agent.provider import ProviderConfigurationError, ProviderRequestError, create_llm_provider
from app.agent.tools import build_tool_registry
from app.analysis.context_builder import CodeContextBuilder
from app.fault.localizer import FaultLocalizer
from app.repository.index import AnalysisIndex


class RepositoryAnalysisRequest(BaseModel):
    path: str


class FileReadRequest(BaseModel):
    filePath: str
    startLine: int | None = None
    endLine: int | None = None


class ContextRequest(BaseModel):
    symbolId: str
    maxCallers: int = 5
    maxCallees: int = 5
    maxReferences: int = 10
    maxSnippetLines: int = 40


class FaultLocalizationRequest(BaseModel):
    stackTrace: str


class AgentChatRequest(BaseModel):
    question: str
    maxSteps: int = 8
    timeoutSeconds: float = 30


app = FastAPI(title="RepoMind Code Intelligence Service", version="0.1.0")
index = AnalysisIndex()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/analysis/status")
def analysis_status() -> dict:
    """Report in-memory index readiness separately from process liveness."""
    return {"analysisReady": index.analysisReady,
            "repositoryPath": str(index.repositoryPath) if index.analysisReady and index.repositoryPath else None,
            "sourceFileCount": len(index.sourceFiles) if index.analysisReady else 0,
            "symbolCount": len(index.symbols) if index.analysisReady else 0}


@app.post("/analysis/repository")
def analyze_repository(request: RepositoryAnalysisRequest) -> dict:
    try:
        index.analyze(Path(request.path))
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    call_relations = [relation for relation in index.relations if relation.type == RelationType.CALLS]
    language_breakdown: dict[str, int] = {}
    for source_file in index.sourceFiles.values():
        language = source_file.language.value
        language_breakdown[language] = language_breakdown.get(language, 0) + 1
    return {
        "repositoryPath": str(Path(request.path).resolve()),
        "analysisReady": index.analysisReady,
        "sourceFileCount": len(index.sourceFiles),
        "symbolCount": len(index.symbols),
        "relationCount": len(index.relations),
        "resolvedCallCount": sum(1 for relation in call_relations if relation.resolved),
        "unresolvedCallCount": sum(1 for relation in call_relations if not relation.resolved),
        "languageBreakdown": language_breakdown,
        "scanIssues": [to_dict(issue) for issue in index.issues],
    }


@app.get("/call-graph")
def get_call_graph(includeUnresolved: bool = False) -> dict:
    if index.repositoryPath is None:
        raise HTTPException(status_code=409, detail="No repository has been analyzed")
    all_calls = [relation for relation in index.relations if relation.type == RelationType.CALLS]
    visible_calls = [relation for relation in all_calls if relation.resolved or includeUnresolved]
    symbol_ids = {
        symbol_id
        for relation in visible_calls
        for symbol_id in (relation.sourceSymbolId, relation.targetSymbolId)
        if symbol_id is not None
    }
    return {
        "nodes": [to_dict(index.symbols[symbol_id]) for symbol_id in symbol_ids if symbol_id in index.symbols],
        "edges": [to_dict(relation) for relation in visible_calls],
        "resolvedCallCount": sum(1 for relation in all_calls if relation.resolved),
        "unresolvedCallCount": sum(1 for relation in all_calls if not relation.resolved),
    }


@app.get("/demo/order-demo")
def get_order_demo() -> dict:
    repository = Path(__file__).resolve().parents[3] / "demo" / "order-demo"
    stack_trace = repository / "expected-stacktrace.txt"
    if not repository.is_dir() or not stack_trace.is_file():
        raise HTTPException(status_code=404, detail="Order demo assets are unavailable")
    return {
        "repositoryPath": str(repository),
        "stackTrace": stack_trace.read_text(encoding="utf-8"),
    }


@app.get("/symbols")
def list_symbols(
    query: str | None = Query(default=None),
    name: str | None = Query(default=None),
    qualifiedName: str | None = Query(default=None),
    type: str | None = Query(default=None),
    language: str | None = Query(default=None),
) -> list[dict]:
    if any(value is not None for value in (name, qualifiedName, type, language)):
        return [to_dict(symbol) for symbol in index.search_symbols(name, qualifiedName, type, language)]
    return [to_dict(symbol) for symbol in index.find_symbols(query)]


@app.get("/files/read")
def read_file(filePath: str, startLine: int | None = None, endLine: int | None = None) -> dict:
    try:
        return to_dict(index.read_file(filePath, startLine, endLine))
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/context")
def build_context(request: ContextRequest) -> dict:
    try:
        return CodeContextBuilder(index).build(
            request.symbolId,
            request.maxCallers,
            request.maxCallees,
            request.maxReferences,
            request.maxSnippetLines,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _graph_result(symbol_id: str, callers: bool) -> list[dict]:
    if index.get_symbol(symbol_id) is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    if index.callGraph is None:
        return []
    values = index.callGraph.findCallers(symbol_id) if callers else index.callGraph.findCallees(symbol_id)
    return [to_dict(value) for value in values]


@app.get("/symbols/{symbol_id:path}/callers")
def find_callers(symbol_id: str) -> list[dict]:
    return _graph_result(symbol_id, callers=True)


@app.get("/symbols/{symbol_id:path}/callees")
def find_callees(symbol_id: str) -> list[dict]:
    return _graph_result(symbol_id, callers=False)


@app.get("/symbols/{symbol_id:path}")
def get_symbol(symbol_id: str) -> dict:
    symbol = index.get_symbol(symbol_id)
    if symbol is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return to_dict(symbol)


@app.post("/fault-localization")
def fault_localization(request: FaultLocalizationRequest) -> dict:
    try:
        return to_dict(FaultLocalizer(index).localize(request.stackTrace))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/agent/chat")
def agent_chat(request: AgentChatRequest) -> dict:
    try:
        provider = create_llm_provider()
        if provider is None:
            raise HTTPException(status_code=503, detail="No LLM provider configured; use DeterministicTestProvider only in tests")
        if not index.analysisReady:
            raise HTTPException(status_code=409, detail="Repository analysis is not ready")
        plan = TaskPlanner().plan(request.question)
        return AgentLoop(provider, build_tool_registry(index)).run(request.question, request.maxSteps, request.timeoutSeconds, plan)
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ProviderRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
