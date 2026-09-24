from pathlib import Path
import pytest

from app.analysis.call_graph import CallGraph
from app.analysis.call_path import CallPathFinder
from app.analysis.relation_extractor import RelationExtractor
from app.analysis.resolver import SymbolResolver
from app.analysis.symbol_extractor import JavaSymbolExtractor, PythonSymbolExtractor
from app.domain.models import Language, Relation, RelationType, SourceFile, Symbol, SymbolType
from app.parsers.java_parser import JavaParser
from app.parsers.python_parser import PythonParser
from app.repository.index import AnalysisIndex


def test_java_relations_resolve_simple_field_calls() -> None:
    source = """class Controller {
  private Service service;
  void create() { service.run(); }
}
class Service {
  void run() {}
}
"""
    file = SourceFile("Demo.java", Language.JAVA, source)
    tree = JavaParser().parse(source)
    symbols = JavaSymbolExtractor().extract(tree, source, file.filePath)
    relations = RelationExtractor().extract(file, tree, symbols, SymbolResolver(symbols))
    calls = [relation for relation in relations if relation.type == RelationType.CALLS]
    assert len(calls) == 1
    assert calls[0].resolved is True
    assert calls[0].targetName == "run"
    assert calls[0].resolutionMethod == "RECEIVER_TYPE_BINDING"


def test_java_import_extends_and_implements_relations_are_extracted() -> None:
    source = """import java.util.List;
interface Contract {}
class Base {}
class Demo extends Base implements Contract {
  List<String> values;
}
"""
    file = SourceFile("Demo.java", Language.JAVA, source)
    tree = JavaParser().parse(source)
    symbols = JavaSymbolExtractor().extract(tree, source, file.filePath)
    relations = RelationExtractor().extract(file, tree, symbols, SymbolResolver(symbols))
    relation_types = {(relation.type, relation.targetName, relation.resolved) for relation in relations}
    assert (RelationType.IMPORTS, "java.util.List", False) in relation_types
    assert (RelationType.EXTENDS, "Base", True) in relation_types
    assert (RelationType.IMPLEMENTS, "Contract", True) in relation_types


def test_python_relations_resolve_unique_function_call() -> None:
    source = "def run():\n    pass\n\ndef start():\n    run()\n"
    file = SourceFile("demo.py", Language.PYTHON, source)
    tree = PythonParser().parse(source)
    symbols = PythonSymbolExtractor().extract(tree, source, file.filePath)
    relations = RelationExtractor().extract(file, tree, symbols, SymbolResolver(symbols))
    call = next(relation for relation in relations if relation.type == RelationType.CALLS)
    assert call.resolved is True
    assert call.targetSymbolId is not None


def test_unresolved_call_is_not_added_to_call_graph() -> None:
    source = "class Demo { void run() { missing(); } }"
    file = SourceFile("Demo.java", Language.JAVA, source)
    tree = JavaParser().parse(source)
    symbols = JavaSymbolExtractor().extract(tree, source, file.filePath)
    relations = RelationExtractor().extract(file, tree, symbols, SymbolResolver(symbols))
    unresolved = next(relation for relation in relations if relation.type == RelationType.CALLS)
    assert unresolved.resolved is False
    graph = CallGraph(symbols, relations)
    demo = next(symbol for symbol in symbols if symbol.name == "run")
    assert graph.findCallees(demo.id) == []


def test_index_builds_demo_call_graph() -> None:
    demo_path = Path(__file__).parents[3] / "demo" / "order-demo"
    index = AnalysisIndex().analyze(demo_path)
    controller = next(symbol for symbol in index.symbols.values() if symbol.qualifiedName == "demo.order.OrderController.createOrder")
    service = next(symbol for symbol in index.symbols.values() if symbol.qualifiedName == "demo.order.OrderService.createOrder")
    inventory = next(symbol for symbol in index.symbols.values() if symbol.qualifiedName == "demo.order.InventoryService.checkStock")
    assert [item["symbol"].qualifiedName for item in index.callGraph.findCallees(controller.id)] == [service.qualifiedName]
    assert [item["symbol"].qualifiedName for item in index.callGraph.findCallees(service.id)] == [inventory.qualifiedName]
    assert [item["symbol"].qualifiedName for item in index.callGraph.findCallers(service.id)] == [controller.qualifiedName]
    path = index.callGraph.pathFinder.find_path(controller.id, inventory.id)
    assert [edge.targetSymbolId for edge in path] == [service.id, inventory.id]
    assert all(edge.resolved and edge.filePath and edge.line and edge.resolutionMethod for edge in path)


def test_python_constructor_bindings_are_local_and_ambiguous_receivers_stay_unresolved() -> None:
    source = """class Repo:
    def get(self):
        pass
class Other:
    def get(self):
        pass
class Service:
    def __init__(self):
        self.repo = Repo()
    def run(self):
        local = Other()
        self.repo.get()
        local.get()
        unknown.get()
"""
    file = SourceFile("demo.py", Language.PYTHON, source)
    tree = PythonParser().parse(source)
    symbols = PythonSymbolExtractor().extract(tree, source, file.filePath)
    calls = [item for item in RelationExtractor().extract(file, tree, symbols, SymbolResolver(symbols))
             if item.type == RelationType.CALLS and item.targetName == "get"]
    assert [item.resolved for item in calls] == [True, True, False]
    assert [item.resolutionMethod for item in calls] == ["LOCAL_CONSTRUCTOR_ASSIGNMENT",
                                                      "LOCAL_CONSTRUCTOR_ASSIGNMENT", "UNRESOLVED"]
    assert [next(symbol.name for symbol in symbols if symbol.id == item.targetSymbolId and
                 symbol.parentSymbolId == next(owner.id for owner in symbols if owner.name == owner_name))
            for item, owner_name in zip(calls[:2], ["Repo", "Other"])] == ["get", "get"]


def test_python_receiver_before_assignment_or_conflicting_reassignment_stays_unresolved() -> None:
    source = """class Repo:
    def get(self):
        pass
class Other:
    def get(self):
        pass
def run():
    local.get()
    local = Repo()
    local = Other()
    local.get()
"""
    file = SourceFile("demo.py", Language.PYTHON, source)
    tree = PythonParser().parse(source)
    symbols = PythonSymbolExtractor().extract(tree, source, file.filePath)
    calls = [item for item in RelationExtractor().extract(file, tree, symbols, SymbolResolver(symbols))
             if item.type == RelationType.CALLS and item.targetName == "get"]
    assert len(calls) == 2
    assert all(not item.resolved for item in calls)


def test_python_import_alias_constructor_resolves_only_matching_module() -> None:
    repository = SourceFile("repository.py", Language.PYTHON,
                            "class Repo:\n    def get(self):\n        pass\n")
    unrelated = SourceFile("other.py", Language.PYTHON,
                           "class Repo:\n    def get(self):\n        pass\n")
    service = SourceFile("service.py", Language.PYTHON,
                         "from repository import Repo as Storage\n"
                         "class Service:\n    def __init__(self):\n        self.store = Storage()\n"
                         "    def run(self):\n        self.store.get()\n")
    files = [repository, unrelated, service]
    trees = [PythonParser().parse(item.content) for item in files]
    symbols = [symbol for item, tree in zip(files, trees)
               for symbol in PythonSymbolExtractor().extract(tree, item.content, item.filePath)]
    calls = [item for item in RelationExtractor().extract(service, trees[-1], symbols, SymbolResolver(symbols))
             if item.type == RelationType.CALLS and item.targetName == "get"]
    assert len(calls) == 1 and calls[0].resolved
    assert calls[0].resolutionMethod == "IMPORTED_CONSTRUCTOR_ASSIGNMENT"
    assert next(symbol.filePath for symbol in symbols if symbol.id == calls[0].targetSymbolId) == "repository.py"


def test_call_path_is_shortest_stable_bounded_and_excludes_unresolved_edges() -> None:
    symbols = [Symbol(str(i), str(i), str(i), SymbolType.METHOD, Language.JAVA, "Demo.java", i, i)
               for i in range(5)]
    def edge(source, target, resolved=True):
        return Relation(f"{source}-{target}", str(source), str(target) if resolved else None,
                        str(target), RelationType.CALLS, "Demo.java", source + 1,
                        resolved, f"{source}.call({target})", "DIRECT_SYMBOL" if resolved else "UNRESOLVED")
    finder = CallPathFinder(symbols, [edge(0, 2), edge(2, 4), edge(0, 1), edge(1, 4),
                                      edge(1, 0), edge(0, 3, False)])
    assert [item.id for item in finder.find_path("0", "4")] == ["0-1", "1-4"]
    assert finder.find_path("0", "4", max_depth=1) == []
    assert finder.find_path("0", "3") == []


def test_index_readiness_requires_a_completed_analysis() -> None:
    index = AnalysisIndex()
    assert index.analysisReady is False
    with pytest.raises(FileNotFoundError):
        index.analyze(Path(__file__).parent / "missing-repository")
    assert index.analysisReady is False and index.callGraph is None
    index.analyze(Path(__file__).parents[3] / "demo" / "order-demo")
    assert index.analysisReady is True and index.callGraph is not None
