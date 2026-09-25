# Enterprise Showcase · 未解析 CALLS 审计

本页是对 `demo/enterprise-order-showcase` 的逐条审计，不是冻结基准或性能指标。分类按该仓库的实际源码表达式人工校核；[分类脚本](../../scripts/analyze-showcase-unresolved.py)遇到未知模式会报错，不会默认把它算成可解析。每条关系的文件、行、原始代码、类别和处置见[变更前 106 条](unresolved-calls-before.json)与[变更后 59 条](unresolved-calls-after.json)。变更前版本由原始 RepoMind 解析器和库存方法变更前的源码在内存中重建；没有改动原仓库。

## 统计与优先级

| 指标 | 变更前 | 变更后 |
| --- | ---: | ---: |
| 源文件 / Symbol | 60 / 205 | 60 / 205 |
| Relation | 578 | 579 |
| 已解析 CALLS | 53 | 100 |
| 未解析 CALLS | 106 | 59 |
| 其中：项目内可改进缺口 | 58 | 11 |
| 其中：合理未解析 | 48 | 48 |

`Relation` 增加 1 是库存仓储中显式局部变量带来的 REFERENCES，不是新增模块。47 条新增 CALLS 均对应已有项目方法，逐条检查了源表达式、接收者类型、目标 Symbol 和 `resolutionMethod`；未发现错误目标。这个检查不能证明对任意 Java 代码都没有错误边。

## 分类

| 类别 | 前 | 后 | 例子 | 处置与建议 |
| --- | ---: | ---: | --- | --- |
| `SCOPED_RECEIVER_TYPE` | 43 | 0 | `order.getId()`、`stock.getSku()`、`item.getQuantity()` | 项目内缺口；已基于所在方法参数、局部声明和增强 `for` 的词法作用域保守解析。 |
| `STATIC_CLASS_RECEIVER` | 4 | 0 | `Money.of(...)`、`ShowcaseApplication.createController()` | 项目内缺口；唯一类与非重载方法时解析，保留 `STATIC_CLASS_RECEIVER` 来源。 |
| `CHAINED_PROJECT_CALL` | 9 | 9 | `request.getPayment().getMethod()`、`item.getProduct().getSku()` | 项目内缺口；需安全传播前一调用的返回类型。非库存关键链，暂不引入泛化数据流。 |
| `LAMBDA_RECEIVER_UNKNOWN` | 1 | 1 | `record.getOrderId()` | 项目内缺口；需要流式调用的 lambda 参数类型推断，优先级低。 |
| `CONSTRUCTOR_CREATED_RECEIVER` | 1 | 1 | `new StockAllocator(repository).allocate(...)` | 项目内缺口；可局部推断构造结果，但仅出现在测试，暂不改解析器。 |
| `JDK_LIBRARY` | 43 | 43 | `List.copyOf`、`Map.get`、`BigDecimal.valueOf` | 合理未解析：目标不在项目 Symbol 索引中，不应为了数字强行连到项目方法。 |
| `EXTERNAL_LIBRARY` | 5 | 5 | JUnit `assertEquals`、`assertNotNull` | 合理未解析：外部测试库，不是业务调用图节点。 |

库存关键调用 `StockAllocator.allocate → InventoryRepository.findAvailableStock` **原本已解析**到接口方法，变更前后都是 `RECEIVER_TYPE_BINDING`。实现类 `InMemoryInventoryRepository` 通过真实 `IMPLEMENTS` 关系和相同参数类型被列为唯一静态候选；系统没有创建 `StockAllocator → InMemoryInventoryRepository` 的假 CALLS 边。若出现多个实现、重载或签名不匹配，不能擅自选择一个运行时目标。

新增解析范围限于明确声明的项目内接收者和唯一的类名调用；JDK、外部库、链式返回类型、lambda 与构造结果仍保守处理。下一步若处理余下 11 条，应先补精确的返回类型及作用域测试，而非引入完整指针分析或追求 159 条全部解析。
