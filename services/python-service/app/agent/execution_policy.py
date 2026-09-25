"""Observation and separately labelled AST-graph memory for the existing AgentLoop.

This module never invokes Tools or chooses a Tool on behalf of the LLM. It records
actual Tool results and independently verified indexed paths with distinct provenance.
"""

import json
import re
from collections import deque
from dataclasses import asdict, dataclass, field

from app.agent.planner import ExecutionPlan
from app.agent.diagnosis import validate_evidence_against_trace
from app.agent.evidence import VerifiedEvidenceStore
from app.domain.models import RelationType, SymbolType


def _parameter_types(signature: str | None) -> tuple[str, ...] | None:
    """Compare indexed Java method parameters without treating overload names as identities."""
    if not signature or "(" not in signature or ")" not in signature:
        return None
    parameters = signature.split("(", 1)[1].rsplit(")", 1)[0].strip()
    if not parameters:
        return ()
    if "<" in parameters or ">" in parameters:
        return None  # No generic-signature guesses in the narrow dispatch bridge.
    result = []
    for parameter in parameters.split(","):
        parts = parameter.strip().split()
        if len(parts) != 2:
            return None
        result.append(parts[0])
    return tuple(result)


@dataclass(frozen=True)
class CallEdgeEvidence:
    source_id: str
    target_id: str
    file: str | None
    line: int | None
    code: str | None
    source_tool: str
    source_step: int


@dataclass
class CallChainEvidenceTracker:
    nodes: dict[str, dict] = field(default_factory=dict)
    edges: dict[tuple[str, str], CallEdgeEvidence] = field(default_factory=dict)

    def add_symbol(self, symbol: object) -> bool:
        if not isinstance(symbol, dict) or not isinstance(symbol.get("id"), str) or not isinstance(symbol.get("qualifiedName"), str):
            return False
        fresh = symbol["id"] not in self.nodes
        self.nodes[symbol["id"]] = symbol
        return fresh

    def add_connections(self, tool: str, arguments: dict, data: object, step: int) -> tuple[int, int]:
        new_symbols = new_edges = 0
        if not isinstance(data, list):
            return 0, 0
        for item in data:
            if not isinstance(item, dict):
                continue
            new_symbols += self.add_symbol(item.get("symbol"))
            relation = item.get("relation")
            if not isinstance(relation, dict) or relation.get("type") != "CALLS" or relation.get("resolved") is not True:
                continue
            source_id, target_id = relation.get("sourceSymbolId"), relation.get("targetSymbolId")
            if not isinstance(source_id, str) or not isinstance(target_id, str):
                continue
            # Verify the returned edge is incident to the Symbol actually queried.
            queried_id = arguments.get("symbolId")
            if tool == "findCallees" and source_id != queried_id:
                continue
            if tool == "findCallers" and target_id != queried_id:
                continue
            key = (source_id, target_id)
            if key not in self.edges:
                self.edges[key] = CallEdgeEvidence(source_id, target_id, relation.get("filePath"),
                                                   relation.get("line"), relation.get("evidence"), tool, step)
                new_edges += 1
        return new_symbols, new_edges

    def match_symbol(self, hint: str | None) -> str | None:
        if not hint:
            return None
        matches = [symbol_id for symbol_id, symbol in self.nodes.items()
                   if symbol.get("qualifiedName") == hint or
                   str(symbol.get("qualifiedName") or "").endswith("." + hint) or
                   symbol.get("name") == hint]
        return matches[0] if len(matches) == 1 else None

    def path_ids(self, start_id: str | None, end_id: str | None) -> list[str]:
        if not start_id or not end_id or start_id == end_id:
            return []
        queue = deque([[start_id]])
        visited = {start_id}
        while queue:
            path = queue.popleft()
            for source_id, target_id in self.edges:
                if source_id != path[-1] or target_id in visited:
                    continue
                next_path = [*path, target_id]
                if target_id == end_id:
                    return next_path
                visited.add(target_id)
                queue.append(next_path)
        return []

    def longest_prefix_ids(self, start_id: str | None) -> list[str]:
        if not start_id:
            return []
        queue = deque([[start_id]])
        longest = [start_id]
        while queue:
            path = queue.popleft()
            if len(path) > len(longest):
                longest = path
            if len(path) >= 20:
                continue
            for source_id, target_id in self.edges:
                if source_id == path[-1] and target_id not in path:
                    queue.append([*path, target_id])
        return longest

    def names(self, ids: list[str]) -> list[str]:
        return [self.nodes[symbol_id]["qualifiedName"] for symbol_id in ids if symbol_id in self.nodes]

    def edge_records(self) -> list[dict]:
        return [{**asdict(edge), "from": self.nodes.get(edge.source_id, {}).get("qualifiedName"),
                 "to": self.nodes.get(edge.target_id, {}).get("qualifiedName")}
                for edge in self.edges.values()]


def normalized_call(tool: str, arguments: dict) -> str:
    """Canonicalize semantically identical static-analysis calls for duplicate detection."""
    clean = {key: value for key, value in arguments.items() if value not in (None, "")}
    if tool == "searchSymbol":
        for key in ("name", "qualifiedName"):
            if isinstance(clean.get(key), str):
                clean[key] = clean[key].strip().casefold()
        for key in ("type", "language"):
            if isinstance(clean.get(key), str):
                clean[key] = clean[key].strip().upper()
    return json.dumps([tool, clean], ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def query_symbol_hints(question: str) -> list[str]:
    return list(dict.fromkeys(re.findall(
        r"(?<![A-Za-z0-9_$])(?:[A-Z][A-Za-z0-9_$]*\.)+[A-Za-z_][A-Za-z0-9_$]*(?![A-Za-z0-9_$])",
        question)))


@dataclass
class AgentExecutionState:
    question: str
    plan: ExecutionPlan | None
    analysis_index: object | None = field(default=None, repr=False)
    seen_tool_calls: set[str] = field(default_factory=set)
    discovered_symbols: dict[str, dict] = field(default_factory=dict)
    discovered_files: set[str] = field(default_factory=set)
    source_lines: dict[tuple[str, int], dict] = field(default_factory=dict)
    evidence_store: VerifiedEvidenceStore = field(default_factory=VerifiedEvidenceStore)
    call_tracker: CallChainEvidenceTracker = field(default_factory=CallChainEvidenceTracker)
    collected_evidence: list[dict] = field(default_factory=list)
    last_progress_step: int | None = None
    consecutive_no_progress: int = 0
    failed_searches: list[dict] = field(default_factory=list)
    current_evidence_requirements: list[str] = field(default_factory=list)
    duplicate_calls: int = 0
    no_progress_calls: int = 0
    policy_events: list[dict] = field(default_factory=list)
    graph_path_evidence: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.plan:
            self.current_evidence_requirements = list(self.plan.required_evidence)

    def already_called(self, tool: str, arguments: dict) -> bool:
        return normalized_call(tool, arguments) in self.seen_tool_calls

    def complete_verified_graph_path(self, index) -> None:
        """Attach an indexed path only after a real Symbol search has succeeded."""
        if not self.plan or self.plan.task_type != "CALL_CHAIN_ANALYSIS" or self.graph_path_evidence:
            return
        if not self.discovered_symbols or not index.callGraph:
            return
        hints = query_symbol_hints(self.question)
        if len(hints) < 2:
            return
        def unique_id(hint):
            matches = [item for item in index.symbols.values() if
                       item.qualifiedName == hint or item.qualifiedName.endswith("." + hint)]
            return matches[0].id if len(matches) == 1 else None
        start_id, end_id = unique_id(hints[0]), unique_id(hints[-1])
        if not start_id or not end_id or start_id not in self.discovered_symbols:
            return
        path = index.callGraph.pathFinder.find_path(start_id, end_id)
        if not path:
            return
        ids = [start_id, *(edge.targetSymbolId for edge in path)]
        symbols = [index.symbols[symbol_id] for symbol_id in ids]
        self.evidence_store.ingest_resolved_graph_path(symbols, path)
        from app.domain.models import to_dict
        for symbol in symbols:
            self.call_tracker.add_symbol(to_dict(symbol))
        for edge in path:
            key = (edge.sourceSymbolId, edge.targetSymbolId)
            self.call_tracker.edges.setdefault(key, CallEdgeEvidence(
                key[0], key[1], edge.filePath, edge.line, edge.evidence, "resolved_call_graph", 0))
        self.discovered_symbols.update(self.call_tracker.nodes)
        self.graph_path_evidence = [{"relationId": edge.id, "sourceSymbolId": edge.sourceSymbolId,
                                     "targetSymbolId": edge.targetSymbolId, "filePath": edge.filePath,
                                     "line": edge.line, "evidence": edge.evidence,
                                     "resolutionMethod": edge.resolutionMethod,
                                     "source": "AST_RESOLVED_CALL_GRAPH"} for edge in path]
        self.policy_events.append({"step": 0, "status": "GRAPH_PATH_FOUND",
                                   "message": "Resolved call graph supplied a shortest verified path; no Tool call was fabricated."})

    def record_duplicate(self, tool: str, arguments: dict, step: int) -> None:
        self.duplicate_calls += 1
        self._record_progress(False, step)
        self.policy_events.append({"step": step, "status": "DUPLICATE_CALL", "tool": tool,
                                   "message": "The same static-analysis call was already executed; choose a different query or Tool."})

    def observe(self, tool: str, arguments: dict, observation: dict, step: int) -> tuple[bool, list[str]]:
        self.seen_tool_calls.add(normalized_call(tool, arguments))
        self.evidence_store.ingest(tool, arguments, observation, step)
        new_items: list[str] = []
        data = observation.get("data") if observation.get("success") else None
        if tool == "searchSymbol" and isinstance(data, list):
            for symbol in data:
                if self.call_tracker.add_symbol(symbol):
                    self.discovered_symbols[symbol["id"]] = symbol
                    new_items.append(f"Symbol:{symbol['qualifiedName']}")
            if not data:
                self.failed_searches.append({"step": step, "arguments": arguments})
        elif tool == "readFile" and isinstance(data, dict):
            file_path = data.get("filePath")
            requested = data.get("requestedRange") or {}
            start = requested.get("startLine")
            if isinstance(file_path, str) and isinstance(start, int) and isinstance(data.get("content"), str):
                if file_path not in self.discovered_files:
                    self.discovered_files.add(file_path)
                    new_items.append(f"File:{file_path}")
                for offset, code in enumerate(data["content"].splitlines()):
                    if not code.strip():
                        continue
                    key = (file_path, start + offset)
                    if key not in self.source_lines:
                        fact = {"file": file_path, "line": start + offset, "code": code.strip(),
                                "source_tool": "readFile", "source_step": step}
                        self.source_lines[key] = fact
                        self.collected_evidence.append(fact)
                        new_items.append(f"Source:{file_path}:{start + offset}")
        elif tool in {"findCallers", "findCallees"}:
            new_symbols, new_edges = self.call_tracker.add_connections(tool, arguments, data, step)
            self.discovered_symbols.update(self.call_tracker.nodes)
            if new_symbols:
                new_items.append(f"Symbols:{new_symbols}")
            if new_edges:
                new_items.append(f"CallEdges:{new_edges}")
        elif tool == "findReferences" and isinstance(data, list):
            for relation in data:
                if isinstance(relation, dict) and relation.get("id") and relation["id"] not in {
                    item.get("id") for item in self.collected_evidence}:
                    self.collected_evidence.append(relation)
                    new_items.append(f"Reference:{relation['id']}")
        progress = bool(new_items)
        self._record_progress(progress, step)
        if not progress:
            self.policy_events.append({"step": step, "status": "NO_PROGRESS" if self.consecutive_no_progress >= 2
                                       else "NO_NEW_EVIDENCE", "tool": tool,
                                       "message": "Tool completed without new Symbols, files, source lines, or resolved edges."})
        return progress, new_items

    def _record_progress(self, progress: bool, step: int) -> None:
        if progress:
            self.last_progress_step = step
            self.consecutive_no_progress = 0
        else:
            self.consecutive_no_progress += 1
            self.no_progress_calls += 1

    def _target_id(self) -> str | None:
        hints = query_symbol_hints(self.question)
        if hints:
            return self.call_tracker.match_symbol(hints[0])
        if self.plan:
            for hint in self.plan.target_keywords:
                matched = self.call_tracker.match_symbol(hint)
                if matched:
                    return matched
        return None

    def _target_lines(self, symbol_id: str | None) -> list[dict]:
        symbol = self.discovered_symbols.get(symbol_id or "")
        if not symbol:
            return []
        return [fact for (file_path, line), fact in self.source_lines.items()
                if file_path == symbol.get("filePath") and symbol.get("startLine", 0) <= line <= symbol.get("endLine", -1)]

    def runtime_facts(self) -> dict[str, dict | None]:
        target_id = self._target_id()
        flow = self.evidence_store.trace_value_source(target_id, max_depth=3)
        indexed_call = None
        implementation = None
        implementation_relation = None
        ambiguous_implementations = False
        interface_dispatch = False
        index = self.analysis_index
        assignment = flow["assignment"]
        if index is not None and target_id and assignment and flow["candidate_method"]:
            calls = [relation for relation in index.relations if
                     relation.type == RelationType.CALLS and relation.resolved and
                     relation.sourceSymbolId == target_id and relation.line == assignment.line and
                     relation.targetName == flow["candidate_method"] and relation.targetSymbolId]
            if len(calls) == 1:
                indexed_call = calls[0]
                interface_method = index.symbols.get(indexed_call.targetSymbolId)
                interface_owner = index.symbols.get(interface_method.parentSymbolId) if interface_method else None
                if interface_owner and interface_owner.type == SymbolType.INTERFACE:
                    interface_dispatch = True
                    implementations = [relation for relation in index.relations if
                                       relation.type == RelationType.IMPLEMENTS and relation.resolved and
                                       relation.targetSymbolId == interface_owner.id and relation.sourceSymbolId]
                    if len(implementations) == 1:
                        signature = _parameter_types(interface_method.signature)
                        matches = [symbol for symbol in index.symbols.values() if
                                   symbol.parentSymbolId == implementations[0].sourceSymbolId and
                                   symbol.type == SymbolType.METHOD and symbol.name == interface_method.name and
                                   signature is not None and _parameter_types(symbol.signature) == signature]
                        if len(matches) == 1:
                            implementation = matches[0]
                            implementation_relation = implementations[0]
                            if implementation.id in self.evidence_store.symbols:
                                flow = self.evidence_store.trace_value_source(
                                    target_id, max_depth=3, preferred_callee_id=implementation.id)
                    else:
                        ambiguous_implementations = len(implementations) > 1
        callee = flow["callee_symbol"]
        related_edge = self.call_tracker.edges.get((target_id, callee.symbol_id)) if callee else None
        def fact(value):
            return asdict(value) if value is not None else None
        indexed_edge = ({"source_id": indexed_call.sourceSymbolId, "target_id": indexed_call.targetSymbolId,
                         "file": indexed_call.filePath, "line": indexed_call.line, "code": indexed_call.evidence,
                         "source_tool": "indexed_call_graph", "source_step": 0,
                         "resolution_method": indexed_call.resolutionMethod} if indexed_call else None)
        implementation_hint = ({"symbol_id": implementation.id, "qualified_name": implementation.qualifiedName,
                                "file": implementation.filePath, "line": implementation.startLine,
                                "end_line": implementation.endLine,
                                "source": "UNIQUE_INDEXED_IMPLEMENTS_CANDIDATE"} if implementation else None)
        observed_implementation = bool(implementation and implementation.id in self.evidence_store.symbols)
        cross_file_required = bool(indexed_call and interface_dispatch)
        linkage = flow["linkage"]
        if cross_file_required and observed_implementation and flow["return_source"]:
            linkage = "UNIQUE_INTERFACE_IMPLEMENTATION_CANDIDATE"
        return {"assignment": fact(flow["assignment"]),
                "invalid_value_origin": fact(flow["return_source"]),
                "trigger_operation": fact(flow["trigger"]),
                "related_call_edge": asdict(related_edge) if related_edge else indexed_edge,
                "source_to_usage_linkage": linkage,
                "candidate_method": flow["candidate_method"],
                "callee_symbol": fact(callee),
                "implementation_candidate": implementation_hint,
                "implementation_relation": ({"file": implementation_relation.filePath,
                                             "line": implementation_relation.line,
                                             "source_symbol_id": implementation_relation.sourceSymbolId,
                                             "target_symbol_id": implementation_relation.targetSymbolId,
                                             "source": "INDEXED_IMPLEMENTS_RELATION"}
                                            if implementation_relation else None),
                "ambiguous_implementations": ambiguous_implementations,
                "cross_file_required": cross_file_required,
                "implementation_observed": observed_implementation}

    def cross_file_evidence(self) -> dict:
        """Verified static-risk chain; unique implementation is not a runtime dispatch proof."""
        facts = self.runtime_facts()
        if not facts["cross_file_required"]:
            return {"applicable": False, "complete": False, "missing": [], "chain": [],
                    "implementation_candidate": facts["implementation_candidate"],
                    "ambiguous_implementations": facts["ambiguous_implementations"]}
        assignment, origin, trigger = (facts[key] for key in
                                       ("assignment", "invalid_value_origin", "trigger_operation"))
        files = {item["file"] for item in (assignment, origin, trigger) if item}
        checks = {"producing_method_observed": facts["implementation_observed"],
                  "invalid_return_observed": bool(origin and origin["evidence_type"] == "RETURN_VALUE"),
                  "resolved_interface_call": facts["related_call_edge"] is not None,
                  "unique_implementation_relation": facts["implementation_relation"] is not None,
                  "assignment_observed": assignment is not None,
                  "dereference_observed": trigger is not None,
                  "two_source_files": len(files) >= 2}
        chain = []
        edge = facts["related_call_edge"]
        if edge:
            chain.append({"type": "CALL_EDGE", **edge})
        relation = facts["implementation_relation"]
        if relation:
            chain.append({"type": "IMPLEMENTS", **relation})
        for label, value in (("RETURN_VALUE", origin), ("ASSIGNMENT", assignment), ("DEREFERENCE", trigger)):
            if value:
                chain.append({"type": label, **value})
        return {"applicable": True, "complete": all(checks.values()),
                "missing": [key for key, present in checks.items() if not present],
                "chain": chain, "implementation_candidate": facts["implementation_candidate"],
                "ambiguous_implementations": facts["ambiguous_implementations"],
                "runtime_execution_proven": False}

    def checklist(self) -> dict[str, bool]:
        task = self.plan.task_type if self.plan else None
        target_id = self._target_id()
        target_lines = self._target_lines(target_id)
        if task == "RUNTIME_ERROR":
            facts = self.runtime_facts()
            checks = {"target_symbol": target_id is not None, "target_source": bool(target_lines),
                    "assignment": facts["assignment"] is not None,
                    "invalid_value_origin": facts["invalid_value_origin"] is not None,
                    "trigger_operation": facts["trigger_operation"] is not None,
                    "source_to_usage_linkage": facts["source_to_usage_linkage"] is not None,
                    "related_call_edge": facts["related_call_edge"] is not None}
            if facts["cross_file_required"]:
                chain = self.cross_file_evidence()
                checks["cross_file_source"] = chain["complete"]
            return checks
        if task == "BUSINESS_LOGIC_ERROR":
            callers = [edge for edge in self.call_tracker.edges.values() if edge.target_id == target_id]
            callees = [edge for edge in self.call_tracker.edges.values() if edge.source_id == target_id]
            related_source = any(self._target_lines(edge.source_id) for edge in callers) or \
                any(self._target_lines(edge.target_id) for edge in callees)
            actual_logic = any(re.search(r"\breturn\b", item["code"]) for item in target_lines)
            expectation = any(re.search(r"\bassert(?:Equals|Equal)?\s*\(|\bassert\s+", fact["code"])
                              for fact in self.source_lines.values())
            return {"target_symbol": target_id is not None, "target_source": bool(target_lines),
                    "related_call_context": bool((callers or callees) and related_source), "actual_logic": actual_logic,
                    "business_expectation": expectation}
        if task == "CALL_CHAIN_ANALYSIS":
            hints = query_symbol_hints(self.question)
            start_id = self.call_tracker.match_symbol(hints[0]) if hints else None
            end_id = self.call_tracker.match_symbol(hints[-1]) if len(hints) >= 2 else None
            path = self.call_tracker.path_ids(start_id, end_id)
            return {"start_symbol": start_id is not None, "end_symbol": end_id is not None,
                    "intermediate_nodes": len(path) >= 2,  # zero intermediates is valid for a direct edge
                    "each_call_edge": len(path) >= 2,
                    "edge_observations": len(path) >= 2 and all(
                        (left, right) in self.call_tracker.edges for left, right in zip(path, path[1:]))}
        if task == "CONFIGURATION_ERROR":
            return {"configuration_source": False, "code_usage_site": False, "configuration_link": False}
        return {"observed_evidence": bool(self.collected_evidence or self.discovered_symbols)}

    def missing_evidence(self) -> list[str]:
        checks = self.checklist()
        if self.plan and self.plan.task_type == "RUNTIME_ERROR":
            if not self.runtime_facts()["cross_file_required"]:
                checks = {key: value for key, value in checks.items() if key != "related_call_edge"}
        return [key for key, present in checks.items() if not present]

    def completion_decision(self) -> str:
        task = self.plan.task_type if self.plan else None
        if task == "CONFIGURATION_ERROR":
            return "UNSUPPORTED"
        checks = self.checklist()
        if task == "RUNTIME_ERROR":
            return "COMPLETE" if not self.missing_evidence() else (
                "PARTIAL" if any(checks.values()) else "INSUFFICIENT_EVIDENCE")
        if checks and all(checks.values()):
            return "COMPLETE"
        if task == "BUSINESS_LOGIC_ERROR" and all(checks.get(key) for key in
                                                    ("target_symbol", "target_source", "related_call_context", "actual_logic")):
            return "PARTIAL"  # A formula in source does not prove the intended business rule.
        if task == "CALL_CHAIN_ANALYSIS" and self.partial_chain():
            return "PARTIAL"
        if any(checks.values()):
            return "PARTIAL"
        return "INSUFFICIENT_EVIDENCE"

    def verified_chain(self) -> list[str]:
        hints = query_symbol_hints(self.question)
        if len(hints) < 2:
            return []
        return self.call_tracker.names(self.call_tracker.path_ids(
            self.call_tracker.match_symbol(hints[0]), self.call_tracker.match_symbol(hints[-1])))

    def partial_chain(self) -> list[str]:
        hints = query_symbol_hints(self.question)
        return self.call_tracker.names(self.call_tracker.longest_prefix_ids(
            self.call_tracker.match_symbol(hints[0]) if hints else None))

    def feedback(self) -> str:
        gaps = self.missing_evidence()
        hints: list[str] = []
        priority = ""
        if self.failed_searches:
            failed = self.failed_searches[-1]["arguments"]
            method = str(failed.get("name") or failed.get("qualifiedName") or "").split(".")[-1]
            if method:
                hints.append(f"The prior search with {json.dumps(failed, ensure_ascii=False)} found no Symbol. "
                             f"Do not repeat those exact filters. A broader searchSymbol query can use only "
                             f"name={method!r}, omitting qualifiedName, type and language; infer any later filters "
                             "from an actual Symbol Observation.")
            if re.search(r"typeerror|indexerror|keyerror|traceback|python", self.question, re.IGNORECASE):
                hints.append("The exception may be Python. For a Class.method query, Python class methods are indexed as type=METHOD (module functions are FUNCTION): try searchSymbol with the method name and language=PYTHON, type=METHOD, omitting qualifiedName. Do not assume a Symbol exists until observed.")
            if self.failed_searches[-1]["arguments"].get("qualifiedName"):
                hints.append("A Python qualified name may include a module prefix; exact class.method filters can be too restrictive.")
        if self.plan and self.plan.task_type == "CALL_CHAIN_ANALYSIS":
            if self.graph_path_evidence and self.verified_chain():
                priority = ("The shortest requested call path is already verified by AST_RESOLVED_CALL_GRAPH "
                            "with relation IDs and file/line provenance. Do not rediscover these edges with "
                            "findCallers/findCallees; return FinalDiagnosis now using an actual Tool Observation "
                            "for the evidence array. This graph path is not a Tool Call. ")
            hints_from_query = query_symbol_hints(self.question)
            start_id = self.call_tracker.match_symbol(hints_from_query[0]) if hints_from_query else None
            prefix = self.call_tracker.longest_prefix_ids(start_id)
            if prefix and not self.verified_chain():
                frontier = prefix[-1]
                if frontier in self.call_tracker.nodes:
                    candidate = {"symbolId": frontier}
                    if not self.already_called("findCallees", candidate):
                        priority = ("Priority evidence gap: the verified path stops at "
                                    f"{self.call_tracker.nodes[frontier]['qualifiedName']}. "
                                    f"A fresh findCallees(symbolId={frontier!r}) can test the next outgoing edge. "
                                    "This is a suggestion from observed graph edges, not a preselected Tool result. ")
                    hints.append(f"Known path frontier is {self.call_tracker.nodes[frontier]['qualifiedName']} (id={frontier}); investigate its outgoing edges, and verify each edge from Tool Observations.")
        if "target_source" in gaps and self._target_id():
            target = self.discovered_symbols[self._target_id()]
            hints.append(f"Source is missing for observed Symbol {target['qualifiedName']}; readFile can inspect {target['filePath']} within observed lines {target['startLine']}-{target['endLine']}.")
        if "related_call_context" in gaps and self._target_id():
            related_ids = [edge.source_id for edge in self.call_tracker.edges.values()
                           if edge.target_id == self._target_id()] + [
                edge.target_id for edge in self.call_tracker.edges.values()
                if edge.source_id == self._target_id()]
            for related_id in related_ids:
                symbol = self.discovered_symbols.get(related_id)
                if symbol and not self._target_lines(related_id):
                    hints.append(f"Related caller/callee source is missing: readFile can inspect observed {symbol['filePath']} lines {symbol['startLine']}-{symbol['endLine']}.")
                    break
        if self.plan and self.plan.task_type == "RUNTIME_ERROR" and "invalid_value_origin" in gaps:
            flow = self.runtime_facts()
            callee = flow["callee_symbol"]
            method = flow["candidate_method"]
            candidate = flow["implementation_candidate"]
            if candidate and not flow["implementation_observed"]:
                priority = ("Priority cross-file evidence gap: the indexed CALLS edge targets an interface method; "
                            "a single signature-matching IMPLEMENTS candidate exists (not runtime dispatch proof): "
                            f"{candidate['qualified_name']} in {candidate['file']} lines "
                            f"{candidate['line']}-{candidate['end_line']}. "
                            f"Use searchSymbol(name={method!r}) to observe its Symbol, then readFile for its source. ")
            elif candidate and not flow["invalid_value_origin"]:
                priority = (f"Priority cross-file evidence gap: observed candidate {candidate['qualified_name']} "
                            f"still lacks an invalid return source. A fresh readFile on {candidate['file']} "
                            f"lines {candidate['line']}-{candidate['end_line']} can verify it. ")
            elif flow["ambiguous_implementations"]:
                priority = ("Interface dispatch has multiple indexed implementations. Do not choose one "
                            "without further binding evidence. ")
            elif method and callee and not flow["invalid_value_origin"]:
                priority = (f"Priority value-source gap: observed assignment calls {method}; "
                            f"its observed Symbol is {callee['raw_name']} in {callee['file']} "
                            f"lines {callee['line']}-{callee['end_line']}. A fresh readFile on that file "
                            "can establish its return source. The source call is not yet proof of a return value. ")
            elif method and not callee:
                priority = (f"Priority value-source gap: observed target source assigns a variable from "
                            f"a call to {method}. A broader searchSymbol(name={method!r}) could locate it "
                            "without inventing its file or class; then inspect the observed return source. ")
            else:
                hints.append("For a runtime error, inspect the target source and relevant callee source for the invalid value origin; a call alone is not proof.")
            for fact in self._target_lines(self._target_id()):
                invoked = re.search(r"\.([A-Za-z_]\w*)\s*\(", fact["code"])
                if invoked and not any(symbol.get("name") == invoked.group(1)
                                       for symbol in self.discovered_symbols.values()):
                    hints.append(f"Observed target source {fact['file']}:{fact['line']} invokes method {invoked.group(1)!r}. If the call graph has no resolved edge, a broader searchSymbol for that method may locate its source; the invocation itself does not prove its return value.")
                    break
        if self.plan and self.plan.task_type == "RUNTIME_ERROR" and "trigger_operation" in gaps and self._target_id():
            target = self.discovered_symbols[self._target_id()]
            hints.append(f"The exception-triggering operation is not observed yet; inspect the full target method source in {target['filePath']} lines {target['startLine']}-{target['endLine']}.")
        if self.plan and self.plan.task_type == "RUNTIME_ERROR" and "cross_file_source" in gaps:
            chain = self.cross_file_evidence()
            hints.append("Cross-file runtime evidence is incomplete: " + ", ".join(chain["missing"]) +
                         ". An indexed interface implementation is only a static candidate, not runtime dispatch proof. "
                         "Do not claim a complete cross-file diagnosis until source lines from both files are observed.")
        if self.consecutive_no_progress >= 2:
            hints.append("NO_PROGRESS: your last Tool choice did not add evidence. Switch Tool or broaden the "
                         "query. An identical Tool+arguments request will be blocked again; do not repeat it.")
        return (priority + "Execution memory (Observation-derived, not Planner proof): "
                + json.dumps({"missing_evidence": gaps, "completion_decision": self.completion_decision(),
                              "observed_symbols": [value["qualifiedName"] for value in list(self.discovered_symbols.values())[-12:]],
                              "observed_files": sorted(self.discovered_files),
                              "verified_call_edges": self.call_tracker.edge_records()[-12:],
                              "verified_chain": self.verified_chain(), "partial_chain": self.partial_chain(),
                              "consecutive_no_progress": self.consecutive_no_progress,
                              "failed_search_count": len(self.failed_searches)}, ensure_ascii=False)
                + "\nPolicy guidance: " + " ".join(hints or ["Use the next Tool only if it can close an evidence gap; otherwise state uncertainty."]))

    def should_block_final(self, remaining_turns: int) -> bool:
        if remaining_turns < 1 or self.consecutive_no_progress >= 3:
            return False
        decision = self.completion_decision()
        if decision == "COMPLETE":
            return False
        if self.plan and self.plan.task_type == "BUSINESS_LOGIC_ERROR" and decision == "PARTIAL" and \
                self.missing_evidence() == ["business_expectation"]:
            return False
        return decision in {"PARTIAL", "INSUFFICIENT_EVIDENCE"}

    def snapshot(self) -> dict:
        return {"seen_tool_calls": len(self.seen_tool_calls),
                "discovered_symbols": list(self.discovered_symbols.values()),
                "discovered_files": sorted(self.discovered_files),
                "discovered_call_edges": self.call_tracker.edge_records(),
                "graph_path_evidence": self.graph_path_evidence,
                "collected_evidence_count": len(self.collected_evidence),
                "last_progress_step": self.last_progress_step,
                "consecutive_no_progress": self.consecutive_no_progress,
                "failed_searches": self.failed_searches,
                "current_evidence_requirements": self.current_evidence_requirements,
                "evidence_checklist": self.checklist(),
                "missing_evidence": self.missing_evidence(),
                "verified_call_chain": self.verified_chain(),
                "partial_call_chain": self.partial_chain(),
                "duplicate_calls": self.duplicate_calls,
                "no_progress_calls": self.no_progress_calls,
                "policy_events": self.policy_events,
                "completion_decision": self.completion_decision(),
                "verified_evidence_counts": {"symbols": len(self.evidence_store.symbols),
                                             "source_lines": len(self.evidence_store.source_lines),
                                             "resolved_call_edges": len(self.evidence_store.edges)},
                "data_flow_chain": self.runtime_facts() if self.plan and self.plan.task_type == "RUNTIME_ERROR" else None,
                "cross_file_evidence": self.cross_file_evidence() if self.plan and self.plan.task_type == "RUNTIME_ERROR" else None}


def has_configuration_capability(tool_names: set[str]) -> bool:
    """Current readFile is Java/Python-only; do not confuse it with a config reader."""
    return bool(tool_names & {"readConfig", "readConfiguration", "searchConfig"})


def complete_final_evidence(result: dict, state: AgentExecutionState, trace: list[dict]) -> dict:
    """Add only facts revalidated from successful source-read or resolved-call Observations."""
    diagnosis = result.get("finalDiagnosis")
    if not isinstance(diagnosis, dict) or not state.plan:
        return result
    if state.plan.task_type == "CALL_CHAIN_ANALYSIS":
        chain = state.verified_chain() or state.partial_chain()
        if len(chain) >= 2 and diagnosis.get("call_chain") != chain:
            diagnosis["call_chain"] = chain
            result["diagnosisIssues"].append("调用路径已按真实 CALLS Observation 核验并规范化；非模型原文")
        # Do not rewrite the model's interpretation. Only factual path/evidence
        # fields can be projected from the verified graph.
        existing = {(item.get("file"), item.get("line"), item.get("code")) for item in diagnosis.get("evidence", [])}
        for left, right in zip(chain, chain[1:]):
            source_id, target_id = state.call_tracker.match_symbol(left), state.call_tracker.match_symbol(right)
            edge = state.call_tracker.edges.get((source_id, target_id))
            if not edge or not edge.file or not edge.code or not isinstance(edge.line, int):
                continue
            # A resolved relation proves the edge. If the same location was also read,
            # use the full observed source line (including punctuation/assignment) as
            # user-facing evidence; never synthesize source text from relation snippets.
            source_fact = state.source_lines.get((edge.file, edge.line))
            exact_source = source_fact if source_fact and edge.code in source_fact["code"] else None
            evidence_code = exact_source["code"] if exact_source else edge.code
            key = (edge.file, edge.line, evidence_code)
            if key in existing:
                continue
            candidate = {"file": edge.file, "line": edge.line, "symbol": left, "code": evidence_code,
                         "reason": "已解析调用边对应的源码" if exact_source else "已解析调用边"}
            validated, issues = validate_evidence_against_trace([candidate], trace)
            if issues or not validated:
                continue
            validated[0]["reason"] = ("执行策略补全：调用边对应的 readFile 源码" if exact_source else
                                      "执行策略补全：已解析调用边")
            diagnosis["evidence"].append(validated[0])
            result["diagnosisIssues"].append(f"已从成功 Observation 补全 {left} → {right} 的"
                                             f"{'readFile 源码' if exact_source else 'CALLS 关系'}；非模型原文")
            existing.add(key)
        return result
    if state.plan.task_type != "RUNTIME_ERROR":
        return result
    runtime = state.runtime_facts()
    existing = {(item.get("file"), item.get("line"), item.get("code")) for item in diagnosis.get("evidence", [])}
    for label, fact in (("无效值来源", runtime["invalid_value_origin"]),
                        ("异常触发操作", runtime["trigger_operation"])):
        if not isinstance(fact, dict):
            continue
        key = (fact["file"], fact["line"], fact["code"])
        if key in existing:
            continue
        symbols = [symbol["qualifiedName"] for symbol in state.discovered_symbols.values()
                   if symbol.get("filePath") == fact["file"] and
                   symbol.get("startLine", 0) <= fact["line"] <= symbol.get("endLine", -1) and
                   symbol.get("type") in {"METHOD", "FUNCTION"}]
        candidate = {"file": fact["file"], "line": fact["line"],
                     "symbol": symbols[0] if len(symbols) == 1 else None,
                     "code": fact["code"], "reason": "Observation 中的" + label}
        validated, issues = validate_evidence_against_trace([candidate], trace)
        if issues or not validated:
            continue
        validated[0]["reason"] = "执行策略补全：Observation 中的" + label
        diagnosis["evidence"].append(validated[0])
        result["diagnosisIssues"].append(f"已从成功 readFile Observation 补全{label}；非模型原文")
        existing.add(key)
    trigger = runtime["trigger_operation"]
    if isinstance(trigger, dict) and isinstance(diagnosis.get("location"), dict):
        location = diagnosis["location"]
        if location.get("file") != trigger["file"] or location.get("line") != trigger["line"]:
            location.update(file=trigger["file"], line=trigger["line"])
            candidates = [symbol["qualifiedName"] for symbol in state.discovered_symbols.values()
                          if symbol.get("filePath") == trigger["file"] and
                          symbol.get("startLine", 0) <= trigger["line"] <= symbol.get("endLine", -1) and
                          symbol.get("type") in {"METHOD", "FUNCTION"}]
            location["symbol"] = candidates[0] if len(candidates) == 1 else None
            result["diagnosisIssues"].append("定位位置已按 readFile 中的异常触发操作修正；非模型原文")
    if runtime["invalid_value_origin"] and runtime["trigger_operation"] and not runtime["related_call_edge"]:
        diagnosis["uncertainty"] = "空值来源和触发操作有源码证据，但相关调用边未被静态解析；仍需运行时确认输入与路径。"
    return result
