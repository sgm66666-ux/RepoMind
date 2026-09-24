from app.domain.models import RelationType, Symbol, to_dict


class CodeContextBuilder:
    """Build bounded, evidence-oriented context from the in-memory index."""

    def __init__(self, index) -> None:
        self.index = index

    def build(
        self,
        symbol_id: str,
        maxCallers: int = 5,
        maxCallees: int = 5,
        maxReferences: int = 10,
        maxSnippetLines: int = 40,
    ) -> dict:
        target = self.index.get_symbol(symbol_id)
        if target is None:
            raise KeyError(f"Symbol not found: {symbol_id}")
        if min(maxCallers, maxCallees, maxReferences, maxSnippetLines) < 0:
            raise ValueError("Context limits cannot be negative")

        start = target.startLine
        end = min(target.endLine, start + maxSnippetLines - 1) if maxSnippetLines else start - 1
        snippet = self.index.read_file(target.filePath, start, end) if maxSnippetLines else None
        parent = self.index.get_symbol(target.parentSymbolId) if target.parentSymbolId else None
        imports = [
            relation for relation in self.index.relations
            if relation.filePath == target.filePath and relation.type == RelationType.IMPORTS
        ]
        callers = self.index.callGraph.findCallers(symbol_id)[:maxCallers] if self.index.callGraph else []
        callees = self.index.callGraph.findCallees(symbol_id)[:maxCallees] if self.index.callGraph else []
        references = self.index.references_for(symbol_id)[:maxReferences]

        evidence = [
            {
                "filePath": relation.filePath,
                "line": relation.line,
                "relationType": relation.type.value,
                "sourceSymbolId": relation.sourceSymbolId,
                "targetSymbolId": relation.targetSymbolId,
                "targetName": relation.targetName,
                "resolved": relation.resolved,
                "evidence": relation.evidence,
            }
            for relation in [*imports, *[item["relation"] for item in callers], *[item["relation"] for item in callees], *references]
        ]
        return {
            "targetSymbol": to_dict(target),
            "sourceSnippet": to_dict(snippet) if snippet else None,
            "parent": to_dict(parent) if parent else None,
            "imports": [to_dict(item) for item in imports],
            "callers": [to_dict(item) for item in callers],
            "callees": [to_dict(item) for item in callees],
            "references": [to_dict(item) for item in references],
            "evidence": evidence,
        }
