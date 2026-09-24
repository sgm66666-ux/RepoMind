from collections import defaultdict

from app.domain.models import Relation, RelationType, Symbol
from app.analysis.call_path import CallPathFinder


class CallGraph:
    def __init__(self, symbols: list[Symbol], relations: list[Relation]) -> None:
        self.symbols = {symbol.id: symbol for symbol in symbols}
        self.relations = relations
        self.pathFinder = CallPathFinder(symbols, relations)
        self._callers: dict[str, list[Relation]] = defaultdict(list)
        self._callees: dict[str, list[Relation]] = defaultdict(list)
        for relation in relations:
            if relation.type != RelationType.CALLS or not relation.resolved or not relation.targetSymbolId:
                continue
            if relation.sourceSymbolId:
                self._callers[relation.targetSymbolId].append(relation)
                self._callees[relation.sourceSymbolId].append(relation)

    def findCallers(self, symbol_id: str) -> list[dict[str, Symbol | Relation]]:
        return [
            {"symbol": self.symbols[relation.sourceSymbolId], "relation": relation}
            for relation in self._callers.get(symbol_id, [])
            if relation.sourceSymbolId in self.symbols
        ]

    def findCallees(self, symbol_id: str) -> list[dict[str, Symbol | Relation]]:
        return [
            {"symbol": self.symbols[relation.targetSymbolId], "relation": relation}
            for relation in self._callees.get(symbol_id, [])
            if relation.targetSymbolId in self.symbols
        ]
