# 企业订单 Showcase

这是独立的 Java/Maven 电商订单处理示例仓库，供 RepoMind 做较大代码仓库的静态调用图与 Agent 演示。它不依赖 RepoMind 主应用，也不属于冻结的评测场景。

## 业务与结构

- `api`：订单请求、响应和入口控制器。
- `application`：订单用例编排与对象组装。
- `domain`：订单、客户、商品、库存、定价、支付、配送和通知规则。
- `infrastructure`：内存仓储、模拟支付通道、配送提供方、消息发送和审计。
- `common`：共享业务异常。

`OrderController.createOrder` 进入应用层，订单域服务根据客户、商品和定价信息处理库存、支付、配送、通知及审计。存储和外部客户端均为本地实现，不需要联网。

## 本地运行

在本目录运行：

```powershell
mvn test
mvn package
java -cp target/classes com.repomind.showcase.ShowcaseApplication
```

在 RepoMind 根目录启动分析服务后，可运行 `./scripts/prepare-showcase.ps1` 索引本仓库；也可在前端代码仓库页面输入本目录的绝对路径。

## 建议提问

1. 追踪 `OrderController.createOrder` 到 `InventoryRepository.findAvailableStock` 的静态调用路径。
2. 为什么订单创建过程可能在库存预留阶段出现 `NullPointerException`？
3. 订单最终价格为什么可能与业务预期不符？哪些规则仍需确认？
4. 追踪订单创建过程中的支付调用链。

静态路径只代表已解析的源码调用关系，不证明某次运行实际执行；没有业务需求文档时，不应把计价推断当作既定规则。
