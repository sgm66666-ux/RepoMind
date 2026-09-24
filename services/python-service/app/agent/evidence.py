"""Verified Tool facts and separately labelled AST call-graph facts.

The store cannot ingest a Plan or model draft. Tool facts require a successful
Observation; AST path facts use a distinct indexed-graph provenance route.
"""

import re
from dataclasses import asdict, dataclass, field


def normalize_source_code(value: str) -> str:
    """Ignore surrounding/indentation whitespace, never alter source tokens."""
    return "\n".join(line.strip() for line in value.replace("\r\n", "\n").strip().split("\n"))


@dataclass(frozen=True)
class VerifiedSymbol:
    symbol_id: str
    raw_name: str
    file: str
    line: int
    end_line: int
    symbol_type: str
    language: str
    signature: str | None
    source_tool: str
    source_step: int


@dataclass(frozen=True)
class VerifiedSourceEvidence:
    file: str
    line: int
    symbol_id: str | None
    code: str
    evidence_type: str
    source_tool: str
    source_step: int


@dataclass(frozen=True)
class VerifiedCallEdge:
    source_id: str
    target_id: str
    file: str
    line: int
    code: str
    source_tool: str
    source_step: int
    resolved: bool = True


def classify_line(code: str) -> str:
    stripped = code.strip()
    if re.search(r"\breturn\s+(?:None|null)\s*;?\s*$", stripped):
        return "RETURN_VALUE"
    if re.search(r"(?<![=!<>])=(?!=)", stripped):
        return "ASSIGNMENT"
    if re.search(r"\b[A-Za-z_]\w*\s*(?:\[|\.(?!\w*\())", stripped):
        return "DEREFERENCE"
    if re.search(r"\b(?:if|while)\s*\(", stripped):
        return "CONDITION"
    if re.search(r"\b[A-Za-z_]\w*\s*\(", stripped):
        return "CALL_SITE"
    return "SOURCE_LINE"


@dataclass
class VerifiedEvidenceStore:
    symbols: dict[str, VerifiedSymbol] = field(default_factory=dict)
    source_lines: dict[tuple[str, int], VerifiedSourceEvidence] = field(default_factory=dict)
    edges: dict[tuple[str, str], VerifiedCallEdge] = field(default_factory=dict)
    source_provenance: dict[tuple[str, int], list[tuple[str, int]]] = field(default_factory=dict)

    def ingest_resolved_graph_path(self, symbols: list, relations: list) -> None:
        """Accept only relations returned by the indexed graph path finder, not model text."""
        from app.domain.models import RelationType, to_dict
        by_id = {symbol.id: symbol for symbol in symbols}
        for symbol in symbols:
            self._add_symbol(to_dict(symbol), "resolved_call_graph", 0)
        for relation in relations:
            if (relation.type != RelationType.CALLS or not relation.resolved or
                    relation.sourceSymbolId not in by_id or relation.targetSymbolId not in by_id):
                raise ValueError("Graph path contains an unverified edge")
            self.edges.setdefault((relation.sourceSymbolId, relation.targetSymbolId), VerifiedCallEdge(
                relation.sourceSymbolId, relation.targetSymbolId, relation.filePath, relation.line,
                relation.evidence, "resolved_call_graph", 0))

    def ingest(self, tool: str, arguments: dict, observation: dict, step: int) -> None:
        if not isinstance(observation, dict) or observation.get("success") is not True:
            return
        data = observation.get("data")
        if tool == "searchSymbol" and isinstance(data, list):
            for item in data:
                self._add_symbol(item, tool, step)
        elif tool in {"findCallers", "findCallees"} and isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                self._add_symbol(item.get("symbol"), tool, step)
                relation = item.get("relation")
                symbol = item.get("symbol")
                if not isinstance(relation, dict) or not isinstance(symbol, dict) or \
                        relation.get("type") != "CALLS" or relation.get("resolved") is not True:
                    continue
                source_id, target_id = relation.get("sourceSymbolId"), relation.get("targetSymbolId")
                queried = arguments.get("symbolId")
                if tool == "findCallees" and (source_id != queried or target_id != symbol.get("id")):
                    continue
                if tool == "findCallers" and (target_id != queried or source_id != symbol.get("id")):
                    continue
                if not all(isinstance(value, str) for value in (source_id, target_id,
                                                                 relation.get("filePath"), relation.get("evidence"))) or \
                        not isinstance(relation.get("line"), int):
                    continue
                self.edges.setdefault((source_id, target_id), VerifiedCallEdge(
                    source_id, target_id, relation["filePath"], relation["line"], relation["evidence"], tool, step))
        elif tool == "readFile" and isinstance(data, dict):
            file_path = data.get("filePath")
            start = (data.get("requestedRange") or {}).get("startLine")
            content = data.get("content")
            if not isinstance(file_path, str) or not isinstance(start, int) or not isinstance(content, str):
                return
            for offset, text in enumerate(content.splitlines()):
                if not text.strip():
                    continue
                line = start + offset
                key = (file_path, line)
                self.source_provenance.setdefault(key, []).append((tool, step))
                if key in self.source_lines:
                    continue
                owner = self.symbol_at(file_path, line)
                self.source_lines[key] = VerifiedSourceEvidence(
                    file_path, line, owner.symbol_id if owner else None, text.strip(),
                    classify_line(text), tool, step)

    def _add_symbol(self, item: object, tool: str, step: int) -> None:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or \
                not isinstance(item.get("qualifiedName"), str) or \
                not isinstance(item.get("filePath"), str) or \
                not isinstance(item.get("startLine"), int) or not isinstance(item.get("endLine"), int):
            return
        self.symbols.setdefault(item["id"], VerifiedSymbol(
            item["id"], item["qualifiedName"], item["filePath"], item["startLine"],
            item["endLine"], str(item.get("type") or ""), str(item.get("language") or ""),
            item.get("signature"), tool, step))
        # A Symbol may be observed after its source was read. Attach it without
        # changing the literal line or its readFile provenance.
        for key, source in list(self.source_lines.items()):
            if key[0] == item["filePath"] and item["startLine"] <= key[1] <= item["endLine"]:
                owner = self.symbol_at(*key)
                if owner and owner.symbol_id != source.symbol_id:
                    self.source_lines[key] = VerifiedSourceEvidence(
                        source.file, source.line, owner.symbol_id, source.code,
                        source.evidence_type, source.source_tool, source.source_step)

    def symbol_at(self, file: str, line: int) -> VerifiedSymbol | None:
        matches = [symbol for symbol in self.symbols.values() if symbol.file == file and
                   symbol.line <= line <= symbol.end_line]
        methods = [symbol for symbol in matches if symbol.symbol_type in {"METHOD", "FUNCTION"}]
        pool = methods or matches
        return min(pool, key=lambda item: (item.end_line - item.line, item.symbol_id)) if pool else None

    def resolve_symbol(self, name: str | None, *, file: str | None = None) -> VerifiedSymbol | None:
        if not name:
            return None
        matches = [symbol for symbol in self.symbols.values() if
                   (file is None or symbol.file == file) and
                   (symbol.raw_name == name or symbol.raw_name.endswith("." + name))]
        return matches[0] if len(matches) == 1 else None

    def canonical_name(self, symbol_id: str) -> str | None:
        symbol = self.symbols.get(symbol_id)
        if not symbol:
            return None
        parts = symbol.raw_name.split(".")
        short = ".".join(parts[-2:]) if len(parts) >= 2 else symbol.raw_name
        matches = [other for other in self.symbols.values() if
                   other.raw_name == short or other.raw_name.endswith("." + short)]
        if len(matches) == 1:
            return short
        # Overloads or same Class.method in different packages must stay distinct.
        return f"{symbol.raw_name}::{symbol.signature or symbol.symbol_id}"

    def source_for_symbol(self, symbol_id: str) -> list[VerifiedSourceEvidence]:
        symbol = self.symbols.get(symbol_id)
        if not symbol:
            return []
        return sorted((fact for fact in self.source_lines.values() if fact.file == symbol.file and
                       symbol.line <= fact.line <= symbol.end_line), key=lambda fact: fact.line)

    def source_at(self, file: str, line: int) -> VerifiedSourceEvidence | None:
        return self.source_lines.get((file, line))

    def call_path(self, start_name: str | None, end_name: str | None) -> list[VerifiedSymbol]:
        start, end = self.resolve_symbol(start_name), self.resolve_symbol(end_name)
        if not start or not end or start.symbol_id == end.symbol_id:
            return []
        from collections import deque
        queue = deque([[start.symbol_id]])
        visited = {start.symbol_id}
        while queue:
            path = queue.popleft()
            for source_id, target_id in self.edges:
                if source_id != path[-1] or target_id in visited:
                    continue
                candidate = [*path, target_id]
                if target_id == end.symbol_id:
                    return [self.symbols[symbol_id] for symbol_id in candidate if symbol_id in self.symbols]
                visited.add(target_id)
                queue.append(candidate)
        return []

    def _call_from_assignment(self, source: VerifiedSourceEvidence) -> tuple[str, str, str] | None:
        match = re.search(r"\b(?P<variable>[A-Za-z_]\w*)\s*=\s*(?P<rhs>[^;]+)", source.code)
        if not match:
            return None
        rhs = match.group("rhs")
        calls = re.findall(r"(?:(?P<owner>(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*)\.)?"
                           r"(?P<method>[A-Za-z_]\w*)\s*\(", rhs)
        if not calls:
            return None
        owner, method = calls[-1]
        if method in {"if", "while", "return"}:
            return None
        return match.group("variable"), owner, method

    def _owner_link(self, owner: str, callee: VerifiedSymbol, target_file: str) -> bool:
        if not owner:
            return False
        class_name = callee.raw_name.split(".")[-2] if "." in callee.raw_name else ""
        if not class_name:
            return False
        if owner.split(".")[-1].casefold() == class_name.casefold():
            return True
        # This is a textual constructor/type link, not a resolved CALLS edge.
        return any(fact.file == target_file and re.search(
            rf"\b{re.escape(owner)}\s*=\s*{re.escape(class_name)}\s*\(", fact.code)
            for fact in self.source_lines.values()) or any(
            fact.file == target_file and re.search(
                rf"\b{re.escape(class_name)}\s+{re.escape(owner)}\b", fact.code)
            for fact in self.source_lines.values())

    def _return_source(self, symbol: VerifiedSymbol, remaining: int,
                       visited: set[str]) -> VerifiedSourceEvidence | None:
        if remaining <= 0 or symbol.symbol_id in visited:
            return None
        visited.add(symbol.symbol_id)
        lines = self.source_for_symbol(symbol.symbol_id)
        for fact in lines:
            if re.search(r"\breturn\s+(?:None|null)\s*;?\s*$", fact.code):
                return fact
        for fact in lines:
            match = re.search(r"\breturn\s+(?:[A-Za-z_]\w*\.)*(?P<method>[A-Za-z_]\w*)\s*\(", fact.code)
            if not match:
                continue
            callees = [item for item in self.symbols.values() if item.raw_name.endswith("." + match.group("method"))]
            if len(callees) == 1:
                found = self._return_source(callees[0], remaining - 1, visited)
                if found:
                    return found
        return None

    def trace_value_source(self, target_id: str | None, max_depth: int = 3) -> dict:
        """Bounded local assignment -> call -> return investigation; never assert runtime value."""
        target = self.symbols.get(target_id or "")
        if not target:
            return {"assignment": None, "trigger": None, "return_source": None,
                    "callee_symbol": None, "candidate_method": None, "linkage": None,
                    "max_depth": max_depth}
        lines = self.source_for_symbol(target.symbol_id)
        for assignment in lines:
            parsed = self._call_from_assignment(assignment)
            if not parsed:
                continue
            variable, owner, method = parsed
            triggers = [fact for fact in lines if fact.line > assignment.line and re.search(
                rf"\b{re.escape(variable)}\s*(?:\[|\.(?!\w*\())", fact.code)]
            candidates = [item for item in self.symbols.values() if item.raw_name.endswith("." + method) and
                          item.symbol_type in {"METHOD", "FUNCTION"} and item.language == target.language]
            callee = candidates[0] if len(candidates) == 1 else None
            resolved = bool(callee and (target.symbol_id, callee.symbol_id) in self.edges)
            textual = bool(callee and self._owner_link(owner, callee, target.file))
            origin = self._return_source(callee, max_depth - 1, set()) if callee else None
            return {"assignment": assignment, "trigger": triggers[0] if triggers else None, "return_source": origin,
                    "callee_symbol": callee, "candidate_method": method,
                    "linkage": "RESOLVED_CALL_EDGE" if resolved else ("OBSERVED_OWNER_TYPE" if textual else None),
                    "max_depth": max_depth}
        return {"assignment": None, "trigger": None, "return_source": None,
                "callee_symbol": None, "candidate_method": None, "linkage": None,
                "max_depth": max_depth}

    def snapshot(self) -> dict:
        return {"symbols": [asdict(item) | {"canonical_name": self.canonical_name(item.symbol_id)}
                            for item in self.symbols.values()],
                "source_evidence": [asdict(item) | {"provenance": self.source_provenance.get((item.file, item.line), [])}
                                    for item in self.source_lines.values()],
                "call_edges": [asdict(item) for item in self.edges.values()]}
