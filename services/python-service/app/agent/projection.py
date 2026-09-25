"""Project facts from Tool Observations; accept graph path separately for chain checks."""

import json
from dataclasses import asdict

from pydantic import ValidationError

from app.agent.diagnosis import FinalDiagnosis, _model_json, parse_final_diagnosis, validate_evidence_against_trace
from app.agent.evidence import VerifiedCallEdge, VerifiedEvidenceStore, VerifiedSourceEvidence
from app.agent.execution_policy import AgentExecutionState, query_symbol_hints
from app.agent.planner import ExecutionPlan
from app.domain.models import to_dict


def _fact_candidate(store: VerifiedEvidenceStore, fact: VerifiedSourceEvidence,
                    reason: str) -> dict:
    owner = store.symbol_at(fact.file, fact.line)
    return {"file": fact.file, "line": fact.line,
            "symbol": owner.raw_name if owner else None,
            "code": fact.code, "reason": reason}


def _edge_candidate(store: VerifiedEvidenceStore, edge: VerifiedCallEdge) -> dict:
    source = store.source_at(edge.file, edge.line)
    source_code = source.code if source and edge.code in source.code else edge.code
    symbol = store.symbols.get(edge.source_id)
    return {"file": edge.file, "line": edge.line,
            "symbol": symbol.raw_name if symbol else None,
            "code": source_code, "reason": "已解析 CALLS 边对应的源码" if source and edge.code in source.code
            else "已解析 CALLS 关系"}


def _data_flow_chain(state: AgentExecutionState) -> dict:
    facts = state.runtime_facts()
    return {"return_source": facts["invalid_value_origin"], "assignment": facts["assignment"],
            "exception_site": facts["trigger_operation"],
            "linkage": facts["source_to_usage_linkage"],
            "resolved_call_edge": facts["related_call_edge"],
            "candidate_method": facts["candidate_method"], "max_depth": 3,
            "implementation_candidate": facts["implementation_candidate"],
            "implementation_relation": facts["implementation_relation"]}


def _final_cross_file_status(state: AgentExecutionState, diagnosis: dict | None) -> dict:
    chain = state.cross_file_evidence()
    required = [item for item in chain["chain"] if item["type"] in
                {"RETURN_VALUE", "ASSIGNMENT", "DEREFERENCE"}]
    observed = {(item.get("file"), item.get("line"), item.get("code")) for item in
                (diagnosis or {}).get("evidence", []) if item.get("source_tool") == "readFile"}
    chain["final_diagnosis_complete"] = bool(chain["complete"] and len(required) == 3 and all(
        (item["file"], item["line"], item["code"]) in observed for item in required))
    return chain


def _compatible_draft(raw: str) -> tuple[FinalDiagnosis, list[str]]:
    """Repair only common field names; grounding still happens against real Observations."""
    value = _model_json(raw)
    if not isinstance(value, dict):
        raise ValueError("FinalDiagnosis must be an object")
    adjusted = dict(value)
    changes: list[str] = []
    if "fix_suggestion" not in adjusted and isinstance(adjusted.get("suggestion"), str):
        adjusted["fix_suggestion"] = adjusted["suggestion"]
        changes.append("suggestion -> fix_suggestion")
    if "call_chain" not in adjusted:
        adjusted["call_chain"] = []
        changes.append("missing call_chain -> []")
    if isinstance(adjusted.get("evidence"), list):
        evidence = []
        for item in adjusted["evidence"]:
            if not isinstance(item, dict):
                evidence.append(item)
                continue
            candidate = dict(item)
            if "code" not in candidate and isinstance(candidate.get("evidence"), str):
                candidate["code"] = candidate["evidence"]
                changes.append("evidence[].evidence -> code")
            if "reason" not in candidate:
                candidate["reason"] = "模型提出的待核验片段"
                changes.append("missing evidence[].reason -> pending verification")
            evidence.append(candidate)
        adjusted["evidence"] = evidence
    return FinalDiagnosis.model_validate(adjusted), sorted(set(changes))


def project_final_diagnosis(raw: str | None, plan: ExecutionPlan | None,
                            trace: list[dict], state: AgentExecutionState) -> dict:
    """Keep model inference; replace/complete only independently verified factual fields.

    The draft remains in rawModelOutput. We submit the evidence-enriched draft to
    the unchanged FinalDiagnosis validator, then revalidate all projected facts.
    """
    store = state.evidence_store
    graph_symbols = [item for item in state.call_tracker.nodes.values() if item.get("id") in
                     {edge["sourceSymbolId"] for edge in state.graph_path_evidence} |
                     {edge["targetSymbolId"] for edge in state.graph_path_evidence}]
    graph_edges = list(state.graph_path_evidence)
    runtime_edge = state.runtime_facts()["related_call_edge"] if plan and plan.task_type == "RUNTIME_ERROR" else None
    if runtime_edge and runtime_edge.get("source_tool") == "indexed_call_graph" and state.analysis_index:
        source = state.analysis_index.symbols.get(runtime_edge["source_id"])
        target_symbol = state.analysis_index.symbols.get(runtime_edge["target_id"])
        if source and target_symbol:
            graph_symbols.extend((to_dict(source), to_dict(target_symbol)))
            graph_edges.append({"sourceSymbolId": source.id, "targetSymbolId": target_symbol.id,
                                "filePath": runtime_edge["file"], "line": runtime_edge["line"],
                                "evidence": runtime_edge["code"], "source": "AST_RESOLVED_CALL_GRAPH"})
    def parse(value):
        return parse_final_diagnosis(value, plan, trace, graph_symbols, graph_edges)
    try:
        draft, compatibility_changes = _compatible_draft(raw or "")
    except (ValueError, TypeError, ValidationError):
        result = parse(raw)
        if plan and plan.task_type == "RUNTIME_ERROR":
            result["crossFileEvidence"] = _final_cross_file_status(state, result["finalDiagnosis"])
        return result
    if plan and draft.issue_type != plan.task_type:
        return parse(raw)

    model_claim = {"location": draft.location.model_dump(), "call_chain": list(draft.call_chain),
                   "evidence": [item.model_dump() for item in draft.evidence]}
    projected = draft.model_dump()
    factual_candidates: list[dict] = []
    projection_issues: list[str] = []
    if compatibility_changes:
        projection_issues.append("STRUCTURAL_COMPATIBILITY: " + ", ".join(compatibility_changes) +
                                 "；所有源码仍需 Observation 核验")
    data_flow = _data_flow_chain(state) if draft.issue_type == "RUNTIME_ERROR" else None
    requested = query_symbol_hints(state.question)
    target = store.resolve_symbol(requested[0]) if requested else store.symbols.get(state._target_id() or "")

    if draft.issue_type == "RUNTIME_ERROR" and data_flow:
        if runtime_edge and runtime_edge.get("source_tool") == "indexed_call_graph" and len(graph_symbols) >= 2:
            source_name, target_name = graph_symbols[-2]["qualifiedName"], graph_symbols[-1]["qualifiedName"]
            projected["call_chain"] = [source_name, target_name]
            if projected["call_chain"] != model_claim["call_chain"]:
                projection_issues.append("CALL_CHAIN_PROJECTED_FROM_VERIFIED_STATIC_EDGE: not runtime execution")
        for label, key in (("赋值来源", "assignment"), ("无效值返回", "return_source"),
                           ("异常触发位置", "exception_site")):
            value = data_flow[key]
            if not value:
                continue
            source = store.source_at(value["file"], value["line"])
            if source:
                factual_candidates.append(_fact_candidate(store, source, "Observation：" + label))
        site = data_flow["exception_site"]
        if site:
            owner = store.symbol_at(site["file"], site["line"])
            projected["location"] = {"file": site["file"], "line": site["line"],
                                     "symbol": owner.raw_name if owner else None}
        if data_flow["return_source"] and not data_flow["resolved_call_edge"]:
            projection_issues.append("CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边")

    if draft.issue_type == "CALL_CHAIN_ANALYSIS" and len(requested) >= 2:
        path = store.call_path(requested[0], requested[-1])
        if not path:
            # A partial chain may still be safely retained by the strict parser.
            projection_issues.append("CALL_EDGE_NOT_VERIFIED: 请求的完整路径缺少已解析边")
        else:
            projected["call_chain"] = [store.canonical_name(symbol.symbol_id) for symbol in path]
            if projected["call_chain"] != model_claim["call_chain"]:
                projection_issues.append("CALL_CHAIN_PROJECTED_FROM_VERIFIED_EDGES")
            # Static graph relations remain in graph_path_evidence, not in the
            # Tool-only FinalDiagnosis evidence array. Anchor the answer to an
            # actual searchSymbol Observation even if the model supplied only
            # graph-edge claims there.
            observed_start = next((symbol for symbol in path if symbol.source_tool == "searchSymbol"), None)
            if observed_start:
                factual_candidates.append({"file": observed_start.file, "line": observed_start.line,
                                           "symbol": observed_start.raw_name, "code": None,
                                           "reason": "searchSymbol 返回的起点 Symbol"})
            for left, right in zip(path, path[1:]):
                edge = store.edges.get((left.symbol_id, right.symbol_id))
                if edge and edge.source_tool != "resolved_call_graph":
                    factual_candidates.append(_edge_candidate(store, edge))
            end = path[-1]
            end_source = store.source_for_symbol(end.symbol_id)
            projected["location"] = {"file": end.file,
                                     "line": end_source[0].line if end_source else end.line,
                                     "symbol": end.raw_name}

    if draft.issue_type == "BUSINESS_LOGIC_ERROR" and target:
        for source in store.source_for_symbol(target.symbol_id):
            if "return" in source.code:
                factual_candidates.append(_fact_candidate(store, source, "Observation：当前实现"))
        for edge in store.edges.values():
            if edge.source_id == target.symbol_id or edge.target_id == target.symbol_id:
                factual_candidates.append(_edge_candidate(store, edge))

    # Preserve model claims for audit. The strict validator removes ungrounded ones;
    # all system additions are independently reconstructed from successful Tool data.
    verified_candidates, candidate_issues = validate_evidence_against_trace(factual_candidates, trace)
    projection_issues.extend("EVIDENCE_NOT_FOUND: " + issue for issue in candidate_issues)
    existing = {(item.get("file"), item.get("line"), item.get("code"), item.get("symbol"))
                for item in projected["evidence"]}
    added = 0
    for item in verified_candidates:
        key = (item["file"], item["line"], item["code"], item["symbol"])
        if key not in existing:
            projected["evidence"].append(item)
            existing.add(key)
            added += 1
    if added:
        projection_issues.append(f"EVIDENCE_PROJECTED_FROM_TOOL: {added} verified facts")

    claim_location = model_claim["location"]
    if claim_location.get("line") != projected["location"].get("line"):
        projection_issues.append("MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置")
    if claim_location.get("symbol") != projected["location"].get("symbol"):
        # Name variants that resolve to the same Symbol are not a mismatch.
        original = store.resolve_symbol(claim_location.get("symbol"), file=claim_location.get("file"))
        corrected = store.resolve_symbol(projected["location"].get("symbol"),
                                         file=projected["location"].get("file"))
        if not original or not corrected or original.symbol_id != corrected.symbol_id:
            projection_issues.append("MODEL_SYMBOL_MISMATCH: 使用 Observation 中的 Symbol")

    result = parse(json.dumps(projected, ensure_ascii=False))
    result["rawModelOutput"] = raw
    parser_issues = result["diagnosisIssues"]
    if any("证据未见于成功 Observation" in issue for issue in parser_issues):
        projection_issues.append("EVIDENCE_NOT_FOUND: 模型原稿包含无法核验的源码")
    if any("调用链含有未观察到" in issue for issue in parser_issues):
        projection_issues.append("CALL_EDGE_NOT_VERIFIED: 模型原稿包含无法核验的调用边")
    if any("行号" in issue for issue in parser_issues) and not any(
            issue.startswith("MODEL_LINE_MISMATCH") for issue in projection_issues):
        projection_issues.append("MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正")
    if any("模型声称确定的正确业务公式" in issue for issue in parser_issues):
        projection_issues.append("UNSUPPORTED_CLAIM_REMOVED: 无需求证据的公式断言已移除")
    result["diagnosisIssues"].extend(projection_issues)
    if result["finalDiagnosis"]:
        diagnosis = result["finalDiagnosis"]
        # Deduplicate even when the model and multiple Tools reported the same fact.
        seen: set[tuple] = set()
        deduped: list[dict] = []
        for item in diagnosis["evidence"]:
            key = (item.get("file"), item.get("line"), item.get("code"), item.get("symbol"))
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        diagnosis["evidence"] = deduped
        if draft.issue_type == "CALL_CHAIN_ANALYSIS" and len(requested) >= 2:
            path = store.call_path(requested[0], requested[-1])
            if path:
                diagnosis["call_chain"] = [store.canonical_name(symbol.symbol_id) for symbol in path]
        if data_flow and data_flow["return_source"] and not data_flow["resolved_call_edge"]:
            guard = "该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。"
            if guard not in diagnosis["uncertainty"]:
                diagnosis["uncertainty"] = (diagnosis["uncertainty"].rstrip() + " " + guard).strip()
        if data_flow and data_flow["linkage"] == "UNIQUE_INTERFACE_IMPLEMENTATION_CANDIDATE":
            guard = "唯一接口实现仅是当前索引中的静态候选，不能证明运行时实际分派或空值输入发生。"
            if guard not in diagnosis["uncertainty"]:
                diagnosis["uncertainty"] = (diagnosis["uncertainty"].rstrip() + " " + guard).strip()
        # An unchanged model inference is not reclassified as an observed fact.
        diagnosis["root_cause_kind"] = "INFERENCE"
    result["evidenceProjection"] = {
        "modelClaim": model_claim,
        "systemResult": {"location": result["finalDiagnosis"]["location"] if result["finalDiagnosis"] else None,
                         "call_chain": result["finalDiagnosis"]["call_chain"] if result["finalDiagnosis"] else [],
                         "projected_fact_count": added},
        "dataFlowChain": data_flow,
        "verifiedSymbolCount": len(store.symbols), "verifiedSourceLineCount": len(store.source_lines),
        "verifiedCallEdgeCount": len(store.edges),
    }
    if draft.issue_type == "RUNTIME_ERROR":
        result["crossFileEvidence"] = _final_cross_file_status(state, result["finalDiagnosis"])
        if result["crossFileEvidence"]["applicable"] and not result["crossFileEvidence"]["final_diagnosis_complete"]:
            result["diagnosisIssues"].append("跨文件证据链尚未完整进入 FinalDiagnosis；详见 crossFileEvidence.missing")
        elif result["crossFileEvidence"]["final_diagnosis_complete"] and result["finalDiagnosis"]:
            # Source and static dispatch establish a risk, not an observed runtime event.
            diagnosis = result["finalDiagnosis"]
            diagnosis["summary"] = "发现潜在空值解引用风险（静态证据）"
            diagnosis["root_cause"] = ("若已观察到的空值返回分支在运行时发生，随后对该值的解引用可能触发 "
                                       "NullPointerException；静态证据不能证明该分支实际执行。")
            diagnosis["uncertainty"] = ("当前仅核验静态调用与两处源码；唯一接口实现是静态候选，"
                                         "未观察到运行时输入、实际分派或异常发生。")
            result["diagnosisIssues"].append(
                "RUNTIME_EXECUTION_NOT_OBSERVED: 模型的确定性运行时表述已降级为静态风险推断；原文保留在 rawModelOutput")
    return result
