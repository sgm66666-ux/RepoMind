"""Read-only benchmark expectations; none of these fields are sent to the Agent prompt."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectedEvidence:
    file: str
    code: str


@dataclass(frozen=True)
class AgentScenario:
    id: str
    task_type_expected: str
    repository_path: str
    user_query: str
    expected_target: str
    expected_evidence: tuple[ExpectedEvidence, ...]
    expected_tool_family: tuple[str, ...]
    expected_call_chain: tuple[str, ...]
    forbidden_conclusions: tuple[str, ...]
    notes: str


SCENARIOS = (
    AgentScenario("runtime-inventory-npe", "RUNTIME_ERROR", "demo/order-demo",
                  "为什么InventoryService.checkStock出现NullPointerException？",
                  "InventoryService.checkStock",
                  (ExpectedEvidence("InventoryRepository.java", "return null;"),
                   ExpectedEvidence("InventoryService.java", "if (stock.available) {")),
                  ("searchSymbol", "findCallees", "readFile"), (),
                  ("必然在生产环境复现",), "Java 空值来源与解引用；不能只凭调用断言。"),
    AgentScenario("runtime-python-login", "RUNTIME_ERROR", "demo/repomind-agent-test-demo/python-bug-demo",
                  "为什么UserService.login出现TypeError异常？请检查返回值来源。",
                  "UserService.login",
                  (ExpectedEvidence("repository.py", "return None"),
                   ExpectedEvidence("service.py", 'return user["name"]')),
                  ("searchSymbol", "findCallees", "readFile"), (),
                  ("一定是 IndexError",), "Python 空值返回与下标访问。"),
    AgentScenario("business-price", "BUSINESS_LOGIC_ERROR", "demo/repomind-agent-test-demo/logic-bug-demo",
                  "为什么订单价格计算错误？", "PriceService.calculatePrice",
                  (ExpectedEvidence("src/PriceService.java", "return price + quantity * discount;"),
                   ExpectedEvidence("src/OrderService.java", "return priceService.calculatePrice(100, 3);")),
                  ("searchSymbol", "findCallers", "readFile"),
                  ("OrderService.createOrder", "PriceService.calculatePrice"),
                  ("正确公式一定是", "应该是price * quantity * discount"), "正确计价规则未在源码中给出。"),
    AgentScenario("business-order-return", "BUSINESS_LOGIC_ERROR", "demo/repomind-agent-test-demo/logic-bug-demo",
                  "为什么OrderService.createOrder返回的订单价格不符合预期？",
                  "OrderService.createOrder",
                  (ExpectedEvidence("src/OrderService.java", "return priceService.calculatePrice(100, 3);"),
                   ExpectedEvidence("src/PriceService.java", "return price + quantity * discount;")),
                  ("searchSymbol", "findCallees", "readFile"),
                  ("OrderService.createOrder", "PriceService.calculatePrice"),
                  ("正确公式一定是", "应该是price * quantity * discount"), "需同时看调用方与计算方法。"),
    AgentScenario("callchain-registration", "CALL_CHAIN_ANALYSIS", "demo/repomind-agent-test-demo/call-chain-demo",
                  "追踪UserService.register到ConfigRepository.getTemplate的调用路径。",
                  "UserService.register",
                  (ExpectedEvidence("src/UserService.java", "emailService.sendEmail(email);"),
                   ExpectedEvidence("src/EmailService.java", "templateService.render();"),
                   ExpectedEvidence("src/TemplateService.java", "repository.getTemplate();")),
                  ("searchSymbol", "findCallees"),
                  ("UserService.register", "EmailService.sendEmail", "TemplateService.render",
                   "ConfigRepository.getTemplate"),
                  ("根据文件名推断",), "需核对全部已解析 CALLS 边。"),
    AgentScenario("callchain-order-stock", "CALL_CHAIN_ANALYSIS", "demo/order-demo",
                  "追踪OrderController.createOrder到InventoryRepository.findStock的调用路径。",
                  "OrderController.createOrder",
                  (ExpectedEvidence("OrderController.java", "orderService.createOrder();"),
                   ExpectedEvidence("OrderService.java", "inventoryService.checkStock();"),
                   ExpectedEvidence("InventoryService.java", "inventoryRepository.findStock();")),
                  ("searchSymbol", "findCallees"),
                  ("OrderController.createOrder", "OrderService.createOrder",
                   "InventoryService.checkStock", "InventoryRepository.findStock"),
                  ("根据文件名推断",), "需核对全部已解析 CALLS 边。"),
    AgentScenario("config-database-url", "CONFIGURATION_ERROR", "demo/repomind-agent-test-demo/config-demo",
                  "为什么数据库URL配置缺失导致连接失败？请核对application.yml与代码使用位置。",
                  "DatabaseService.connect", (), ("searchSymbol", "readFile"), (),
                  ("已证实部署环境URL为空", "配置值一定为空"),
                  "当前 Scanner/CodeReader 不支持 YAML；应明确能力不足。"),
    AgentScenario("config-database-username", "CONFIGURATION_ERROR", "demo/repomind-agent-test-demo/config-demo",
                  "为什么application.yml中的database.username配置没有生效？",
                  "database.username", (), ("searchSymbol", "readFile"), (),
                  ("已证实部署环境用户名为空", "配置值一定为空"),
                  "当前工具链无法证明 YAML 值与使用位置。"),
)

REPETITION_IDS = ("runtime-inventory-npe", "business-price", "callchain-registration", "runtime-python-login")
