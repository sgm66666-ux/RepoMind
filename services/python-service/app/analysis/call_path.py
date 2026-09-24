"""Deterministic, bounded paths over AST-resolved CALLS relations only."""

from collections import defaultdict, deque

from app.domain.models import Relation, RelationType, Symbol


class CallPathFinder:
    def __init__(self, symbols: list[Symbol], relations: list[Relation]) -> None:
        ids = {symbol.id for symbol in symbols}
        self.outgoing: dict[str, list[Relation]] = defaultdict(list)
        for relation in relations:
            if (relation.type == RelationType.CALLS and relation.resolved and
                    relation.sourceSymbolId in ids and relation.targetSymbolId in ids):
                self.outgoing[relation.sourceSymbolId].append(relation)
        for edges in self.outgoing.values():
            edges.sort(key=lambda edge: (edge.targetSymbolId or "", edge.id))
        self.symbol_ids = ids

    def find_path(self, start_id: str, end_id: str, max_depth: int = 8) -> list[Relation]:
        if start_id not in self.symbol_ids or end_id not in self.symbol_ids or start_id == end_id or max_depth < 1:
            return []
        queue: deque[tuple[str, list[Relation]]] = deque([(start_id, [])])
        visited = {start_id}
        while queue:
            current, path = queue.popleft()
            if len(path) >= max_depth:
                continue
            for edge in self.outgoing.get(current, []):
                target = edge.targetSymbolId
                if target in visited:
                    continue
                candidate = [*path, edge]
                if target == end_id:
                    return candidate
                visited.add(target)
                queue.append((target, candidate))
        return []
