"""Validate a model's final diagnosis against observations, never against Planner hints."""

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from app.agent.planner import ExecutionPlan
from app.agent.evidence import normalize_source_code


class DiagnosisLocation(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    file: str | None
    line: int | None
    symbol: str | None


class DiagnosisEvidence(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    file: str | None
    line: int | None
    symbol: str | None
    code: str | None
    reason: str
    kind: Literal["FACT"] = "FACT"
    source_tool: str | None = None
    source_step: int | None = None


class FinalDiagnosis(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)
    issue_type: Literal["RUNTIME_ERROR", "BUSINESS_LOGIC_ERROR", "CALL_CHAIN_ANALYSIS", "CONFIGURATION_ERROR"]
    summary: str
    location: DiagnosisLocation
    root_cause: str
    evidence: list[DiagnosisEvidence]
    call_chain: list[str]
    fix_suggestion: str
    uncertainty: str
    root_cause_kind: Literal["INFERENCE"] = "INFERENCE"


INVALID_MESSAGE = "本次诊断结果格式异常，分析过程已保留，请展开查看详细 Tool Trace。"
INSUFFICIENT_MESSAGE = "当前工具返回的证据不足以形成可靠诊断；请展开分析过程查看已取得的证据。"
UNSUPPORTED_MESSAGE = "当前工具链无法读取并关联配置文件与代码使用位置，暂不能确认配置故障原因。"


def _normalized(value: str) -> str:
    return normalize_source_code(value)


def _model_json(raw: str) -> object:
    """Accept a single JSON code fence, but never extract JSON from arbitrary prose."""
    candidate = raw.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", candidate, flags=re.DOTALL | re.IGNORECASE)
    return json.loads(fenced.group(1) if fenced else candidate)


def _observed_symbol(name: object, file_path: object, symbols: dict[str, dict]) -> str | None:
    if not isinstance(name, str):
        return None
    matches = [qualified for qualified, value in symbols.items()
               if value.get("filePath") == file_path and
               (qualified == name or qualified.endswith("." + name) or value.get("name") == name)]
    return matches[0] if len(matches) == 1 else None


def _observed_chain_name(name: object, symbols: dict[str, dict]) -> str | None:
    if not isinstance(name, str):
        return None
    matches = [qualified for qualified in symbols if qualified == name or qualified.endswith("." + name)]
    return matches[0] if len(matches) == 1 else None


def _observed_facts(trace: list[dict]) -> tuple[list[dict], dict[str, dict], set[tuple[str, str]]]:
    facts: list[dict] = []
    symbols: dict[str, dict] = {}
    ambiguous_names: set[str] = set()
    edges: set[tuple[str, str]] = set()
    relations: list[tuple[dict, int]] = []

    def add_symbol(value: object) -> None:
        if isinstance(value, dict) and isinstance(value.get("qualifiedName"), str):
            name = value["qualifiedName"]
            if name in ambiguous_names:
                return
            previous = symbols.get(name)
            if previous is not None and previous.get("id") != value.get("id"):
                symbols.pop(name, None)
                ambiguous_names.add(name)
            else:
                symbols[name] = value

    for step in trace:
        if not step.get("success"):
            continue
        observation = step.get("observation") or {}
        data = observation.get("data") if isinstance(observation, dict) else None
        tool, number = step.get("tool"), step.get("step")
        if tool == "searchSymbol" and isinstance(data, list):
            for symbol in data:
                add_symbol(symbol)
                if isinstance(symbol, dict):
                    facts.append({"tool": tool, "step": number, "file": symbol.get("filePath"),
                                  "line": symbol.get("startLine"), "symbol": symbol.get("qualifiedName"), "code": None})
        elif tool == "readFile" and isinstance(data, dict):
            file_path = data.get("filePath")
            requested = data.get("requestedRange") or {}
            start = requested.get("startLine")
            if isinstance(file_path, str) and isinstance(start, int) and isinstance(data.get("content"), str):
                for offset, line in enumerate(data["content"].splitlines()):
                    facts.append({"tool": tool, "step": number, "file": file_path,
                                  "line": start + offset, "symbol": None, "code": line.strip()})
        elif tool in {"findCallers", "findCallees"} and isinstance(data, list):
            for connection in data:
                if not isinstance(connection, dict):
                    continue
                add_symbol(connection.get("symbol"))
                relation = connection.get("relation")
                if isinstance(relation, dict) and relation.get("resolved") is True and relation.get("type") == "CALLS":
                    relations.append((relation, number))

    by_id = {value.get("id"): name for name, value in symbols.items()}
    for relation, number in relations:
        source, target = by_id.get(relation.get("sourceSymbolId")), by_id.get(relation.get("targetSymbolId"))
        if source and target:
            edges.add((source, target))
        facts.append({"tool": "call_relation", "step": number, "file": relation.get("filePath"),
                      "line": relation.get("line"), "symbol": source, "code": relation.get("evidence")})
    return facts, symbols, edges


def validate_evidence_against_trace(evidence: list[dict], trace: list[dict]) -> tuple[list[dict], list[str]]:
    """Return only facts that can be reconstructed from successful Tool observations."""
    facts, symbols, _ = _observed_facts(trace)
    validated: list[dict] = []
    issues: list[str] = []
    for item in evidence:
        file_path, line, code = item.get("file"), item.get("line"), item.get("code")
        candidates = [fact for fact in facts if fact["file"] == file_path and
                      (line is None or fact["line"] == line) and
                      (code is None or isinstance(fact["code"], str) and _normalized(fact["code"]) == _normalized(code))]
        if code is None:
            candidates = [fact for fact in candidates if fact["tool"] == "searchSymbol" and
                          fact["symbol"] == _observed_symbol(item.get("symbol"), file_path, symbols)]
        if not candidates and code is not None and line is not None:
            # A model line number is not proof. Recover it only from a unique exact observed source line.
            same_code = [fact for fact in facts if fact["file"] == file_path and
                         isinstance(fact["code"], str) and _normalized(fact["code"]) == _normalized(code)]
            if len(same_code) == 1:
                candidates = same_code
                issues.append(f"模型行号 {file_path}:{line} 与 Observation 不符，已按源码修正为 {same_code[0]['line']}")
        if not candidates:
            issues.append(f"证据未见于成功 Observation：{file_path}:{line}")
            continue
        fact = candidates[0]
        symbol_name = _observed_symbol(item.get("symbol"), file_path, symbols)
        if symbol_name is None:
            symbol_name = fact["symbol"] if fact["symbol"] in symbols else None
        if symbol_name and fact["tool"] == "readFile":
            symbol = symbols[symbol_name]
            if not (symbol.get("startLine", 0) <= fact["line"] <= symbol.get("endLine", -1)):
                symbol_name = None
        validated.append({"file": fact["file"], "line": fact["line"] if line is not None else None,
                          "symbol": symbol_name, "code": fact["code"],
                          "reason": {"readFile": "readFile 返回的源码", "call_relation": "已解析的 CALLS 关系",
                                     "searchSymbol": "searchSymbol 返回的 Symbol"}[fact["tool"]],
                          "kind": "FACT", "source_tool": fact["tool"], "source_step": fact["step"]})
    return validated, issues


def parse_final_diagnosis(raw: str | None, plan: ExecutionPlan | None, trace: list[dict],
                          graph_symbols: list[dict] | None = None,
                          graph_edges: list[dict] | None = None) -> dict:
    """Keep raw output for experts; expose a diagnosis only after schema and grounding checks."""
    base = {"finalDiagnosis": None, "rawModelOutput": raw, "diagnosisIssues": [], "diagnosisStatus": "INVALID_FORMAT",
            "userMessage": INVALID_MESSAGE}
    if not raw:
        return base
    try:
        parsed = FinalDiagnosis.model_validate(_model_json(raw))
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        base["diagnosisIssues"] = [f"FinalDiagnosis schema: {type(exc).__name__}"]
        return base

    if plan is not None and parsed.issue_type != plan.task_type:
        base["diagnosisIssues"] = ["FinalDiagnosis.issue_type 与实际 Planner 分类不一致"]
        return base
    if parsed.issue_type == "CONFIGURATION_ERROR":
        # The current scanner/reader expose only Java and Python. Source-code references
        # cannot establish the value of a YAML/properties setting or its deployment state.
        config_observed = any(
            step.get("success") and step.get("tool") == "readFile" and
            str((step.get("observation") or {}).get("data", {}).get("filePath", "")).lower().endswith(
                (".yml", ".yaml", ".properties"))
            for step in trace
        )
        if not config_observed:
            base.update(diagnosisStatus="UNSUPPORTED", userMessage=UNSUPPORTED_MESSAGE,
                        diagnosisIssues=["当前 Observation 未包含配置文件及代码使用位置的可核验关联"])
            return base
    validated, issues = validate_evidence_against_trace(
        [item.model_dump() for item in parsed.evidence], trace)
    if not validated:
        base.update(diagnosisStatus="INSUFFICIENT_EVIDENCE", userMessage=INSUFFICIENT_MESSAGE,
                    diagnosisIssues=issues or ["FinalDiagnosis 未包含可核验的证据"])
        return base

    facts, symbols, edges = _observed_facts(trace)
    # Graph context is independently verified by CallPathFinder. It is not a
    # Tool Observation and must never be used to validate claimed source facts.
    if graph_symbols and graph_edges:
        ambiguous = {name for name in {item.get("qualifiedName") for item in graph_symbols}
                     if name and sum(item.get("qualifiedName") == name for item in graph_symbols) > 1}
        for item in graph_symbols:
            name = item.get("qualifiedName")
            if isinstance(name, str) and name not in ambiguous:
                symbols.setdefault(name, item)
        by_id = {item.get("id"): name for name, item in symbols.items()}
        for edge in graph_edges:
            source, target = by_id.get(edge.get("sourceSymbolId")), by_id.get(edge.get("targetSymbolId"))
            if source and target and edge.get("source") == "AST_RESOLVED_CALL_GRAPH":
                edges.add((source, target))
                facts.append({"tool": "resolved_call_graph", "step": 0, "file": edge.get("filePath"),
                              "line": edge.get("line"), "symbol": source, "code": edge.get("evidence")})
    location = parsed.location.model_dump()
    if location["file"] not in ({fact["file"] for fact in facts} |
                                {symbol.get("filePath") for symbol in symbols.values()}):
        location["file"] = None
        issues.append("定位文件未见于 Observation")
    location["symbol"] = _observed_symbol(location["symbol"], location["file"], symbols)
    if location["symbol"] is None:
        location["symbol"] = None
        issues.append("定位 Symbol 未见于 Observation")
    source_evidence = [item for item in validated if item["file"] == location["file"] and
                       item["source_tool"] == "readFile" and item["line"] is not None]
    if source_evidence and location["line"] not in {item["line"] for item in source_evidence}:
        location["line"] = source_evidence[0]["line"]
        issues.append("模型定位行号与源码证据不符，已按已核验代码行修正")
    elif location["line"] is not None and not any(
        fact["file"] == location["file"] and fact["line"] == location["line"]
        for fact in facts if fact["tool"] in {"readFile", "call_relation"}
    ) and not any(symbol.get("filePath") == location["file"] and
                  symbol.get("startLine") == location["line"] for symbol in symbols.values()):
        location["line"] = None
        issues.append("定位行号未见于源码或已解析调用 Observation")

    normalized_chain = [_observed_chain_name(name, symbols) for name in parsed.call_chain]
    call_chain: list[str] = []
    if normalized_chain and normalized_chain[0] is not None:
        call_chain = [normalized_chain[0]]
        for node in normalized_chain[1:]:
            if node is None or (call_chain[-1], node) not in edges:
                issues.append("调用链含有未观察到的已解析关系；仅保留已核验前缀")
                break
            call_chain.append(node)
    elif parsed.call_chain:
        issues.append("调用链起点 Symbol 未见于 Observation")

    incomplete_chain = len(call_chain) != len(parsed.call_chain)
    if parsed.issue_type != "CALL_CHAIN_ANALYSIS" and incomplete_chain:
        call_chain = []

    if parsed.issue_type == "CALL_CHAIN_ANALYSIS" and len(call_chain) < 2:
        base.update(diagnosisStatus="INSUFFICIENT_EVIDENCE", userMessage=INSUFFICIENT_MESSAGE,
                    diagnosisIssues=issues + ["未取得可核验的完整调用边，不能声称调用路径已追踪"])
        return base

    root_cause = parsed.root_cause.strip()
    fix_suggestion = parsed.fix_suggestion.strip()
    summary = parsed.summary.strip()
    uncertainty = parsed.uncertainty.strip()
    if parsed.issue_type == "CALL_CHAIN_ANALYSIS" and incomplete_chain:
        summary = "仅核验了部分调用路径"
        root_cause = "已核验的调用边只覆盖当前显示的路径前缀；到目标 Symbol 的后续关系仍缺少 Observation。"
        fix_suggestion = "继续沿已核验路径调查缺失的调用边。"
        uncertainty = "不能依据方法名或源码文件名推断未观察到的边。"
    if parsed.issue_type == "BUSINESS_LOGIC_ERROR":
        # Source reveals the current formula, but without requirements it cannot prove the correct formula.
        unsupported = re.search(r"(?:correct (?:calculation|formula).*?should|正确公式|正确计算.*?应|必须改为|应该是\s*[A-Za-z]|改为\s*return|修正.{0,12}公式为\s*(?:return\s+)?[A-Za-z]|should be\s*[A-Za-z])",
                                root_cause + " " + fix_suggestion, flags=re.IGNORECASE)
        if unsupported:
            issues.append("模型声称确定的正确业务公式，但 Observation 中没有业务规则")
            summary = "已定位价格计算实现；是否符合业务规则仍需确认"
            root_cause = "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。"
            fix_suggestion = "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。"
            uncertainty = "现有源码可确认当前计算表达式，但未提供预期计价规则。"
        elif not uncertainty or re.fullmatch(r"[\d.]+", uncertainty):
            uncertainty = "现有源码可确认当前实现；预期业务规则仍需核对。"
    if not root_cause:
        base.update(diagnosisStatus="INSUFFICIENT_EVIDENCE", userMessage=INSUFFICIENT_MESSAGE,
                    diagnosisIssues=issues + ["缺少可用原因分析"])
        return base

    diagnosis = parsed.model_dump()
    diagnosis.update(summary=summary, location=location, evidence=validated, call_chain=call_chain,
                     root_cause=root_cause, fix_suggestion=fix_suggestion, uncertainty=uncertainty)
    base.update(finalDiagnosis=diagnosis, diagnosisStatus="VALID", userMessage=None, diagnosisIssues=issues)
    return base
