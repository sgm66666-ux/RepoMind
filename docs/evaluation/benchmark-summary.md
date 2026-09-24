# RepoMind 冻结场景基准摘要

本页仅总结固定的 8 个场景：Java/Python 运行时错误、价格业务问题、调用链和配置问题。Ground Truth 与事后评分没有为 v1.0 展示而改动；全部 Tool Trace、模型原文和失败仍保留在[详细评测目录](./)。

| 指标 | 初始基线 | 执行策略后 / 当前冻结基线 |
| --- | ---: | ---: |
| 场景状态 | 3 PARTIAL / 3 FAIL / 2 UNSUPPORTED | 6 PARTIAL / 0 FAIL / 2 UNSUPPORTED |
| 平均 Tool 步数 | 6.62 | 5.12 |
| 重复调用尝试 | 7 | 1 |
| 无进展调用 | 27 | 7 |
| MAX_STEPS 响应 | 4 | 0 |
| 有效 FinalDiagnosis | 3/8 | 6/8 |
| Evidence Grounding 通过 | 3/8 | 6/8 |

状态对比以[初始冻结报告](./agent-scenario-benchmark.json)和[执行策略 v2 报告](./agent-scenario-benchmark.execution-policy.v2.json)为依据；调用解析增强后的[最新完整 20 次运行](./agent-scenario-benchmark.call-resolution.json)状态仍为 6 PARTIAL / 2 UNSUPPORTED。平均步数等执行策略指标是两个相应报告的对比，不应误写为最新运行的新测值。

没有 PASS 不等于所有调查都失败：两个配置场景因没有 YAML/properties 读取与关联能力而明确拒绝猜测；价格场景缺少可证明“正确公式”的产品需求；静态调用边也不能证明运行时路径。与此同时，PARTIAL 不能当作 PASS。最新运行还存在 `business-order-return` 调用链匹配退步，详见[调用解析对比](./agent-scenario-benchmark.call-resolution.md)。

**这些数字只描述固定小样本场景中的 Agent 行为与证据约束，不是总体故障定位准确率。**
