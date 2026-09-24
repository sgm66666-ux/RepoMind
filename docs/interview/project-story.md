# RepoMind：面试项目故事

## 1. 问题

我希望让代码仓库故障调查可解释，而不只是让 LLM 猜一个答案。真实 Agent 容易重复搜索、耗尽步数，也可能把没读过的源码、调用链和业务规则说成事实。

## 2. 初始实现

用 tree-sitter 解析 Java/Python，抽取 Symbol 与 Relation，建立保守的 Call Graph；FastAPI 提供代码分析 Tool，AgentLoop 使用本地 Ollama 多轮 Tool Calling，Spring Boot 作为网关，Vue 负责展示。

## 3. 真实评测暴露的问题

在冻结场景中，模型曾重复 `searchSymbol`、到达 `MAX_STEPS`，也曾给价格计算问题虚构正确公式。某些调用链只找到前缀，模型却可能给出完整路径；行号和源码片段也可能与实际 Observation 不符。这些失败保留在旧报告里。

## 4. 改进

TaskPlanner 仅给分析方向；Execution Policy 记录已取得的 Symbol、文件、源码行与关系，阻止重复调用并反馈证据缺口。Verified Evidence Store 与 FinalDiagnosis Projection/Validation 将 Tool Observation 中可核验的 FACT 和模型的 INFERENCE 分开。CallPathFinder 仅沿 AST 已解析边确定性寻找有界路径，图证据与真实 Tool Trace 独立标记。对缺失业务规则或配置分析能力的情况明确保留不确定性。

## 5. 测量到的变化

同一冻结 8 场景，初始状态 3 PARTIAL / 3 FAIL / 2 UNSUPPORTED，执行策略后为 6 PARTIAL / 0 FAIL / 2 UNSUPPORTED；平均 Tool 步数 6.62→5.12，重复尝试 7→1，无进展调用 27→7，MAX_STEPS 4→0，有效诊断与 Evidence Grounding 均为 3→6。最新调用解析运行保持 6 PARTIAL / 2 UNSUPPORTED；[完整口径](../evaluation/benchmark-summary.md)不代表通用故障定位准确率。

## 6. 仍然有限制

静态边不保证运行时路径；Python 动态分派只做保守解析；配置文件关联不支持；没有产品需求就无法确认正确业务公式。模型输出仍可能需要校验，最新业务返回场景的调用链匹配也出现退步。

## 7. 收获

Agent 可靠性不只是 Prompt Engineering。更重要的是明确工具边界、保存每次 Observation 的来源、用确定性代码核验事实，并愿意把证据不足如实展示出来。
