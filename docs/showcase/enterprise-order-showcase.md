# Enterprise Order Showcase · 实际演示记录

本记录只描述 `demo/enterprise-order-showcase` 在本地的验证；它不是冻结的 8 场景基准，也不代表总体故障定位准确率。原有小 Demo 与基准未改动。库存仓储源码增加了显式空值返回分支，以便如实展示已有返回语义；没有添加文件或答案注释。

## 范围与构建

- 独立 Maven 工程；59 个主代码 Java 文件、1 个测试 Java 文件，`mvn test` 通过。
- 订单入口：`OrderController.createOrder` → `OrderApplicationService.createOrder` → `OrderService.processOrder`。
- 订单处理从域服务分支到客户、定价、库存、支付、配送、通知、审计与仓储；存储和外部客户端为本地实现。

## RepoMind 实际分析

| 指标 | 本次结果 |
| --- | ---: |
| 扫描的 Java 源文件 | 60 |
| Symbol | 205（50 Class、10 Interface、145 Method） |
| Relation | 579（变更前 578） |
| 已解析 CALLS | 100（变更前 53） |
| 未解析 CALLS | 59（变更前 106） |
| 完整 Call Graph | 82 节点、100 条已解析边 |
| 解析问题 | 0 |

这些是重新启动 FastAPI、从空索引分析该仓库得到的结果；Relation 包括 IMPORTS、REFERENCES 等，不等同于调用边。未解析调用不应作为确定路径使用。[逐条未解析 CALLS 审计](unresolved-calls-analysis.md)将原始 106 条分成 58 条项目内缺口和 48 条合理未解析；当前余下 11 条项目内缺口与 48 条合理未解析。47 条新增 CALLS 均保留解析方法来源，没有将接口调用假连到实现类。

CallPathFinder 在已解析边上验证了一条 6 节点静态路径：

```text
OrderController.createOrder
→ OrderApplicationService.createOrder
→ OrderService.processOrder
→ InventoryService.reserveInventory
→ StockAllocator.allocate
→ InventoryRepository.findAvailableStock
```

接口上的终点是 `InventoryRepository.findAvailableStock`，不能凭这条 CALLS 路径直接声称运行时必然选择 `InMemoryInventoryRepository`；实现关系需另行核对。

## 库存跨文件证据链

实际源码关系如下（行号以当前 Showcase 为准）：

1. `StockAllocator.java:8`：`Stock stock = repository.findAvailableStock(sku);`，`readFile` 证实赋值；`CALLS` 已解析到 `InventoryRepository.findAvailableStock` 接口 Symbol。
2. `InMemoryInventoryRepository.java:5`：真实 `IMPLEMENTS` 关系指向 `InventoryRepository`。当前索引中唯一签名匹配的实现方法是静态候选，**不证明运行时实际分派**。
3. `InMemoryInventoryRepository.java:10`：`if (stock == null) return null;`，`readFile` 证实存在显式空值返回分支。
4. `StockAllocator.java:9`：`stock.getAvailableQuantity()`，`readFile` 证实在无空值检查时解引用。

Execution Policy 的 `crossFileEvidence` 只有在生产方法 Symbol、空值返回、接口调用边、唯一实现关系、赋值、解引用与两文件源码全部具备时才标记 `complete`。`FinalDiagnosis` 还需确实包含两份文件的 Observation 源码行，才标记 `final_diagnosis_complete`。`CALL_EDGE` 与 `IMPLEMENTS` 分别保留索引关系来源；三条源码证据保留 `file`、`line`、`symbol`、`code`、`evidence_type`、`source_tool=readFile` 与 `source_step`。模型原文不能进入 Verified Evidence Store。

此前单文件诊断的断点是：Agent 常只读取 `StockAllocator.java` 或接口文件；同名接口与实现方法使原有值追踪无法唯一选取生产者；方法调用式解引用没有被触发点正则识别；模型输出的 `evidence` / `suggestion` 键也未符合 FinalDiagnosis schema。现通过唯一签名匹配的静态候选、明确的缺失证据反馈和通用字段兼容处理这些断点；所有兼容后的源码仍逐项与成功 Observation 比对。非本次库存链的多实现分派仍保持不确定。

## 真实 Ollama Agent 观察

Provider：`ollama:qwen2.5-coder:14b:json-tool-compat`。这是 JSON 工具调用兼容方式，不是原生 Tool Calling。下列观察来自真实 Tool Trace，模型输出可能变化。

- **深层调用链**：一次执行为 `searchSymbol → searchSymbol → findCallers → findCallers → findCallers → findCallers → readFile`。模型原文给出六节点路径，但 FinalDiagnosis 结构校验失败，因此界面显示“暂未形成可核验的最终诊断”。上面的六节点路径由独立 CallPathFinder 验证，不能把模型原文算作有效 Agent 最终诊断。[实际界面](../screenshots/showcase-call-chain.png)
- **库存空值风险（本阶段）**：最终代码重新启动服务并重新分析后，连续两批共 6 次独立真实 Ollama 请求，均完成六步 Tool Trace；其中 **5/6** 为 `COMPLETED / VALID` 且 `crossFileEvidence.final_diagnosis_complete=true`，另一次是 `COMPLETED / INVALID_FORMAT`，不能算作有效诊断。实际 Tool Trace 均为 `searchSymbol → readFile → searchSymbol → readFile → findCallers → readFile`；读取 `StockAllocator.java`、`InMemoryInventoryRepository.java` 与 `InventoryService.java`。有效 FinalDiagnosis 的 FACT 源码来自前两文件，包含赋值、空值返回和解引用；静态调用链只到 `InventoryRepository` 接口方法。模型把风险说成已发生异常时，Projection 降级为“潜在空值解引用风险”，保留原文供审计。[跨文件诊断截图](../screenshots/showcase-cross-file-diagnosis.png) · [首批 2/3 记录](enterprise-inventory-ollama-runs.json) · [第二批 3/3 记录（含模型原文）](enterprise-inventory-ollama-runs-second-batch.json)
- **定价规则**：一次执行为 `searchSymbol → readFile → findCallers → readFile`，FinalDiagnosis 引用 `PricingService.java` 与调用方 `OrderService.java`，并提示业务预期仍需确认。模型将源码中的固定 `4.99` 称为“美元”，而源码未定义币种；这属于未经证实的模型推断，不能作为事实引用。

在字段兼容前的三次运行中，Agent 已读到两文件，内部证据链完整，但模型 JSON 缺少 `call_chain`、将 `code` 写成 `evidence` 等，FinalDiagnosis **0/3** 通过；[失败记录](enterprise-inventory-ollama-runs-precompat.json)仍保留。字段兼容之后、静态链投影之前的另三次运行是 **3/3** 有效跨文件证据，[中间记录](enterprise-inventory-ollama-runs-pre-chain-projection.json)也保留。最终代码的首批 **2/3** 表明 JSON 格式仍有波动；该批审计脚本未保存模型原文，因此不能进一步归因这一次 `INVALID_FORMAT`。第二批脚本开始保存原文，但 **3/3** 也只代表这个问题、同一模型和本地环境中的三次观察，不能外推为总体稳定性或运行时必然故障。

## 截图范围

- [Showcase 概览](../screenshots/showcase-overview.png)：真实索引统计与拍摄时的服务状态；截图裁掉了下方因全图适配而难以阅读的 Call Graph 预览。
- [完整 Call Graph](../screenshots/showcase-call-graph-full.png)：真实 API 返回的 82 节点 / 100 边全图；节点较密，仅作拓扑总览。
- [可读聚焦图](../screenshots/showcase-call-graph-focus.png)：截图浏览器从同一次真实 Call Graph API 响应中只选取订单主干及定价、库存、支付分支的 6 个 Symbol 与 5 条已解析边，再交由原有 Cytoscape 组件渲染；这**不是**前端现有的筛选功能，也不是全仓图。没有增造节点或边。截图浏览器仅为拍摄扩大画布并使用页面原有缩放/拖拽控件，不改变正常应用。
- [深链路 Agent 界面](../screenshots/showcase-call-chain.png)：展示结构校验失败的真实边界，非成功诊断截图。
- [旧库存诊断界面](../screenshots/showcase-runtime-diagnosis.png)：改进前的单文件有效诊断，保留作为边界对照。
- [跨文件库存诊断界面](../screenshots/showcase-cross-file-diagnosis.png)：最终版本的真实有效 FinalDiagnosis，清楚列出两份源码文件的 FACT 证据；Agent 原文仍受本地模型输出影响。

截图均由无头浏览器在真实服务上拍摄，不包含鼠标或 AI 指针覆盖；图与诊断不代表生产可用性。
