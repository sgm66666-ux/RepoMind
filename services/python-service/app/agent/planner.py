"""A small, deterministic planning stage. It never reads code or executes Tools."""

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ExecutionPlan:
    task_type: str
    analysis_goal: str
    target_keywords: list[str]
    target_source: str
    required_evidence: list[str]
    preferred_tools: list[str]
    stop_condition: str

    def as_dict(self) -> dict:
        return asdict(self)


class TaskPlanner:
    """Classify a question and recommend evidence, without claiming a Symbol exists."""

    def plan(self, question: str) -> ExecutionPlan:
        query = question.strip()
        if not query:
            raise ValueError("question cannot be empty")

        lower = query.lower()
        if re.search(r"nullpointer|indexerror|keyerror|exception|traceback|空指针|异常|越界|崩溃", lower):
            task_type = "RUNTIME_ERROR"
            goal = "定位异常位置、调用链和错误值来源"
            evidence = ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"]
            tools = ["searchSymbol", "findCallers", "findCallees", "readFile"]
            stop = "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"
        elif re.search(r"调用路径|调用链|调用关系|追踪|调用流程|call chain|call path", lower):
            task_type = "CALL_CHAIN_ANALYSIS"
            goal = "追踪目标 Symbol 的真实调用路径"
            evidence = ["target_symbol", "caller_context", "callee_context"]
            tools = ["searchSymbol", "findCallers", "findCallees"]
            stop = "获得足够的已解析调用关系来回答路径；未解析边需标明不确定"
        elif re.search(r"配置|环境变量|配置文件|configuration|config|property|properties|yaml", lower):
            task_type = "CONFIGURATION_ERROR"
            goal = "定位配置读取位置与缺失或错误的配置来源"
            evidence = ["configuration_reference", "target_method_source", "caller_context"]
            tools = ["searchSymbol", "findReferences", "findCallers", "readFile"]
            stop = "找到配置使用位置及相关源码证据；否则明确配置状态无法从代码确认"
        else:
            task_type = "BUSINESS_LOGIC_ERROR"
            goal = "检查目标业务计算及其输入来源、调用方和返回值影响"
            evidence = ["target_method_source", "caller_context", "input_origin", "return_value_impact"]
            tools = ["searchSymbol", "findCallers", "readFile"]
            stop = "核对目标实现、输入来源与调用方源码后给出有证据的诊断；否则明确证据不足"

        # Only an identifier explicitly written by the user is a known target.
        ascii_start = r"(?<![A-Za-z0-9_$])"
        ascii_end = r"(?![A-Za-z0-9_$])"
        dotted = re.findall(ascii_start + r"[A-Z][A-Za-z0-9_$]*\.([a-z][A-Za-z0-9_$]*)" + ascii_end, query)
        camel = re.findall(ascii_start + r"[a-z][A-Za-z0-9_$]*[A-Z][A-Za-z0-9_$]*" + ascii_end, query)
        keywords = list(dict.fromkeys(dotted + camel))
        target_source = "QUERY" if keywords else "UNSPECIFIED"
        if not keywords and re.search(r"价格|金额|price|amount", lower):
            # Search hints, not a claim that calculatePrice is present in the index.
            keywords = ["calculatePrice", "price"] if re.search(r"价格|price", lower) else ["calculateAmount", "amount"]
            target_source = "HEURISTIC"

        return ExecutionPlan(task_type, goal, keywords, target_source, evidence, tools, stop)
