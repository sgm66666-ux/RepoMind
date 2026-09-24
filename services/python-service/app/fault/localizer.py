from app.analysis.context_builder import CodeContextBuilder
from app.domain.models import FaultLocalizationResult, RelationType, RequestedRange, StackFrame
from app.fault.stacktrace_parser import StackTraceParser


class FaultLocalizer:
    def __init__(self, index) -> None:
        self.index = index
        self.parser = StackTraceParser()
        self.context_builder = CodeContextBuilder(index)

    def localize(self, raw_stack_trace: str) -> FaultLocalizationResult:
        parsed = self.parser.parse(raw_stack_trace)
        frame, target = self._find_target(parsed.frames)
        if frame is None or target is None:
            return FaultLocalizationResult(
                exception=parsed,
                targetFile=None,
                targetSymbol=None,
                lineRange=None,
                stackFrame=frame,
                callers=[],
                callees=[],
                references=[],
                evidence=[{"type": "stackTrace", "raw": parsed.raw, "resolved": False}],
                suspectedCause="No project Symbol could be matched to the supplied Stack Trace.",
                confidence="LOW",
                status="NOT_LOCATED",
            )

        context = self.context_builder.build(target.id)
        callers = context["callers"]
        callees = context["callees"]
        references = [item for item in self.index.references_for(target.id)]
        evidence = [
            {"type": "stackTrace", "filePath": target.filePath, "line": frame.lineNumber, "raw": frame.raw, "resolved": True},
            {"type": "source", "filePath": target.filePath, "lineRange": {"startLine": target.startLine, "endLine": target.endLine}, "content": context["sourceSnippet"]},
            *context["evidence"],
        ]
        cause = self._suspected_cause(target, frame, context)
        confidence = "HIGH" if frame.lineNumber is not None else "MEDIUM"
        return FaultLocalizationResult(
            exception=parsed,
            targetFile=target.filePath,
            targetSymbol=target,
            lineRange=RequestedRange(target.startLine, target.endLine),
            stackFrame=frame,
            callers=callers,
            callees=callees,
            references=references,
            evidence=evidence,
            suspectedCause=cause,
            confidence=confidence,
            status="LOCATED",
        )

    def _suspected_cause(self, target, frame: StackFrame, context: dict) -> str:
        source = (context.get("sourceSnippet") or {}).get("content", "")
        callee_source = "\n".join(
            (self.index.get_symbol(item["symbol"]["id"]) and self.index.read_file(
                item["symbol"]["filePath"], item["symbol"]["startLine"], item["symbol"]["endLine"]
            ).content) or ""
            for item in context.get("callees", [])
        )
        if ".available" in source and "return null" in callee_source and "!= null" not in source:
            detail = "The target dereferences a value returned by a callee without a null check, and the callee source contains `return null`."
        else:
            detail = "No stronger deterministic root-cause pattern was proven from the bounded source evidence."
        return (
            f"Deterministic analysis points to {target.qualifiedName} at "
            f"{target.filePath}:{frame.lineNumber}. {detail} "
            "This is an evidence-based suspicion, not a guaranteed root cause."
        )

    def _find_target(self, frames: list[StackFrame]):
        project_frames = [frame for frame in frames if frame.projectFrame]
        for frame in project_frames + frames:
            if not frame.fileName:
                continue
            candidates = [
                symbol for symbol in self.index.symbols.values()
                if symbol.filePath.rsplit("/", 1)[-1] == frame.fileName
                and symbol.type.value in {"METHOD", "FUNCTION"}
            ]
            if frame.className:
                candidates = [
                    symbol for symbol in candidates
                    if symbol.qualifiedName.endswith(f".{frame.className.rsplit('.', 1)[-1]}.{frame.methodName}")
                    or symbol.name == frame.methodName
                ]
            if frame.lineNumber is not None:
                containing = [symbol for symbol in candidates if symbol.startLine <= frame.lineNumber <= symbol.endLine]
                if containing:
                    return frame, min(containing, key=lambda item: item.endLine - item.startLine)
            by_name = [symbol for symbol in candidates if symbol.name == frame.methodName]
            if len(by_name) == 1:
                return frame, by_name[0]
        return None, None
