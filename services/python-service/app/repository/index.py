from dataclasses import dataclass
from pathlib import Path

from app.analysis.call_graph import CallGraph
from app.analysis.relation_extractor import RelationExtractor
from app.analysis.resolver import SymbolResolver
from app.analysis.symbol_extractor import JavaSymbolExtractor, PythonSymbolExtractor
from app.domain.models import Language, Relation, SourceFile, Symbol
from app.parsers.java_parser import JavaParser
from app.parsers.python_parser import PythonParser
from app.repository.scanner import RepositoryScanner, ScanIssue
from app.repository.reader import CodeReader


@dataclass
class AnalysisIndex:
    sourceFiles: dict[str, SourceFile]
    symbols: dict[str, Symbol]
    relations: list[Relation]
    issues: list[ScanIssue]
    callGraph: CallGraph | None
    repositoryPath: Path | None

    def __init__(self) -> None:
        self.sourceFiles = {}
        self.symbols = {}
        self.relations = []
        self.issues = []
        self.callGraph = None
        self.repositoryPath = None
        self.analysisReady = False

    def analyze(self, repository_path: str | Path) -> "AnalysisIndex":
        self.analysisReady = False
        self.callGraph = None
        scan_result = RepositoryScanner().scan(repository_path)
        self.repositoryPath = Path(repository_path).resolve()
        self.sourceFiles = {source_file.filePath: source_file for source_file in scan_result.files}
        self.issues = scan_result.issues
        self.symbols = {}
        self.relations = []
        parsed: list[tuple[SourceFile, object]] = []

        for source_file in scan_result.files:
            parser = JavaParser() if source_file.language == Language.JAVA else PythonParser()
            tree = parser.parse(source_file.content)
            parsed.append((source_file, tree))
            extractor = JavaSymbolExtractor() if source_file.language == Language.JAVA else PythonSymbolExtractor()
            for symbol in extractor.extract(tree, source_file.content, source_file.filePath):
                self.symbols[symbol.id] = symbol

        symbol_list = list(self.symbols.values())
        resolver = SymbolResolver(symbol_list)
        relation_extractor = RelationExtractor()
        for source_file, tree in parsed:
            self.relations.extend(relation_extractor.extract(source_file, tree, symbol_list, resolver))
        self.callGraph = CallGraph(symbol_list, self.relations)
        self.analysisReady = True
        return self

    def get_symbol(self, symbol_id: str) -> Symbol | None:
        return self.symbols.get(symbol_id)

    def find_symbols(self, query: str | None = None) -> list[Symbol]:
        values = list(self.symbols.values())
        if not query:
            return sorted(values, key=lambda item: (item.filePath, item.startLine, item.qualifiedName))
        normalized = query.lower()
        return sorted(
            [item for item in values if normalized in item.name.lower() or normalized in item.qualifiedName.lower()],
            key=lambda item: (item.filePath, item.startLine, item.qualifiedName),
        )

    def search_symbols(
        self,
        name: str | None = None,
        qualified_name: str | None = None,
        symbol_type=None,
        language=None,
    ) -> list[Symbol]:
        values = list(self.symbols.values())
        if name:
            values = [item for item in values if name.lower() in item.name.lower()]
        if qualified_name:
            values = [item for item in values if qualified_name.lower() in item.qualifiedName.lower()]
        if symbol_type:
            values = [item for item in values if item.type.value == getattr(symbol_type, "value", symbol_type)]
        if language:
            values = [item for item in values if item.language.value == getattr(language, "value", language)]
        return sorted(values, key=lambda item: (item.filePath, item.startLine, item.qualifiedName))

    def read_file(self, file_path: str, start_line: int | None = None, end_line: int | None = None):
        if self.repositoryPath is None:
            raise RuntimeError("No repository has been analyzed")
        return CodeReader(self.repositoryPath).read(file_path, start_line, end_line)

    def references_for(self, symbol_id: str) -> list[Relation]:
        return [
            relation for relation in self.relations
            if relation.type.value == "REFERENCES" and relation.targetSymbolId == symbol_id
        ]

    def unresolved_relations(self) -> list[Relation]:
        return [relation for relation in self.relations if not relation.resolved]
