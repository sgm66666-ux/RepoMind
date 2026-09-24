# RepoMind 真实 Ollama Agent Scenario Benchmark

生成时间：2026-09-24T00:26:13+08:00。FastAPI Agent API：`http://127.0.0.1:19002`；模型：`qwen2.5-coder:14b`。

说明：8 个基线场景及代表场景的重复运行均调用真实 API；期望仅用于事后评估，未注入 Prompt。
配置场景当前工具链不支持 YAML/properties 读取及关联，UNSUPPORTED 不是成功定位。

## 总体

基线场景 8；实际 Agent 调用 20；Planner 通过 8；Evidence Grounding 通过 4；有效 FinalDiagnosis 4；Ollama/格式错误 0。

任务类型：{"RUNTIME_ERROR": 2, "BUSINESS_LOGIC_ERROR": 2, "CALL_CHAIN_ANALYSIS": 2, "CONFIGURATION_ERROR": 2}。
状态：{"PARTIAL": 4, "FAIL": 4}。

## 逐场景真实结果

### runtime-inventory-npe · baseline #1 · PARTIAL

- 问题：为什么InventoryService.checkStock出现NullPointerException？
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["checkStock"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → findCallers → readFile → findCallees → readFile → readFile`
- 工具族：期望 `searchSymbol, findCallees, readFile`；覆盖。
- 证据：[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": false}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "NullPointerException in InventoryService.checkStock due to null return from InventoryRepository.findStock", "location": {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock"}, "root_cause": "InventoryRepository.findStock returns null, which is then dereferenced in InventoryService.checkStock", "evidence": [{"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}], "call_chain": [], "fix_suggestion": "Ensure InventoryRepository.findStock does not return null or handle null appropriately in InventoryService.checkStock", "uncertainty": "The exact cause of null in InventoryRepository.findStock is not determined from the provided code.", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 InventoryRepository.java:4 与 Observation 不符，已按源码修正为 5", "调用链含有未观察到的已解析关系"]
- 诊断状态：`VALID`；用户提示：无。
- 错误：无。备注：Java 空值来源与解引用；不能只凭调用断言。

### runtime-python-login · baseline #1 · FAIL

- 问题：为什么UserService.login出现TypeError异常？请检查返回值来源。
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["login"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol`
- 工具族：期望 `searchSymbol, findCallees, readFile`；未覆盖。
- 证据：[{"file": "repository.py", "code": "return None", "in_trace": false, "in_diagnosis": false}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": false, "in_diagnosis": false}]
- FinalDiagnosis：null
- 不支持/校验问题：[]
- 诊断状态：`NOT_COMPLETED`；用户提示：已达到工具调用步数上限，尚无最终诊断。。
- 错误：无。备注：Python 空值返回与下标访问。

### business-price · baseline #1 · PARTIAL

- 问题：为什么订单价格计算错误？
- Planner：期望 `BUSINESS_LOGIC_ERROR`；实际 `BUSINESS_LOGIC_ERROR`；通过。
- Plan：`{"task_type": "BUSINESS_LOGIC_ERROR", "analysis_goal": "检查目标业务计算及其输入来源、调用方和返回值影响", "target_keywords": ["calculatePrice", "price"], "target_source": "HEURISTIC", "required_evidence": ["target_method_source", "caller_context", "input_origin", "return_value_impact"], "preferred_tools": ["searchSymbol", "findCallers", "readFile"], "stop_condition": "核对目标实现、输入来源与调用方源码后给出有证据的诊断；否则明确证据不足"}`
- Tool Trace：`searchSymbol → findCallers → readFile → readFile`
- 工具族：期望 `searchSymbol, findCallers, readFile`；覆盖。
- 证据：[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 3}, {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则"]
- 诊断状态：`VALID`；用户提示：无。
- 错误：无。备注：正确计价规则未在源码中给出。

### business-order-return · baseline #1 · PARTIAL

- 问题：为什么OrderService.createOrder返回的订单价格不符合预期？
- Planner：期望 `BUSINESS_LOGIC_ERROR`；实际 `BUSINESS_LOGIC_ERROR`；通过。
- Plan：`{"task_type": "BUSINESS_LOGIC_ERROR", "analysis_goal": "检查目标业务计算及其输入来源、调用方和返回值影响", "target_keywords": ["createOrder"], "target_source": "QUERY", "required_evidence": ["target_method_source", "caller_context", "input_origin", "return_value_impact"], "preferred_tools": ["searchSymbol", "findCallers", "readFile"], "stop_condition": "核对目标实现、输入来源与调用方源码后给出有证据的诊断；否则明确证据不足"}`
- Tool Trace：`searchSymbol → findCallers → readFile → searchSymbol → findCallers → readFile`
- 工具族：期望 `searchSymbol, findCallees, readFile`；未覆盖。
- 证据：[{"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}, {"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 3}, {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则"]
- 诊断状态：`VALID`；用户提示：无。
- 错误：无。备注：需同时看调用方与计算方法。

### callchain-registration · baseline #1 · FAIL

- 问题：追踪UserService.register到ConfigRepository.getTemplate的调用路径。
- Planner：期望 `CALL_CHAIN_ANALYSIS`；实际 `CALL_CHAIN_ANALYSIS`；通过。
- Plan：`{"task_type": "CALL_CHAIN_ANALYSIS", "analysis_goal": "追踪目标 Symbol 的真实调用路径", "target_keywords": ["register", "getTemplate"], "target_source": "QUERY", "required_evidence": ["target_symbol", "caller_context", "callee_context"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees"], "stop_condition": "获得足够的已解析调用关系来回答路径；未解析边需标明不确定"}`
- Tool Trace：`searchSymbol → findCallers → searchSymbol → findCallees → findCallers → findCallees → findCallers → findCallees`
- 工具族：期望 `searchSymbol, findCallees`；覆盖。
- 证据：[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": false, "in_diagnosis": false}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": false, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": false, "in_diagnosis": false}]
- FinalDiagnosis：null
- 不支持/校验问题：[]
- 诊断状态：`NOT_COMPLETED`；用户提示：已达到工具调用步数上限，尚无最终诊断。。
- 错误：无。备注：需核对全部已解析 CALLS 边。

### callchain-order-stock · baseline #1 · PARTIAL

- 问题：追踪OrderController.createOrder到InventoryRepository.findStock的调用路径。
- Planner：期望 `CALL_CHAIN_ANALYSIS`；实际 `CALL_CHAIN_ANALYSIS`；通过。
- Plan：`{"task_type": "CALL_CHAIN_ANALYSIS", "analysis_goal": "追踪目标 Symbol 的真实调用路径", "target_keywords": ["createOrder", "findStock"], "target_source": "QUERY", "required_evidence": ["target_symbol", "caller_context", "callee_context"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees"], "stop_condition": "获得足够的已解析调用关系来回答路径；未解析边需标明不确定"}`
- Tool Trace：`searchSymbol → findCallers → findCallees → findCallees → findCallees`
- 工具族：期望 `searchSymbol, findCallees`；覆盖。
- 证据：[{"file": "OrderController.java", "code": "orderService.createOrder();", "in_trace": false, "in_diagnosis": false}, {"file": "OrderService.java", "code": "inventoryService.checkStock();", "in_trace": false, "in_diagnosis": false}, {"file": "InventoryService.java", "code": "inventoryRepository.findStock();", "in_trace": false, "in_diagnosis": false}]
- FinalDiagnosis：{"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "追踪OrderController.createOrder到InventoryRepository.findStock的调用路径", "location": {"file": null, "line": null, "symbol": null}, "root_cause": "调用路径已成功追踪", "evidence": [{"file": "OrderDemoApplication.java", "line": 9, "symbol": "demo.order.OrderDemoApplication.main", "code": "controller.createOrder()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 2}, {"file": "OrderController.java", "line": 11, "symbol": "demo.order.OrderController.createOrder", "code": "orderService.createOrder()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 3}, {"file": "OrderService.java", "line": 11, "symbol": "demo.order.OrderService.createOrder", "code": "inventoryService.checkStock()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 4}, {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "inventoryRepository.findStock()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 5}], "call_chain": [], "fix_suggestion": "", "uncertainty": "", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["定位文件未见于 Observation", "定位 Symbol 未见于 Observation", "定位行号未见于源码或已解析调用 Observation", "调用链含有未观察到的已解析关系"]
- 诊断状态：`VALID`；用户提示：无。
- 错误：无。备注：需核对全部已解析 CALLS 边。

### config-database-url · baseline #1 · FAIL

- 问题：为什么数据库URL配置缺失导致连接失败？请核对application.yml与代码使用位置。
- Planner：期望 `CONFIGURATION_ERROR`；实际 `CONFIGURATION_ERROR`；通过。
- Plan：`{"task_type": "CONFIGURATION_ERROR", "analysis_goal": "定位配置读取位置与缺失或错误的配置来源", "target_keywords": [], "target_source": "UNSPECIFIED", "required_evidence": ["configuration_reference", "target_method_source", "caller_context"], "preferred_tools": ["searchSymbol", "findReferences", "findCallers", "readFile"], "stop_condition": "找到配置使用位置及相关源码证据；否则明确配置状态无法从代码确认"}`
- Tool Trace：`searchSymbol → searchSymbol → searchSymbol → findCallers → searchSymbol → findCallers → searchSymbol → findCallers`
- 工具族：期望 `searchSymbol, readFile`；未覆盖。
- 证据：[]
- FinalDiagnosis：null
- 不支持/校验问题：[]
- 诊断状态：`NOT_COMPLETED`；用户提示：已达到工具调用步数上限，尚无最终诊断。。
- 错误：无。备注：当前 Scanner/CodeReader 不支持 YAML；应明确能力不足。

### config-database-username · baseline #1 · FAIL

- 问题：为什么application.yml中的database.username配置没有生效？
- Planner：期望 `CONFIGURATION_ERROR`；实际 `CONFIGURATION_ERROR`；通过。
- Plan：`{"task_type": "CONFIGURATION_ERROR", "analysis_goal": "定位配置读取位置与缺失或错误的配置来源", "target_keywords": [], "target_source": "UNSPECIFIED", "required_evidence": ["configuration_reference", "target_method_source", "caller_context"], "preferred_tools": ["searchSymbol", "findReferences", "findCallers", "readFile"], "stop_condition": "找到配置使用位置及相关源码证据；否则明确配置状态无法从代码确认"}`
- Tool Trace：`searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → findCallers → searchSymbol`
- 工具族：期望 `searchSymbol, readFile`；未覆盖。
- 证据：[]
- FinalDiagnosis：null
- 不支持/校验问题：[]
- 诊断状态：`NOT_COMPLETED`；用户提示：已达到工具调用步数上限，尚无最终诊断。。
- 错误：无。备注：当前工具链无法证明 YAML 值与使用位置。

### runtime-inventory-npe · repeat #1 · PARTIAL

- 问题：为什么InventoryService.checkStock出现NullPointerException？
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["checkStock"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → findCallers → readFile → findCallees → readFile → readFile`
- 工具族：期望 `searchSymbol, findCallees, readFile`；覆盖。
- 证据：[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": false}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "NullPointerException in InventoryService.checkStock due to null return from InventoryRepository.findStock", "location": {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock"}, "root_cause": "InventoryRepository.findStock returns null, which is then dereferenced in InventoryService.checkStock", "evidence": [{"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}], "call_chain": [], "fix_suggestion": "Ensure InventoryRepository.findStock does not return null or handle null appropriately in InventoryService.checkStock", "uncertainty": "The exact cause of null in InventoryRepository.findStock is not determined from the provided code.", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 InventoryRepository.java:4 与 Observation 不符，已按源码修正为 5", "调用链含有未观察到的已解析关系"]
- 诊断状态：`VALID`；用户提示：无。
- 错误：无。备注：Java 空值来源与解引用；不能只凭调用断言。

### runtime-inventory-npe · repeat #2 · PARTIAL

- 问题：为什么InventoryService.checkStock出现NullPointerException？
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["checkStock"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → findCallers → readFile → findCallees → readFile → readFile`
- 工具族：期望 `searchSymbol, findCallees, readFile`；覆盖。
- 证据：[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": false}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "NullPointerException in InventoryService.checkStock due to null return from InventoryRepository.findStock", "location": {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock"}, "root_cause": "InventoryRepository.findStock returns null, which is then dereferenced in InventoryService.checkStock", "evidence": [{"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}], "call_chain": [], "fix_suggestion": "Ensure InventoryRepository.findStock does not return null or handle null appropriately in InventoryService.checkStock", "uncertainty": "The exact cause of null in InventoryRepository.findStock is not determined from the provided code.", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 InventoryRepository.java:4 与 Observation 不符，已按源码修正为 5", "调用链含有未观察到的已解析关系"]
- 诊断状态：`VALID`；用户提示：无。
- 错误：无。备注：Java 空值来源与解引用；不能只凭调用断言。

### runtime-inventory-npe · repeat #3 · PARTIAL

- 问题：为什么InventoryService.checkStock出现NullPointerException？
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["checkStock"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → findCallers → readFile → findCallees → readFile → readFile`
- 工具族：期望 `searchSymbol, findCallees, readFile`；覆盖。
- 证据：[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": false}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "NullPointerException in InventoryService.checkStock due to null return from InventoryRepository.findStock", "location": {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock"}, "root_cause": "InventoryRepository.findStock returns null, which is then dereferenced in InventoryService.checkStock", "evidence": [{"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}], "call_chain": [], "fix_suggestion": "Ensure InventoryRepository.findStock does not return null or handle null appropriately in InventoryService.checkStock", "uncertainty": "The exact cause of null in InventoryRepository.findStock is not determined from the provided code.", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 InventoryRepository.java:4 与 Observation 不符，已按源码修正为 5", "调用链含有未观察到的已解析关系"]
- 诊断状态：`VALID`；用户提示：无。
- 错误：无。备注：Java 空值来源与解引用；不能只凭调用断言。

### business-price · repeat #1 · PARTIAL

- 问题：为什么订单价格计算错误？
- Planner：期望 `BUSINESS_LOGIC_ERROR`；实际 `BUSINESS_LOGIC_ERROR`；通过。
- Plan：`{"task_type": "BUSINESS_LOGIC_ERROR", "analysis_goal": "检查目标业务计算及其输入来源、调用方和返回值影响", "target_keywords": ["calculatePrice", "price"], "target_source": "HEURISTIC", "required_evidence": ["target_method_source", "caller_context", "input_origin", "return_value_impact"], "preferred_tools": ["searchSymbol", "findCallers", "readFile"], "stop_condition": "核对目标实现、输入来源与调用方源码后给出有证据的诊断；否则明确证据不足"}`
- Tool Trace：`searchSymbol → findCallers → readFile → readFile`
- 工具族：期望 `searchSymbol, findCallers, readFile`；覆盖。
- 证据：[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 3}, {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则"]
- 诊断状态：`VALID`；用户提示：无。
- 错误：无。备注：正确计价规则未在源码中给出。

### business-price · repeat #2 · PARTIAL

- 问题：为什么订单价格计算错误？
- Planner：期望 `BUSINESS_LOGIC_ERROR`；实际 `BUSINESS_LOGIC_ERROR`；通过。
- Plan：`{"task_type": "BUSINESS_LOGIC_ERROR", "analysis_goal": "检查目标业务计算及其输入来源、调用方和返回值影响", "target_keywords": ["calculatePrice", "price"], "target_source": "HEURISTIC", "required_evidence": ["target_method_source", "caller_context", "input_origin", "return_value_impact"], "preferred_tools": ["searchSymbol", "findCallers", "readFile"], "stop_condition": "核对目标实现、输入来源与调用方源码后给出有证据的诊断；否则明确证据不足"}`
- Tool Trace：`searchSymbol → findCallers → readFile → readFile`
- 工具族：期望 `searchSymbol, findCallers, readFile`；覆盖。
- 证据：[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 3}, {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则"]
- 诊断状态：`VALID`；用户提示：无。
- 错误：无。备注：正确计价规则未在源码中给出。

### business-price · repeat #3 · PARTIAL

- 问题：为什么订单价格计算错误？
- Planner：期望 `BUSINESS_LOGIC_ERROR`；实际 `BUSINESS_LOGIC_ERROR`；通过。
- Plan：`{"task_type": "BUSINESS_LOGIC_ERROR", "analysis_goal": "检查目标业务计算及其输入来源、调用方和返回值影响", "target_keywords": ["calculatePrice", "price"], "target_source": "HEURISTIC", "required_evidence": ["target_method_source", "caller_context", "input_origin", "return_value_impact"], "preferred_tools": ["searchSymbol", "findCallers", "readFile"], "stop_condition": "核对目标实现、输入来源与调用方源码后给出有证据的诊断；否则明确证据不足"}`
- Tool Trace：`searchSymbol → findCallers → readFile → readFile`
- 工具族：期望 `searchSymbol, findCallers, readFile`；覆盖。
- 证据：[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 3}, {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则"]
- 诊断状态：`VALID`；用户提示：无。
- 错误：无。备注：正确计价规则未在源码中给出。

### callchain-registration · repeat #1 · FAIL

- 问题：追踪UserService.register到ConfigRepository.getTemplate的调用路径。
- Planner：期望 `CALL_CHAIN_ANALYSIS`；实际 `CALL_CHAIN_ANALYSIS`；通过。
- Plan：`{"task_type": "CALL_CHAIN_ANALYSIS", "analysis_goal": "追踪目标 Symbol 的真实调用路径", "target_keywords": ["register", "getTemplate"], "target_source": "QUERY", "required_evidence": ["target_symbol", "caller_context", "callee_context"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees"], "stop_condition": "获得足够的已解析调用关系来回答路径；未解析边需标明不确定"}`
- Tool Trace：`searchSymbol → findCallers → searchSymbol → findCallees → findCallers → findCallees → findCallers → findCallees`
- 工具族：期望 `searchSymbol, findCallees`；覆盖。
- 证据：[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": false, "in_diagnosis": false}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": false, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": false, "in_diagnosis": false}]
- FinalDiagnosis：null
- 不支持/校验问题：[]
- 诊断状态：`NOT_COMPLETED`；用户提示：已达到工具调用步数上限，尚无最终诊断。。
- 错误：无。备注：需核对全部已解析 CALLS 边。

### callchain-registration · repeat #2 · FAIL

- 问题：追踪UserService.register到ConfigRepository.getTemplate的调用路径。
- Planner：期望 `CALL_CHAIN_ANALYSIS`；实际 `CALL_CHAIN_ANALYSIS`；通过。
- Plan：`{"task_type": "CALL_CHAIN_ANALYSIS", "analysis_goal": "追踪目标 Symbol 的真实调用路径", "target_keywords": ["register", "getTemplate"], "target_source": "QUERY", "required_evidence": ["target_symbol", "caller_context", "callee_context"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees"], "stop_condition": "获得足够的已解析调用关系来回答路径；未解析边需标明不确定"}`
- Tool Trace：`searchSymbol → findCallers → searchSymbol → findCallees → findCallers → findCallees → findCallers → findCallees`
- 工具族：期望 `searchSymbol, findCallees`；覆盖。
- 证据：[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": false, "in_diagnosis": false}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": false, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": false, "in_diagnosis": false}]
- FinalDiagnosis：null
- 不支持/校验问题：[]
- 诊断状态：`NOT_COMPLETED`；用户提示：已达到工具调用步数上限，尚无最终诊断。。
- 错误：无。备注：需核对全部已解析 CALLS 边。

### callchain-registration · repeat #3 · FAIL

- 问题：追踪UserService.register到ConfigRepository.getTemplate的调用路径。
- Planner：期望 `CALL_CHAIN_ANALYSIS`；实际 `CALL_CHAIN_ANALYSIS`；通过。
- Plan：`{"task_type": "CALL_CHAIN_ANALYSIS", "analysis_goal": "追踪目标 Symbol 的真实调用路径", "target_keywords": ["register", "getTemplate"], "target_source": "QUERY", "required_evidence": ["target_symbol", "caller_context", "callee_context"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees"], "stop_condition": "获得足够的已解析调用关系来回答路径；未解析边需标明不确定"}`
- Tool Trace：`searchSymbol → findCallers → searchSymbol → findCallees → findCallers → findCallees → findCallers → findCallees`
- 工具族：期望 `searchSymbol, findCallees`；覆盖。
- 证据：[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": false, "in_diagnosis": false}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": false, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": false, "in_diagnosis": false}]
- FinalDiagnosis：null
- 不支持/校验问题：[]
- 诊断状态：`NOT_COMPLETED`；用户提示：已达到工具调用步数上限，尚无最终诊断。。
- 错误：无。备注：需核对全部已解析 CALLS 边。

### runtime-python-login · repeat #1 · FAIL

- 问题：为什么UserService.login出现TypeError异常？请检查返回值来源。
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["login"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol`
- 工具族：期望 `searchSymbol, findCallees, readFile`；未覆盖。
- 证据：[{"file": "repository.py", "code": "return None", "in_trace": false, "in_diagnosis": false}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": false, "in_diagnosis": false}]
- FinalDiagnosis：null
- 不支持/校验问题：[]
- 诊断状态：`NOT_COMPLETED`；用户提示：已达到工具调用步数上限，尚无最终诊断。。
- 错误：无。备注：Python 空值返回与下标访问。

### runtime-python-login · repeat #2 · FAIL

- 问题：为什么UserService.login出现TypeError异常？请检查返回值来源。
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["login"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol`
- 工具族：期望 `searchSymbol, findCallees, readFile`；未覆盖。
- 证据：[{"file": "repository.py", "code": "return None", "in_trace": false, "in_diagnosis": false}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": false, "in_diagnosis": false}]
- FinalDiagnosis：null
- 不支持/校验问题：[]
- 诊断状态：`NOT_COMPLETED`；用户提示：已达到工具调用步数上限，尚无最终诊断。。
- 错误：无。备注：Python 空值返回与下标访问。

### runtime-python-login · repeat #3 · FAIL

- 问题：为什么UserService.login出现TypeError异常？请检查返回值来源。
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["login"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol → searchSymbol`
- 工具族：期望 `searchSymbol, findCallees, readFile`；未覆盖。
- 证据：[{"file": "repository.py", "code": "return None", "in_trace": false, "in_diagnosis": false}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": false, "in_diagnosis": false}]
- FinalDiagnosis：null
- 不支持/校验问题：[]
- 诊断状态：`NOT_COMPLETED`；用户提示：已达到工具调用步数上限，尚无最终诊断。。
- 错误：无。备注：Python 空值返回与下标访问。
