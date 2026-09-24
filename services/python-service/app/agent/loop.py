import json
import threading
import time
from queue import Empty, Queue

from app.agent.diagnosis import UNSUPPORTED_MESSAGE
from app.agent.execution_policy import AgentExecutionState, has_configuration_capability
from app.agent.projection import project_final_diagnosis
from app.agent.provider import BaseLLMProvider, ProviderRequestError
from app.agent.planner import ExecutionPlan
from app.agent.tools import ToolRegistry
from app.domain.models import to_dict


class AgentLoop:
    def __init__(self, provider: BaseLLMProvider, registry: ToolRegistry) -> None:
        self.provider = provider
        self.registry = registry

    def run(self, question: str, maxSteps: int = 8, timeoutSeconds: float = 30, plan: ExecutionPlan | None = None) -> dict:
        if not question.strip():
            raise ValueError("question cannot be empty")
        if maxSteps <= 0 or timeoutSeconds <= 0:
            raise ValueError("maxSteps and timeoutSeconds must be positive")
        deadline = time.monotonic() + timeoutSeconds
        messages = []
        if plan is not None:
            messages.append({"role": "system", "content": (
                "Execution Plan (rule-based guidance, not code evidence): "
                + json.dumps(plan.as_dict(), ensure_ascii=False)
                + ". Target keywords may be unverified hints. Follow the preferred Tool path when observations support it; "
                "use observed Symbol IDs and file ranges, adapt to failed or empty results, and do not claim the stop "
                "condition is met without source or relation evidence."
            )})
        messages.append({"role": "user", "content": question})
        plan_result = {"plan": plan.as_dict()} if plan is not None else {}
        trace: list[dict] = []
        state = AgentExecutionState(question, plan)
        tool_schemas = [
            {"type": "function", "function": {"name": item.name, "description": item.description, "parameters": item.inputSchema}}
            for item in self.registry.definitions()
        ]
        if plan is not None and plan.task_type == "CONFIGURATION_ERROR" and not has_configuration_capability(
            {item["function"]["name"] for item in tool_schemas}
        ):
            state.policy_events.append({"step": 0, "status": "UNSUPPORTED", "message": "No configuration reader is registered."})
            return {"status": "UNSUPPORTED", "provider": self.provider.name, "trace": trace, "answer": None,
                    "finalDiagnosis": None, "rawModelOutput": None, "diagnosisStatus": "UNSUPPORTED",
                    "diagnosisIssues": ["当前 ToolRegistry 没有配置文件读取与关联能力"],
                    "userMessage": UNSUPPORTED_MESSAGE, "completionDecision": "UNSUPPORTED",
                    "executionState": state.snapshot(), **plan_result}
        for step in range(1, maxSteps + 1):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {"status": "TIMEOUT", "provider": self.provider.name, "trace": trace, "answer": None,
                        "finalDiagnosis": None, "rawModelOutput": None, "diagnosisStatus": "NOT_COMPLETED",
                        "diagnosisIssues": [], "userMessage": "Agent 执行超时，尚无最终诊断。",
                        "completionDecision": state.completion_decision(), "executionState": state.snapshot(), **plan_result}
            feedback = {"role": "system", "content": state.feedback()}
            # Put current policy feedback after the growing tool history: the most recent
            # empty/duplicate Observation must be visible at the decision point.
            prompt_messages = [*messages, feedback]
            response = self._complete_with_timeout(prompt_messages, tool_schemas, remaining)
            if response is None:
                return {"status": "TIMEOUT", "provider": self.provider.name, "trace": trace, "answer": None,
                        "finalDiagnosis": None, "rawModelOutput": None, "diagnosisStatus": "NOT_COMPLETED",
                        "diagnosisIssues": [], "userMessage": "Agent 执行超时，尚无最终诊断。",
                        "completionDecision": state.completion_decision(), "executionState": state.snapshot(), **plan_result}
            if response.toolCall is None:
                answer = response.text or ""
                if state.should_block_final(maxSteps - step):
                    state.policy_events.append({"step": step, "status": "EVIDENCE_GAP",
                                                "message": "Final answer deferred while actionable evidence is missing."})
                    messages.append({"role": "assistant", "content": answer})
                    messages.append({"role": "system", "content": "Final answer deferred: close the Observation-backed evidence gaps with a different Tool, or explain precisely why no Tool can do so. Do not repeat an earlier call."})
                    continue
                diagnosis_result = project_final_diagnosis(answer, plan, trace, state)
                return {"status": "COMPLETED", "provider": self.provider.name, "trace": trace, "answer": answer,
                        **diagnosis_result, "completionDecision": state.completion_decision(),
                        "executionState": state.snapshot(), **plan_result}
            call = response.toolCall
            if state.already_called(call.name, call.arguments):
                state.record_duplicate(call.name, call.arguments, step)
                duplicate_observation = {"tool": call.name, "success": False, "data": None,
                                         "error": {"code": "DUPLICATE_CALL", "message":
                                                   "The same tool call has already been executed and produced no new evidence."},
                                         "text": "DUPLICATE_CALL: this exact Tool and arguments cannot run again. "
                                                 "Choose another Tool, or change the search filters/query."}
                trace.append({"step": step, "tool": call.name, "input": call.arguments,
                              "observation": duplicate_observation,
                              "observationText": duplicate_observation["text"], "success": False,
                              "output": None, "error": duplicate_observation["error"], "progress": False,
                              "policyStatus": "DUPLICATE_CALL", "toolExecuted": False})
                assistant_call = {"role": "assistant", "tool_call": {"name": call.name, "arguments": call.arguments}}
                if response.toolCallContent is not None:
                    assistant_call["tool_call_content"] = response.toolCallContent
                messages.append(assistant_call)
                messages.append({"role": "tool", "name": call.name,
                                 "content": json.dumps({"observation": duplicate_observation}, ensure_ascii=False)})
                if state.consecutive_no_progress >= 4 and state.completion_decision() != "COMPLETE":
                    return self._no_progress(state, trace, plan_result)
                continue
            result = self.registry.execute(call.name, call.arguments)
            observation = to_dict(result.observationModel)
            progress, new_evidence = state.observe(call.name, call.arguments, observation, step)
            if call.name == "searchSymbol" and result.success:
                index = getattr(self.registry, "analysis_index", None)
                if index is not None:
                    state.complete_verified_graph_path(index)
            trace.append({
                "step": step,
                "tool": call.name,
                "input": call.arguments,
                "observation": observation,
                "observationText": result.observation,
                "success": result.success,
                "output": result.data,
                "error": result.error,
                "progress": progress,
                "newEvidence": new_evidence,
                "policyStatus": "NO_PROGRESS" if state.consecutive_no_progress >= 2 else None,
                "toolExecuted": True,
            })
            assistant_call = {"role": "assistant", "tool_call": {"name": call.name, "arguments": call.arguments}}
            if response.toolCallContent is not None:
                assistant_call["tool_call_content"] = response.toolCallContent
            messages.append(assistant_call)
            messages.append({
                "role": "tool",
                "name": call.name,
                "content": json.dumps({"observation": observation}, ensure_ascii=False),
            })
            if state.consecutive_no_progress >= 4 and state.completion_decision() != "COMPLETE":
                return self._no_progress(state, trace, plan_result)
        if state.completion_decision() in {"COMPLETE", "PARTIAL"} and deadline - time.monotonic() > 0:
            state.policy_events.append({"step": maxSteps + 1, "status": "FINAL_ONLY",
                                        "message": "Tool budget exhausted; one final-only model turn, no Tools exposed."})
            try:
                final_observations = [{"step": item["step"], "tool": item["tool"],
                                       "observation": item["observation"]} for item in trace]
                final_messages = [
                    {"role": "system", "content": "FINAL-ONLY SYNTHESIS. Tool execution has ended. Never emit a Tool Call. "
                     "Use successful Observations below and any separately labelled AST graph path in execution memory. Return one FinalDiagnosis JSON object "
                     "with FACT evidence and an explicitly uncertain INFERENCE. If a requested path is incomplete, "
                     "report only the verified prefix and the missing edge."},
                    {"role": "user", "content": question},
                    {"role": "system", "content": state.feedback()},
                    {"role": "user", "content": "Actual prior Tool Observations (not expected answers): " +
                     json.dumps(final_observations, ensure_ascii=False)},
                ]
                final_response = self._complete_with_timeout(
                    final_messages,
                    [], max(0.001, deadline - time.monotonic()))
            except ProviderRequestError as exc:
                if "unknown Tool" not in str(exc):
                    raise
                state.policy_events.append({"step": maxSteps + 1, "status": "TOOL_BUDGET_EXHAUSTED",
                                            "message": f"Final-only model turn attempted an unavailable Tool: {exc}"})
                final_response = None
            if final_response is not None and final_response.toolCall is None:
                answer = final_response.text or ""
                diagnosis_result = project_final_diagnosis(answer, plan, trace, state)
                return {"status": "COMPLETED", "provider": self.provider.name, "trace": trace, "answer": answer,
                        **diagnosis_result, "completionDecision": state.completion_decision(),
                        "executionState": state.snapshot(), **plan_result}
            if final_response is not None and final_response.toolCall is not None:
                state.policy_events.append({"step": maxSteps + 1, "status": "TOOL_BUDGET_EXHAUSTED",
                                            "message": "Model attempted another Tool Call; it was not executed."})
        config_gap = plan is not None and plan.task_type == "CONFIGURATION_ERROR"
        tail_violation = any(event["status"] == "TOOL_BUDGET_EXHAUSTED" for event in state.policy_events)
        return {"status": "MAX_STEPS", "provider": self.provider.name, "trace": trace, "answer": None,
                "finalDiagnosis": None, "rawModelOutput": None,
                "diagnosisStatus": "UNSUPPORTED" if config_gap else "NOT_COMPLETED",
                "diagnosisIssues": ["Agent 达到 maxSteps，未形成配置文件与使用位置的证据链"] if config_gap else
                                   (["模型在最终轮次继续请求 Tool，未执行"] if tail_violation else []),
                "userMessage": (UNSUPPORTED_MESSAGE + " Agent 已达到工具调用步数上限。") if config_gap
                               else ("模型在工具预算耗尽后仍请求工具，未形成最终诊断。" if tail_violation
                                     else "已达到工具调用步数上限，尚无最终诊断。"),
                "completionDecision": state.completion_decision(), "executionState": state.snapshot(), **plan_result}

    def _no_progress(self, state: AgentExecutionState, trace: list[dict], plan_result: dict) -> dict:
        partial_chain = state.partial_chain()
        detail = (" 已核验的部分调用路径：" + " → ".join(partial_chain) + "；后续调用边缺少证据。") \
            if len(partial_chain) >= 2 and not state.verified_chain() else ""
        return {"status": "NO_PROGRESS", "provider": self.provider.name, "trace": trace, "answer": None,
                "finalDiagnosis": None, "rawModelOutput": None, "diagnosisStatus": "INSUFFICIENT_EVIDENCE",
                "diagnosisIssues": ["连续工具调用未获得新证据，已提前停止而非耗尽 maxSteps"],
                "userMessage": "连续调查未获得新证据，尚不能形成可靠诊断。" + detail,
                "completionDecision": state.completion_decision(), "executionState": state.snapshot(), **plan_result}

    def _complete_with_timeout(self, messages: list[dict], tools: list[dict], timeout: float):
        """Run provider completion on a daemon worker so a blocked provider cannot block the loop."""
        result_queue: Queue[tuple[str, object]] = Queue(maxsize=1)

        def invoke() -> None:
            try:
                result_queue.put(("response", self.provider.complete(messages, tools)))
            except BaseException as exc:  # propagate provider failures to the caller
                result_queue.put(("error", exc))

        threading.Thread(target=invoke, name="repomind-agent-provider", daemon=True).start()
        try:
            kind, value = result_queue.get(timeout=timeout)
        except Empty:
            return None
        if kind == "error":
            raise value
        return value
