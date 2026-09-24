"""Project facts from Tool Observations; accept graph path separately for chain checks."""

import json
from dataclasses import asdict

from pydantic import ValidationError

from app.agent.diagnosis import FinalDiagnosis, _model_json, parse_final_diagnosis, validate_evidence_against_trace
from app.agent.evidence import VerifiedCallEdge, VerifiedEvidenceStore, VerifiedSourceEvidence
from app.agent.execution_policy import AgentExecutionState, query_symbol_hints
from app.agent.planner import ExecutionPlan


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
            "candidate_method": facts["candidate_method"], "max_depth": 3}


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
    def parse(value):
        return parse_final_diagnosis(value, plan, trace, graph_symbols, state.graph_path_evidence)
    try:
        draft = FinalDiagnosis.model_validate(_model_json(raw or ""))
    except (ValueError, TypeError, ValidationError):
        return parse(raw)
    if plan and draft.issue_type != plan.task_type:
        return parse(raw)

    model_claim = {"location": draft.location.model_dump(), "call_chain": list(draft.call_chain),
                   "evidence": [item.model_dump() for item in draft.evidence]}
    projected = draft.model_dump()
    factual_candidates: list[dict] = []
    projection_issues: list[str] = []
    data_flow = _data_flow_chain(state) if draft.issue_type == "RUNTIME_ERROR" else None
    requested = query_symbol_hints(state.question)
    target = store.resolve_symbol(requested[0]) if requested else store.symbols.get(state._target_id() or "")

    if draft.issue_type == "RUNTIME_ERROR" and data_flow:
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
        if data_flow["return_source"] and data_flow["linkage"] != "RESOLVED_CALL_EDGE":
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
        if data_flow and data_flow["return_source"] and data_flow["linkage"] != "RESOLVED_CALL_EDGE":
            guard = "该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。"
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
    return result
