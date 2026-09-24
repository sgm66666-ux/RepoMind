# RepoMind 真实 Ollama Agent Scenario Benchmark

生成时间：2026-09-24T11:30:01+08:00。FastAPI Agent API：`http://127.0.0.1:19002`；模型：`qwen2.5-coder:14b`。

说明：8 个基线场景及代表场景的重复运行均调用真实 API；期望仅用于事后评估，未注入 Prompt。
配置场景当前工具链不支持 YAML/properties 读取及关联，UNSUPPORTED 不是成功定位。

## 总体

基线场景 8；实际 Agent 调用 20；Planner 通过 8；Evidence Grounding 通过 6；有效 FinalDiagnosis 6；Ollama/格式错误 0。

任务类型：{"RUNTIME_ERROR": 2, "BUSINESS_LOGIC_ERROR": 2, "CALL_CHAIN_ANALYSIS": 2, "CONFIGURATION_ERROR": 2}。
状态：{"PARTIAL": 6, "UNSUPPORTED": 2}。

## 逐场景真实结果

### runtime-inventory-npe · baseline #1 · PARTIAL

- 问题：为什么InventoryService.checkStock出现NullPointerException？
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["checkStock"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → readFile → findCallers → readFile → searchSymbol → readFile`
- 目标 Symbol：`InventoryService.checkStock`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees, readFile`；未覆盖。
- 证据：[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "NullPointerException in InventoryService.checkStock due to null return from InventoryRepository.findStock", "location": {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock"}, "root_cause": "InventoryRepository.findStock returns null, which causes NullPointerException when accessed in InventoryService.checkStock", "evidence": [{"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock", "code": "if (stock.available) {", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}], "call_chain": ["demo.order.OrderService.createOrder", "demo.order.InventoryService.checkStock"], "fix_suggestion": "Ensure InventoryRepository.findStock returns a valid Inventory object instead of null", "uncertainty": "None 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 3 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：Java 空值来源与解引用；不能只凭调用断言。

### runtime-python-login · baseline #1 · PARTIAL

- 问题：为什么UserService.login出现TypeError异常？请检查返回值来源。
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["login"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → searchSymbol → searchSymbol → readFile → searchSymbol → readFile → findCallers → findCallees`
- 目标 Symbol：`UserService.login`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees, readFile`；覆盖。
- 证据：[{"file": "repository.py", "code": "return None", "in_trace": true, "in_diagnosis": true}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "UserService.login出现TypeError异常，因为get_user返回None，尝试访问None的'\"name\"'属性。", "location": {"file": "service.py", "line": 12, "symbol": "service.UserService.login"}, "root_cause": "get_user方法返回None，导致在访问user['name']时引发TypeError。", "evidence": [{"file": "repository.py", "line": 4, "symbol": "repository.UserRepository.get_user", "code": "return None", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "service.py", "line": 10, "symbol": "service.UserService.login", "code": "user = self.repo.get_user(user_id)", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}, {"file": "service.py", "line": 12, "symbol": "service.UserService.login", "code": "return user[\"name\"]", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": [], "fix_suggestion": "检查get_user方法的实现，确保它返回一个有效的用户对象，而不是None。", "uncertainty": "get_user方法的实现细节未完全观察到，可能存在其他导致返回None的原因。 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["证据未见于成功 Observation：service.py:10", "调用链含有未观察到的已解析关系；仅保留已核验前缀", "CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 2 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置", "EVIDENCE_NOT_FOUND: 模型原稿包含无法核验的源码", "CALL_EDGE_NOT_VERIFIED: 模型原稿包含无法核验的调用边"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：Python 空值返回与下标访问。

### business-price · baseline #1 · PARTIAL

- 问题：为什么订单价格计算错误？
- Planner：期望 `BUSINESS_LOGIC_ERROR`；实际 `BUSINESS_LOGIC_ERROR`；通过。
- Plan：`{"task_type": "BUSINESS_LOGIC_ERROR", "analysis_goal": "检查目标业务计算及其输入来源、调用方和返回值影响", "target_keywords": ["calculatePrice", "price"], "target_source": "HEURISTIC", "required_evidence": ["target_method_source", "caller_context", "input_origin", "return_value_impact"], "preferred_tools": ["searchSymbol", "findCallers", "readFile"], "stop_condition": "核对目标实现、输入来源与调用方源码后给出有证据的诊断；否则明确证据不足"}`
- Tool Trace：`searchSymbol → readFile → findCallers → readFile`
- 目标 Symbol：`PriceService.calculatePrice`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallers, readFile`；覆盖。
- 证据：[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则", "EVIDENCE_PROJECTED_FROM_TOOL: 1 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正", "UNSUPPORTED_CLAIM_REMOVED: 无需求证据的公式断言已移除"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：正确计价规则未在源码中给出。

### business-order-return · baseline #1 · PARTIAL

- 问题：为什么OrderService.createOrder返回的订单价格不符合预期？
- Planner：期望 `BUSINESS_LOGIC_ERROR`；实际 `BUSINESS_LOGIC_ERROR`；通过。
- Plan：`{"task_type": "BUSINESS_LOGIC_ERROR", "analysis_goal": "检查目标业务计算及其输入来源、调用方和返回值影响", "target_keywords": ["createOrder"], "target_source": "QUERY", "required_evidence": ["target_method_source", "caller_context", "input_origin", "return_value_impact"], "preferred_tools": ["searchSymbol", "findCallers", "readFile"], "stop_condition": "核对目标实现、输入来源与调用方源码后给出有证据的诊断；否则明确证据不足"}`
- Tool Trace：`searchSymbol → readFile → findCallers → findCallees → readFile`
- 目标 Symbol：`OrderService.createOrder`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees, readFile`；覆盖。
- 证据：[{"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}, {"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正", "UNSUPPORTED_CLAIM_REMOVED: 无需求证据的公式断言已移除"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：需同时看调用方与计算方法。

### callchain-registration · baseline #1 · PARTIAL

- 问题：追踪UserService.register到ConfigRepository.getTemplate的调用路径。
- Planner：期望 `CALL_CHAIN_ANALYSIS`；实际 `CALL_CHAIN_ANALYSIS`；通过。
- Plan：`{"task_type": "CALL_CHAIN_ANALYSIS", "analysis_goal": "追踪目标 Symbol 的真实调用路径", "target_keywords": ["register", "getTemplate"], "target_source": "QUERY", "required_evidence": ["target_symbol", "caller_context", "callee_context"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees"], "stop_condition": "获得足够的已解析调用关系来回答路径；未解析边需标明不确定"}`
- Tool Trace：`searchSymbol → findCallees → findCallers → searchSymbol → findCallers → findCallees → readFile → readFile`
- 目标 Symbol：`UserService.register`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees`；覆盖。
- 证据：[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": true, "in_diagnosis": false}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": true, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": false, "in_diagnosis": false}]
- FinalDiagnosis：{"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "The call chain from UserService.register to ConfigRepository.getTemplate is incomplete.", "location": {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail"}, "root_cause": "The call chain stops at EmailService.sendEmail, and the next outgoing edge to ConfigRepository.getTemplate has not been verified.", "evidence": [{"file": "src/UserService.java", "line": 6, "symbol": "UserService.register", "code": "emailService.sendEmail(email)", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 2}, {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail", "code": "String content = templateService.render();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 8}], "call_chain": ["UserService.register", "EmailService.sendEmail"], "fix_suggestion": "Verify the call from EmailService.sendEmail to TemplateService.render and then from TemplateService.render to ConfigRepository.getTemplate.", "uncertainty": "The call chain is incomplete as it stops at EmailService.sendEmail. Further investigation is needed to verify the next outgoing edge.", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["CALL_EDGE_NOT_VERIFIED: 请求的完整路径缺少已解析边"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：需核对全部已解析 CALLS 边。

### callchain-order-stock · baseline #1 · PARTIAL

- 问题：追踪OrderController.createOrder到InventoryRepository.findStock的调用路径。
- Planner：期望 `CALL_CHAIN_ANALYSIS`；实际 `CALL_CHAIN_ANALYSIS`；通过。
- Plan：`{"task_type": "CALL_CHAIN_ANALYSIS", "analysis_goal": "追踪目标 Symbol 的真实调用路径", "target_keywords": ["createOrder", "findStock"], "target_source": "QUERY", "required_evidence": ["target_symbol", "caller_context", "callee_context"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees"], "stop_condition": "获得足够的已解析调用关系来回答路径；未解析边需标明不确定"}`
- Tool Trace：`searchSymbol → findCallees → findCallees → findCallees → readFile → readFile → readFile → readFile`
- 目标 Symbol：`OrderController.createOrder`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees`；覆盖。
- 证据：[{"file": "OrderController.java", "code": "orderService.createOrder();", "in_trace": true, "in_diagnosis": true}, {"file": "OrderService.java", "code": "inventoryService.checkStock();", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "inventoryRepository.findStock();", "in_trace": true, "in_diagnosis": false}]
- FinalDiagnosis：{"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "Traced the call chain from OrderController.createOrder to InventoryRepository.findStock.", "location": {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock"}, "root_cause": "The call chain from OrderController.createOrder to InventoryRepository.findStock is complete and verified.", "evidence": [{"file": "OrderController.java", "line": 11, "symbol": "demo.order.OrderController.createOrder", "code": "orderService.createOrder()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 2}, {"file": "OrderService.java", "line": 11, "symbol": "demo.order.OrderService.createOrder", "code": "inventoryService.checkStock()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 3}, {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "inventoryRepository.findStock()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 4}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 8}, {"file": "OrderController.java", "line": 11, "symbol": "demo.order.OrderController.createOrder", "code": "orderService.createOrder();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}, {"file": "OrderService.java", "line": 11, "symbol": "demo.order.OrderService.createOrder", "code": "inventoryService.checkStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 7}], "call_chain": ["OrderController.createOrder", "OrderService.createOrder", "InventoryService.checkStock", "InventoryRepository.findStock"], "fix_suggestion": "Ensure that InventoryRepository.findStock returns a valid Inventory object instead of null.", "uncertainty": "None", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 InventoryRepository.java:4 与 Observation 不符，已按源码修正为 5", "模型定位行号与源码证据不符，已按已核验代码行修正", "CALL_CHAIN_PROJECTED_FROM_VERIFIED_EDGES", "EVIDENCE_PROJECTED_FROM_TOOL: 3 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：需核对全部已解析 CALLS 边。

### config-database-url · baseline #1 · UNSUPPORTED

- 问题：为什么数据库URL配置缺失导致连接失败？请核对application.yml与代码使用位置。
- Planner：期望 `CONFIGURATION_ERROR`；实际 `CONFIGURATION_ERROR`；通过。
- Plan：`{"task_type": "CONFIGURATION_ERROR", "analysis_goal": "定位配置读取位置与缺失或错误的配置来源", "target_keywords": [], "target_source": "UNSPECIFIED", "required_evidence": ["configuration_reference", "target_method_source", "caller_context"], "preferred_tools": ["searchSymbol", "findReferences", "findCallers", "readFile"], "stop_condition": "找到配置使用位置及相关源码证据；否则明确配置状态无法从代码确认"}`
- Tool Trace：`无`
- 目标 Symbol：`DatabaseService.connect`；未由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, readFile`；未覆盖。
- 证据：[]
- FinalDiagnosis：null
- 不支持/校验问题：["当前 ToolRegistry 没有配置文件读取与关联能力"]
- Agent 状态：`UNSUPPORTED`；诊断状态：`UNSUPPORTED`；用户提示：当前工具链无法读取并关联配置文件与代码使用位置，暂不能确认配置故障原因。。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：当前 Scanner/CodeReader 不支持 YAML；应明确能力不足。

### config-database-username · baseline #1 · UNSUPPORTED

- 问题：为什么application.yml中的database.username配置没有生效？
- Planner：期望 `CONFIGURATION_ERROR`；实际 `CONFIGURATION_ERROR`；通过。
- Plan：`{"task_type": "CONFIGURATION_ERROR", "analysis_goal": "定位配置读取位置与缺失或错误的配置来源", "target_keywords": [], "target_source": "UNSPECIFIED", "required_evidence": ["configuration_reference", "target_method_source", "caller_context"], "preferred_tools": ["searchSymbol", "findReferences", "findCallers", "readFile"], "stop_condition": "找到配置使用位置及相关源码证据；否则明确配置状态无法从代码确认"}`
- Tool Trace：`无`
- 目标 Symbol：`database.username`；未由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, readFile`；未覆盖。
- 证据：[]
- FinalDiagnosis：null
- 不支持/校验问题：["当前 ToolRegistry 没有配置文件读取与关联能力"]
- Agent 状态：`UNSUPPORTED`；诊断状态：`UNSUPPORTED`；用户提示：当前工具链无法读取并关联配置文件与代码使用位置，暂不能确认配置故障原因。。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：当前工具链无法证明 YAML 值与使用位置。

### runtime-inventory-npe · repeat #1 · PARTIAL

- 问题：为什么InventoryService.checkStock出现NullPointerException？
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["checkStock"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → readFile → findCallers → readFile → searchSymbol → readFile`
- 目标 Symbol：`InventoryService.checkStock`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees, readFile`；未覆盖。
- 证据：[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "NullPointerException in InventoryService.checkStock due to null return from InventoryRepository.findStock", "location": {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock"}, "root_cause": "InventoryRepository.findStock returns null, which causes NullPointerException when accessed in InventoryService.checkStock", "evidence": [{"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock", "code": "if (stock.available) {", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}], "call_chain": ["demo.order.OrderService.createOrder", "demo.order.InventoryService.checkStock"], "fix_suggestion": "Ensure InventoryRepository.findStock returns a valid Inventory object instead of null", "uncertainty": "None 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 3 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：Java 空值来源与解引用；不能只凭调用断言。

### runtime-inventory-npe · repeat #2 · PARTIAL

- 问题：为什么InventoryService.checkStock出现NullPointerException？
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["checkStock"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → readFile → findCallers → readFile → searchSymbol → readFile`
- 目标 Symbol：`InventoryService.checkStock`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees, readFile`；未覆盖。
- 证据：[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "NullPointerException in InventoryService.checkStock due to null return from InventoryRepository.findStock", "location": {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock"}, "root_cause": "InventoryRepository.findStock returns null, which causes NullPointerException when accessed in InventoryService.checkStock", "evidence": [{"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock", "code": "if (stock.available) {", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}], "call_chain": ["demo.order.OrderService.createOrder", "demo.order.InventoryService.checkStock"], "fix_suggestion": "Ensure InventoryRepository.findStock returns a valid Inventory object instead of null", "uncertainty": "None 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 3 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：Java 空值来源与解引用；不能只凭调用断言。

### runtime-inventory-npe · repeat #3 · PARTIAL

- 问题：为什么InventoryService.checkStock出现NullPointerException？
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["checkStock"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → readFile → findCallers → readFile → searchSymbol → readFile`
- 目标 Symbol：`InventoryService.checkStock`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees, readFile`；未覆盖。
- 证据：[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "NullPointerException in InventoryService.checkStock due to null return from InventoryRepository.findStock", "location": {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock"}, "root_cause": "InventoryRepository.findStock returns null, which causes NullPointerException when accessed in InventoryService.checkStock", "evidence": [{"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock", "code": "if (stock.available) {", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}], "call_chain": ["demo.order.OrderService.createOrder", "demo.order.InventoryService.checkStock"], "fix_suggestion": "Ensure InventoryRepository.findStock returns a valid Inventory object instead of null", "uncertainty": "None 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 3 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：Java 空值来源与解引用；不能只凭调用断言。

### business-price · repeat #1 · PARTIAL

- 问题：为什么订单价格计算错误？
- Planner：期望 `BUSINESS_LOGIC_ERROR`；实际 `BUSINESS_LOGIC_ERROR`；通过。
- Plan：`{"task_type": "BUSINESS_LOGIC_ERROR", "analysis_goal": "检查目标业务计算及其输入来源、调用方和返回值影响", "target_keywords": ["calculatePrice", "price"], "target_source": "HEURISTIC", "required_evidence": ["target_method_source", "caller_context", "input_origin", "return_value_impact"], "preferred_tools": ["searchSymbol", "findCallers", "readFile"], "stop_condition": "核对目标实现、输入来源与调用方源码后给出有证据的诊断；否则明确证据不足"}`
- Tool Trace：`searchSymbol → readFile → findCallers → readFile`
- 目标 Symbol：`PriceService.calculatePrice`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallers, readFile`；覆盖。
- 证据：[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则", "EVIDENCE_PROJECTED_FROM_TOOL: 1 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正", "UNSUPPORTED_CLAIM_REMOVED: 无需求证据的公式断言已移除"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：正确计价规则未在源码中给出。

### business-price · repeat #2 · PARTIAL

- 问题：为什么订单价格计算错误？
- Planner：期望 `BUSINESS_LOGIC_ERROR`；实际 `BUSINESS_LOGIC_ERROR`；通过。
- Plan：`{"task_type": "BUSINESS_LOGIC_ERROR", "analysis_goal": "检查目标业务计算及其输入来源、调用方和返回值影响", "target_keywords": ["calculatePrice", "price"], "target_source": "HEURISTIC", "required_evidence": ["target_method_source", "caller_context", "input_origin", "return_value_impact"], "preferred_tools": ["searchSymbol", "findCallers", "readFile"], "stop_condition": "核对目标实现、输入来源与调用方源码后给出有证据的诊断；否则明确证据不足"}`
- Tool Trace：`searchSymbol → readFile → findCallers → readFile`
- 目标 Symbol：`PriceService.calculatePrice`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallers, readFile`；覆盖。
- 证据：[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则", "EVIDENCE_PROJECTED_FROM_TOOL: 1 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正", "UNSUPPORTED_CLAIM_REMOVED: 无需求证据的公式断言已移除"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：正确计价规则未在源码中给出。

### business-price · repeat #3 · PARTIAL

- 问题：为什么订单价格计算错误？
- Planner：期望 `BUSINESS_LOGIC_ERROR`；实际 `BUSINESS_LOGIC_ERROR`；通过。
- Plan：`{"task_type": "BUSINESS_LOGIC_ERROR", "analysis_goal": "检查目标业务计算及其输入来源、调用方和返回值影响", "target_keywords": ["calculatePrice", "price"], "target_source": "HEURISTIC", "required_evidence": ["target_method_source", "caller_context", "input_origin", "return_value_impact"], "preferred_tools": ["searchSymbol", "findCallers", "readFile"], "stop_condition": "核对目标实现、输入来源与调用方源码后给出有证据的诊断；否则明确证据不足"}`
- Tool Trace：`searchSymbol → readFile → findCallers → readFile`
- 目标 Symbol：`PriceService.calculatePrice`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallers, readFile`；覆盖。
- 证据：[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则", "EVIDENCE_PROJECTED_FROM_TOOL: 1 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正", "UNSUPPORTED_CLAIM_REMOVED: 无需求证据的公式断言已移除"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：正确计价规则未在源码中给出。

### callchain-registration · repeat #1 · PARTIAL

- 问题：追踪UserService.register到ConfigRepository.getTemplate的调用路径。
- Planner：期望 `CALL_CHAIN_ANALYSIS`；实际 `CALL_CHAIN_ANALYSIS`；通过。
- Plan：`{"task_type": "CALL_CHAIN_ANALYSIS", "analysis_goal": "追踪目标 Symbol 的真实调用路径", "target_keywords": ["register", "getTemplate"], "target_source": "QUERY", "required_evidence": ["target_symbol", "caller_context", "callee_context"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees"], "stop_condition": "获得足够的已解析调用关系来回答路径；未解析边需标明不确定"}`
- Tool Trace：`searchSymbol → findCallees → findCallees → findCallees → readFile → readFile → readFile → readFile`
- 目标 Symbol：`UserService.register`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees`；覆盖。
- 证据：[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": true, "in_diagnosis": true}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": true, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": true, "in_diagnosis": false}]
- FinalDiagnosis：{"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "Traced the call chain from UserService.register to ConfigRepository.getTemplate.", "location": {"file": "src/ConfigRepository.java", "line": 4, "symbol": "ConfigRepository.getTemplate"}, "root_cause": "The call chain from UserService.register to ConfigRepository.getTemplate is complete and verified.", "evidence": [{"file": "src/UserService.java", "line": 6, "symbol": "UserService.register", "code": "emailService.sendEmail(email)", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 2}, {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail", "code": "String content = templateService.render();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "src/TemplateService.java", "line": 6, "symbol": "TemplateService.render", "code": "String template = repository.getTemplate();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 7}, {"file": "src/ConfigRepository.java", "line": 4, "symbol": "ConfigRepository.getTemplate", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 8}, {"file": "src/UserService.java", "line": 6, "symbol": "UserService.register", "code": "emailService.sendEmail(email);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}], "call_chain": ["UserService.register", "EmailService.sendEmail", "TemplateService.render", "ConfigRepository.getTemplate"], "fix_suggestion": "Ensure that ConfigRepository.getTemplate returns a valid template string instead of null.", "uncertainty": "None", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/ConfigRepository.java:3 与 Observation 不符，已按源码修正为 4", "模型定位行号与源码证据不符，已按已核验代码行修正", "EVIDENCE_PROJECTED_FROM_TOOL: 1 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：需核对全部已解析 CALLS 边。

### callchain-registration · repeat #2 · PARTIAL

- 问题：追踪UserService.register到ConfigRepository.getTemplate的调用路径。
- Planner：期望 `CALL_CHAIN_ANALYSIS`；实际 `CALL_CHAIN_ANALYSIS`；通过。
- Plan：`{"task_type": "CALL_CHAIN_ANALYSIS", "analysis_goal": "追踪目标 Symbol 的真实调用路径", "target_keywords": ["register", "getTemplate"], "target_source": "QUERY", "required_evidence": ["target_symbol", "caller_context", "callee_context"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees"], "stop_condition": "获得足够的已解析调用关系来回答路径；未解析边需标明不确定"}`
- Tool Trace：`searchSymbol → findCallees → findCallees → findCallees → readFile → readFile → readFile → readFile`
- 目标 Symbol：`UserService.register`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees`；覆盖。
- 证据：[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": true, "in_diagnosis": true}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": true, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": true, "in_diagnosis": false}]
- FinalDiagnosis：{"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "Traced the call chain from UserService.register to ConfigRepository.getTemplate.", "location": {"file": "src/ConfigRepository.java", "line": 4, "symbol": "ConfigRepository.getTemplate"}, "root_cause": "The call chain from UserService.register to ConfigRepository.getTemplate is complete and verified.", "evidence": [{"file": "src/UserService.java", "line": 6, "symbol": "UserService.register", "code": "emailService.sendEmail(email)", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 2}, {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail", "code": "templateService.render()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 3}, {"file": "src/TemplateService.java", "line": 6, "symbol": "TemplateService.render", "code": "repository.getTemplate()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 4}, {"file": "src/ConfigRepository.java", "line": 4, "symbol": "ConfigRepository.getTemplate", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 8}, {"file": "src/UserService.java", "line": 6, "symbol": "UserService.register", "code": "emailService.sendEmail(email);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}, {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail", "code": "String content = templateService.render();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "src/TemplateService.java", "line": 6, "symbol": "TemplateService.render", "code": "String template = repository.getTemplate();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 7}], "call_chain": ["UserService.register", "EmailService.sendEmail", "TemplateService.render", "ConfigRepository.getTemplate"], "fix_suggestion": "Ensure that ConfigRepository.getTemplate returns a valid template string instead of null.", "uncertainty": "None", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/ConfigRepository.java:3 与 Observation 不符，已按源码修正为 4", "模型定位行号与源码证据不符，已按已核验代码行修正", "EVIDENCE_PROJECTED_FROM_TOOL: 3 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：需核对全部已解析 CALLS 边。

### callchain-registration · repeat #3 · PARTIAL

- 问题：追踪UserService.register到ConfigRepository.getTemplate的调用路径。
- Planner：期望 `CALL_CHAIN_ANALYSIS`；实际 `CALL_CHAIN_ANALYSIS`；通过。
- Plan：`{"task_type": "CALL_CHAIN_ANALYSIS", "analysis_goal": "追踪目标 Symbol 的真实调用路径", "target_keywords": ["register", "getTemplate"], "target_source": "QUERY", "required_evidence": ["target_symbol", "caller_context", "callee_context"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees"], "stop_condition": "获得足够的已解析调用关系来回答路径；未解析边需标明不确定"}`
- Tool Trace：`searchSymbol → findCallees → findCallees → findCallees → readFile → readFile → readFile → readFile`
- 目标 Symbol：`UserService.register`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees`；覆盖。
- 证据：[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": true, "in_diagnosis": true}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": true, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": true, "in_diagnosis": false}]
- FinalDiagnosis：{"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "Traced the call chain from UserService.register to ConfigRepository.getTemplate.", "location": {"file": "src/ConfigRepository.java", "line": 4, "symbol": "ConfigRepository.getTemplate"}, "root_cause": "The call chain from UserService.register to ConfigRepository.getTemplate is complete and verified.", "evidence": [{"file": "src/UserService.java", "line": 6, "symbol": "UserService.register", "code": "emailService.sendEmail(email)", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 2}, {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail", "code": "templateService.render()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 3}, {"file": "src/TemplateService.java", "line": 6, "symbol": "TemplateService.render", "code": "repository.getTemplate()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 4}, {"file": "src/ConfigRepository.java", "line": 4, "symbol": "ConfigRepository.getTemplate", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 8}, {"file": "src/UserService.java", "line": 6, "symbol": "UserService.register", "code": "emailService.sendEmail(email);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}, {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail", "code": "String content = templateService.render();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "src/TemplateService.java", "line": 6, "symbol": "TemplateService.render", "code": "String template = repository.getTemplate();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 7}], "call_chain": ["UserService.register", "EmailService.sendEmail", "TemplateService.render", "ConfigRepository.getTemplate"], "fix_suggestion": "Ensure that ConfigRepository.getTemplate returns a valid template string instead of null.", "uncertainty": "None", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["模型行号 src/ConfigRepository.java:3 与 Observation 不符，已按源码修正为 4", "模型定位行号与源码证据不符，已按已核验代码行修正", "EVIDENCE_PROJECTED_FROM_TOOL: 3 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：需核对全部已解析 CALLS 边。

### runtime-python-login · repeat #1 · PARTIAL

- 问题：为什么UserService.login出现TypeError异常？请检查返回值来源。
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["login"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → searchSymbol → searchSymbol → readFile → searchSymbol → readFile → findCallers → findCallees`
- 目标 Symbol：`UserService.login`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees, readFile`；覆盖。
- 证据：[{"file": "repository.py", "code": "return None", "in_trace": true, "in_diagnosis": true}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "UserService.login出现TypeError异常，因为get_user返回None，尝试访问None的'\"name\"'属性。", "location": {"file": "service.py", "line": 12, "symbol": "service.UserService.login"}, "root_cause": "get_user方法返回None，导致在访问user['name']时引发TypeError。", "evidence": [{"file": "repository.py", "line": 4, "symbol": "repository.UserRepository.get_user", "code": "return None", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "service.py", "line": 10, "symbol": "service.UserService.login", "code": "user = self.repo.get_user(user_id)", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}, {"file": "service.py", "line": 12, "symbol": "service.UserService.login", "code": "return user[\"name\"]", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": [], "fix_suggestion": "检查get_user方法的实现，确保它返回一个有效的用户对象，而不是None。", "uncertainty": "get_user方法的实现细节未完全观察到，可能存在其他导致返回None的原因。 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["证据未见于成功 Observation：service.py:10", "调用链含有未观察到的已解析关系；仅保留已核验前缀", "CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 2 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置", "EVIDENCE_NOT_FOUND: 模型原稿包含无法核验的源码", "CALL_EDGE_NOT_VERIFIED: 模型原稿包含无法核验的调用边"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：Python 空值返回与下标访问。

### runtime-python-login · repeat #2 · PARTIAL

- 问题：为什么UserService.login出现TypeError异常？请检查返回值来源。
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["login"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → searchSymbol → searchSymbol → readFile → searchSymbol → readFile → findCallers → findCallees`
- 目标 Symbol：`UserService.login`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees, readFile`；覆盖。
- 证据：[{"file": "repository.py", "code": "return None", "in_trace": true, "in_diagnosis": true}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "UserService.login出现TypeError异常，因为get_user返回None，尝试访问None的'\"name\"'属性。", "location": {"file": "service.py", "line": 12, "symbol": "service.UserService.login"}, "root_cause": "get_user方法返回None，导致在访问user['name']时引发TypeError。", "evidence": [{"file": "repository.py", "line": 4, "symbol": "repository.UserRepository.get_user", "code": "return None", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "service.py", "line": 10, "symbol": "service.UserService.login", "code": "user = self.repo.get_user(user_id)", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}, {"file": "service.py", "line": 12, "symbol": "service.UserService.login", "code": "return user[\"name\"]", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": [], "fix_suggestion": "检查get_user方法的实现，确保它返回一个有效的用户对象，而不是None。", "uncertainty": "get_user方法的实现细节未完全观察到，可能存在其他导致返回None的原因。 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["证据未见于成功 Observation：service.py:10", "调用链含有未观察到的已解析关系；仅保留已核验前缀", "CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 2 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置", "EVIDENCE_NOT_FOUND: 模型原稿包含无法核验的源码", "CALL_EDGE_NOT_VERIFIED: 模型原稿包含无法核验的调用边"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：Python 空值返回与下标访问。

### runtime-python-login · repeat #3 · PARTIAL

- 问题：为什么UserService.login出现TypeError异常？请检查返回值来源。
- Planner：期望 `RUNTIME_ERROR`；实际 `RUNTIME_ERROR`；通过。
- Plan：`{"task_type": "RUNTIME_ERROR", "analysis_goal": "定位异常位置、调用链和错误值来源", "target_keywords": ["login"], "target_source": "QUERY", "required_evidence": ["exception_location", "target_method_source", "caller_context", "callee_context", "error_value_origin"], "preferred_tools": ["searchSymbol", "findCallers", "findCallees", "readFile"], "stop_condition": "找到异常位置、错误值来源及对应源码证据；否则明确证据不足"}`
- Tool Trace：`searchSymbol → searchSymbol → searchSymbol → readFile → searchSymbol → readFile → findCallers → findCallees`
- 目标 Symbol：`UserService.login`；已由 searchSymbol 确认。
- 工具族：期望 `searchSymbol, findCallees, readFile`；覆盖。
- 证据：[{"file": "repository.py", "code": "return None", "in_trace": true, "in_diagnosis": true}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": true, "in_diagnosis": true}]
- FinalDiagnosis：{"issue_type": "RUNTIME_ERROR", "summary": "UserService.login出现TypeError异常，因为get_user返回None，尝试访问None的'\"name\"'属性。", "location": {"file": "service.py", "line": 12, "symbol": "service.UserService.login"}, "root_cause": "get_user方法返回None，导致在访问user['name']时引发TypeError。", "evidence": [{"file": "repository.py", "line": 4, "symbol": "repository.UserRepository.get_user", "code": "return None", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "service.py", "line": 10, "symbol": "service.UserService.login", "code": "user = self.repo.get_user(user_id)", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}, {"file": "service.py", "line": 12, "symbol": "service.UserService.login", "code": "return user[\"name\"]", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": [], "fix_suggestion": "检查get_user方法的实现，确保它返回一个有效的用户对象，而不是None。", "uncertainty": "get_user方法的实现细节未完全观察到，可能存在其他导致返回None的原因。 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}
- 不支持/校验问题：["证据未见于成功 Observation：service.py:10", "调用链含有未观察到的已解析关系；仅保留已核验前缀", "CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 2 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置", "EVIDENCE_NOT_FOUND: 模型原稿包含无法核验的源码", "CALL_EDGE_NOT_VERIFIED: 模型原稿包含无法核验的调用边"]
- Agent 状态：`COMPLETED`；诊断状态：`VALID`；用户提示：无。
- 错误：无；类别：`{"http_502": false, "empty_response": false, "invalid_json": false, "tool_call_parse_error": false}`。备注：Python 空值返回与下标访问。


## 冻结 Baseline vs Execution Policy

以下 BEFORE 来自原始保存的真实 API 报告；AFTER 来自本轮真实 API 报告。比较时重放 Observation 计算进展，未重跑或改写旧响应。

### 总体指标（8 个基线场景）

| 指标 | BEFORE | AFTER |
|---|---:|---:|
| average_tool_steps | 5.12 | 4.88 |
| duplicate_attempts | 1 | 0 |
| no_progress_calls | 7 | 7 |
| executed_no_progress_calls | 6 | 7 |
| max_steps_hits | 0 | 0 |
| complete_observation_checklists | 3 | 3 |
| partial_observation_checklists | 3 | 3 |
| complete_final_call_chains | 1 | 1 |
| unsupported_tasks | 2 | 2 |
| invalid_call_edges | 0 | 1 |
| valid_final_diagnosis | 6 | 6 |
| evidence_grounding_pass | 6 | 6 |

### 逐场景变化

#### runtime-inventory-npe · PARTIAL → PARTIAL

- Tool Trace：`searchSymbol → readFile → findCallers → readFile → searchSymbol → searchSymbol → findCallers → readFile` → `searchSymbol → readFile → findCallers → readFile → searchSymbol → readFile`
- 步数：8 → 6；重复调用：0 → 0；无进展：1 → 0。
- Evidence Before：`[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": true}]`
- Evidence After：`[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": true}]`
- No-progress / Policy Events：`[]`
- FinalDiagnosis：`{"issue_type": "RUNTIME_ERROR", "summary": "NullPointerException in InventoryService.checkStock due to null return from InventoryRepository.findStock", "location": {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock"}, "root_cause": "InventoryRepository.findStock returns null, which causes NullPointerException when accessed in InventoryService.checkStock", "evidence": [{"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock", "code": "if (stock.available) {", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}], "call_chain": ["demo.order.OrderService.createOrder", "demo.order.InventoryService.checkStock"], "fix_suggestion": "Ensure InventoryRepository.findStock returns a valid Inventory object instead of null", "uncertainty": "None 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}`
- Unsupported Claims / 校验问题：`["CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 3 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置"]`
- 备注：Java 空值来源与解引用；不能只凭调用断言。

#### runtime-python-login · PARTIAL → PARTIAL

- Tool Trace：`searchSymbol → searchSymbol → searchSymbol → readFile → findCallers → findCallees → readFile → searchSymbol` → `searchSymbol → searchSymbol → searchSymbol → readFile → searchSymbol → readFile → findCallers → findCallees`
- 步数：8 → 8；重复调用：1 → 0；无进展：5 → 4。
- Evidence Before：`[{"file": "repository.py", "code": "return None", "in_trace": false, "in_diagnosis": false}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": true, "in_diagnosis": true}]`
- Evidence After：`[{"file": "repository.py", "code": "return None", "in_trace": true, "in_diagnosis": true}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": true, "in_diagnosis": true}]`
- No-progress / Policy Events：`[{"step": 1, "status": "NO_NEW_EVIDENCE", "tool": "searchSymbol", "message": "Tool completed without new Symbols, files, source lines, or resolved edges."}, {"step": 2, "status": "NO_PROGRESS", "tool": "searchSymbol", "message": "Tool completed without new Symbols, files, source lines, or resolved edges."}, {"step": 7, "status": "NO_NEW_EVIDENCE", "tool": "findCallers", "message": "Tool completed without new Symbols, files, source lines, or resolved edges."}, {"step": 8, "status": "NO_PROGRESS", "tool": "findCallees", "message": "Tool completed without new Symbols, files, source lines, or resolved edges."}, {"step": 9, "status": "FINAL_ONLY", "message": "Tool budget exhausted; one final-only model turn, no Tools exposed."}]`
- FinalDiagnosis：`{"issue_type": "RUNTIME_ERROR", "summary": "UserService.login出现TypeError异常，因为get_user返回None，尝试访问None的'\"name\"'属性。", "location": {"file": "service.py", "line": 12, "symbol": "service.UserService.login"}, "root_cause": "get_user方法返回None，导致在访问user['name']时引发TypeError。", "evidence": [{"file": "repository.py", "line": 4, "symbol": "repository.UserRepository.get_user", "code": "return None", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "service.py", "line": 10, "symbol": "service.UserService.login", "code": "user = self.repo.get_user(user_id)", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}, {"file": "service.py", "line": 12, "symbol": "service.UserService.login", "code": "return user[\"name\"]", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": [], "fix_suggestion": "检查get_user方法的实现，确保它返回一个有效的用户对象，而不是None。", "uncertainty": "get_user方法的实现细节未完全观察到，可能存在其他导致返回None的原因。 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}`
- Unsupported Claims / 校验问题：`["证据未见于成功 Observation：service.py:10", "调用链含有未观察到的已解析关系；仅保留已核验前缀", "CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 2 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置", "EVIDENCE_NOT_FOUND: 模型原稿包含无法核验的源码", "CALL_EDGE_NOT_VERIFIED: 模型原稿包含无法核验的调用边"]`
- 备注：Python 空值返回与下标访问。

#### business-price · PARTIAL → PARTIAL

- Tool Trace：`searchSymbol → readFile → findCallers → readFile` → `searchSymbol → readFile → findCallers → readFile`
- 步数：4 → 4；重复调用：0 → 0；无进展：0 → 0。
- Evidence Before：`[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]`
- Evidence After：`[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]`
- No-progress / Policy Events：`[]`
- FinalDiagnosis：`{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}`
- Unsupported Claims / 校验问题：`["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则", "EVIDENCE_PROJECTED_FROM_TOOL: 1 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正", "UNSUPPORTED_CLAIM_REMOVED: 无需求证据的公式断言已移除"]`
- 备注：正确计价规则未在源码中给出。

#### business-order-return · PARTIAL → PARTIAL

- Tool Trace：`searchSymbol → readFile → findCallers → findCallees → readFile` → `searchSymbol → readFile → findCallers → findCallees → readFile`
- 步数：5 → 5；重复调用：0 → 0；无进展：1 → 1。
- Evidence Before：`[{"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}, {"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}]`
- Evidence After：`[{"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}, {"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}]`
- No-progress / Policy Events：`[{"step": 3, "status": "NO_NEW_EVIDENCE", "tool": "findCallers", "message": "Tool completed without new Symbols, files, source lines, or resolved edges."}]`
- FinalDiagnosis：`{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}`
- Unsupported Claims / 校验问题：`["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正", "UNSUPPORTED_CLAIM_REMOVED: 无需求证据的公式断言已移除"]`
- 备注：需同时看调用方与计算方法。

#### callchain-registration · PARTIAL → PARTIAL

- Tool Trace：`searchSymbol → findCallees → findCallees → findCallees → readFile → readFile → readFile → readFile` → `searchSymbol → findCallees → findCallers → searchSymbol → findCallers → findCallees → readFile → readFile`
- 步数：8 → 8；重复调用：0 → 0；无进展：0 → 2。
- Evidence Before：`[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": true, "in_diagnosis": true}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": true, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": true, "in_diagnosis": false}]`
- Evidence After：`[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": true, "in_diagnosis": false}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": true, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": false, "in_diagnosis": false}]`
- No-progress / Policy Events：`[{"step": 3, "status": "NO_NEW_EVIDENCE", "tool": "findCallers", "message": "Tool completed without new Symbols, files, source lines, or resolved edges."}, {"step": 6, "status": "NO_NEW_EVIDENCE", "tool": "findCallees", "message": "Tool completed without new Symbols, files, source lines, or resolved edges."}, {"step": 9, "status": "FINAL_ONLY", "message": "Tool budget exhausted; one final-only model turn, no Tools exposed."}]`
- FinalDiagnosis：`{"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "The call chain from UserService.register to ConfigRepository.getTemplate is incomplete.", "location": {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail"}, "root_cause": "The call chain stops at EmailService.sendEmail, and the next outgoing edge to ConfigRepository.getTemplate has not been verified.", "evidence": [{"file": "src/UserService.java", "line": 6, "symbol": "UserService.register", "code": "emailService.sendEmail(email)", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 2}, {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail", "code": "String content = templateService.render();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 8}], "call_chain": ["UserService.register", "EmailService.sendEmail"], "fix_suggestion": "Verify the call from EmailService.sendEmail to TemplateService.render and then from TemplateService.render to ConfigRepository.getTemplate.", "uncertainty": "The call chain is incomplete as it stops at EmailService.sendEmail. Further investigation is needed to verify the next outgoing edge.", "root_cause_kind": "INFERENCE"}`
- Unsupported Claims / 校验问题：`["CALL_EDGE_NOT_VERIFIED: 请求的完整路径缺少已解析边"]`
- 备注：需核对全部已解析 CALLS 边。

#### callchain-order-stock · PARTIAL → PARTIAL

- Tool Trace：`searchSymbol → findCallees → findCallees → findCallees → readFile → readFile → readFile → readFile` → `searchSymbol → findCallees → findCallees → findCallees → readFile → readFile → readFile → readFile`
- 步数：8 → 8；重复调用：0 → 0；无进展：0 → 0。
- Evidence Before：`[{"file": "OrderController.java", "code": "orderService.createOrder();", "in_trace": true, "in_diagnosis": true}, {"file": "OrderService.java", "code": "inventoryService.checkStock();", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "inventoryRepository.findStock();", "in_trace": true, "in_diagnosis": false}]`
- Evidence After：`[{"file": "OrderController.java", "code": "orderService.createOrder();", "in_trace": true, "in_diagnosis": true}, {"file": "OrderService.java", "code": "inventoryService.checkStock();", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "inventoryRepository.findStock();", "in_trace": true, "in_diagnosis": false}]`
- No-progress / Policy Events：`[{"step": 9, "status": "FINAL_ONLY", "message": "Tool budget exhausted; one final-only model turn, no Tools exposed."}]`
- FinalDiagnosis：`{"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "Traced the call chain from OrderController.createOrder to InventoryRepository.findStock.", "location": {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock"}, "root_cause": "The call chain from OrderController.createOrder to InventoryRepository.findStock is complete and verified.", "evidence": [{"file": "OrderController.java", "line": 11, "symbol": "demo.order.OrderController.createOrder", "code": "orderService.createOrder()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 2}, {"file": "OrderService.java", "line": 11, "symbol": "demo.order.OrderService.createOrder", "code": "inventoryService.checkStock()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 3}, {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "inventoryRepository.findStock()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 4}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 8}, {"file": "OrderController.java", "line": 11, "symbol": "demo.order.OrderController.createOrder", "code": "orderService.createOrder();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}, {"file": "OrderService.java", "line": 11, "symbol": "demo.order.OrderService.createOrder", "code": "inventoryService.checkStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 7}], "call_chain": ["OrderController.createOrder", "OrderService.createOrder", "InventoryService.checkStock", "InventoryRepository.findStock"], "fix_suggestion": "Ensure that InventoryRepository.findStock returns a valid Inventory object instead of null.", "uncertainty": "None", "root_cause_kind": "INFERENCE"}`
- Unsupported Claims / 校验问题：`["模型行号 InventoryRepository.java:4 与 Observation 不符，已按源码修正为 5", "模型定位行号与源码证据不符，已按已核验代码行修正", "CALL_CHAIN_PROJECTED_FROM_VERIFIED_EDGES", "EVIDENCE_PROJECTED_FROM_TOOL: 3 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正"]`
- 备注：需核对全部已解析 CALLS 边。

#### config-database-url · UNSUPPORTED → UNSUPPORTED

- Tool Trace：`无` → `无`
- 步数：0 → 0；重复调用：0 → 0；无进展：0 → 0。
- Evidence Before：`[]`
- Evidence After：`[]`
- No-progress / Policy Events：`[{"step": 0, "status": "UNSUPPORTED", "message": "No configuration reader is registered."}]`
- FinalDiagnosis：`null`
- Unsupported Claims / 校验问题：`["当前 ToolRegistry 没有配置文件读取与关联能力"]`
- 备注：当前 Scanner/CodeReader 不支持 YAML；应明确能力不足。

#### config-database-username · UNSUPPORTED → UNSUPPORTED

- Tool Trace：`无` → `无`
- 步数：0 → 0；重复调用：0 → 0；无进展：0 → 0。
- Evidence Before：`[]`
- Evidence After：`[]`
- No-progress / Policy Events：`[{"step": 0, "status": "UNSUPPORTED", "message": "No configuration reader is registered."}]`
- FinalDiagnosis：`null`
- Unsupported Claims / 校验问题：`["当前 ToolRegistry 没有配置文件读取与关联能力"]`
- 备注：当前工具链无法证明 YAML 值与使用位置。


## Verified Evidence / Projection 对比（冻结 v2 → 本轮）

旧结果仅从已保存的真实 Trace 重放 Observation；不重跑模型，也不把期望答案送入 Agent。
`observed_expected_snippets` 统计真实源码行中逐字出现的评测片段；`projected_expected_evidence` 仍按最终诊断的完整代码文本比较，二者不可混同。Symbol/Line mismatch 与 unsupported_claims 按受影响运行数统计，不把同一问题的中英文诊断重复计数。

| 指标 | v2 | 本轮 |
|---|---:|---:|
| valid_final_diagnosis | 6 | 6 |
| evidence_grounding | 6 | 6 |
| complete_runtime_evidence | 1 | 2 |
| complete_final_call_chains | 2 | 1 |
| observed_expected_snippets | 13 | 13 |
| projected_expected_evidence | 10 | 10 |
| projected_fact_count | 0 | 9 |
| symbol_mismatch | 0 | 0 |
| line_mismatch | 5 | 5 |
| unsupported_claims | 2 | 3 |

### 每个基线场景

#### runtime-inventory-npe · PARTIAL → PARTIAL

- 旧 Trace：`searchSymbol → readFile → findCallers → readFile → searchSymbol → searchSymbol → findCallers → readFile`
- 新 Trace：`searchSymbol → readFile → findCallers → readFile → searchSymbol → readFile`
- Verified Evidence Before：`[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": true}]`
- Verified Evidence After：`[{"file": "InventoryRepository.java", "code": "return null;", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "if (stock.available) {", "in_trace": true, "in_diagnosis": true}]`
- Data-flow Chain Before：`{"assignment": {"file": "InventoryService.java", "line": 11, "symbol_id": "InventoryService.java:10:15:METHOD:demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "evidence_type": "ASSIGNMENT", "source_tool": "readFile", "source_step": 2}, "invalid_value_origin": {"file": "InventoryRepository.java", "line": 5, "symbol_id": "InventoryRepository.java:4:6:METHOD:demo.order.InventoryRepository.findStock", "code": "return null;", "evidence_type": "RETURN_VALUE", "source_tool": "readFile", "source_step": 8}, "trigger_operation": {"file": "InventoryService.java", "line": 12, "symbol_id": "InventoryService.java:10:15:METHOD:demo.order.InventoryService.checkStock", "code": "if (stock.available) {", "evidence_type": "DEREFERENCE", "source_tool": "readFile", "source_step": 2}, "related_call_edge": {"source_id": "InventoryService.java:10:15:METHOD:demo.order.InventoryService.checkStock", "target_id": "InventoryRepository.java:4:6:METHOD:demo.order.InventoryRepository.findStock", "file": "InventoryService.java", "line": 11, "code": "inventoryRepository.findStock()", "source_tool": "findCallers", "source_step": 7}, "source_to_usage_linkage": "RESOLVED_CALL_EDGE", "candidate_method": "findStock", "callee_symbol": {"symbol_id": "InventoryRepository.java:4:6:METHOD:demo.order.InventoryRepository.findStock", "raw_name": "demo.order.InventoryRepository.findStock", "file": "InventoryRepository.java", "line": 4, "end_line": 6, "symbol_type": "METHOD", "language": "JAVA", "signature": "findStock()", "source_tool": "searchSymbol", "source_step": 6}}`
- Data-flow Chain After：`{"assignment": {"file": "InventoryService.java", "line": 11, "symbol_id": "InventoryService.java:10:15:METHOD:demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "evidence_type": "ASSIGNMENT", "source_tool": "readFile", "source_step": 2}, "invalid_value_origin": {"file": "InventoryRepository.java", "line": 5, "symbol_id": "InventoryRepository.java:4:6:METHOD:demo.order.InventoryRepository.findStock", "code": "return null;", "evidence_type": "RETURN_VALUE", "source_tool": "readFile", "source_step": 6}, "trigger_operation": {"file": "InventoryService.java", "line": 12, "symbol_id": "InventoryService.java:10:15:METHOD:demo.order.InventoryService.checkStock", "code": "if (stock.available) {", "evidence_type": "DEREFERENCE", "source_tool": "readFile", "source_step": 2}, "related_call_edge": null, "source_to_usage_linkage": "OBSERVED_OWNER_TYPE", "candidate_method": "findStock", "callee_symbol": {"symbol_id": "InventoryRepository.java:4:6:METHOD:demo.order.InventoryRepository.findStock", "raw_name": "demo.order.InventoryRepository.findStock", "file": "InventoryRepository.java", "line": 4, "end_line": 6, "symbol_type": "METHOD", "language": "JAVA", "signature": "findStock()", "source_tool": "searchSymbol", "source_step": 5}}`
- Canonical Symbols：`[{"raw": "demo.order.InventoryService.checkStock", "canonical": "InventoryService.checkStock", "signature": "checkStock()", "id": "InventoryService.java:10:15:METHOD:demo.order.InventoryService.checkStock"}, {"raw": "demo.order.OrderService.createOrder", "canonical": "OrderService.createOrder", "signature": "createOrder()", "id": "OrderService.java:10:12:METHOD:demo.order.OrderService.createOrder"}, {"raw": "demo.order.InventoryRepository.findStock", "canonical": "InventoryRepository.findStock", "signature": "findStock()", "id": "InventoryRepository.java:4:6:METHOD:demo.order.InventoryRepository.findStock"}]`
- Verified Call Chain / Projection：`[]` / `["demo.order.OrderService.createOrder", "demo.order.InventoryService.checkStock"]`
- Model Claim：`{"location": {"file": "InventoryService.java", "line": 11, "symbol": "checkStock"}, "call_chain": ["OrderService.createOrder", "InventoryService.checkStock"], "evidence": [{"file": "InventoryService.java", "line": 11, "symbol": "checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "NullPointerException occurs here", "kind": "FACT", "source_tool": null, "source_step": null}, {"file": "InventoryRepository.java", "line": 5, "symbol": "findStock", "code": "return null;", "reason": "findStock returns null, causing the NullPointerException", "kind": "FACT", "source_tool": null, "source_step": null}]}`
- System Corrected Result：`{"location": {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock"}, "call_chain": ["demo.order.OrderService.createOrder", "demo.order.InventoryService.checkStock"], "projected_fact_count": 3}`
- Diagnosis Issues：`["CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 3 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置"]`
- FinalDiagnosis：`{"issue_type": "RUNTIME_ERROR", "summary": "NullPointerException in InventoryService.checkStock due to null return from InventoryRepository.findStock", "location": {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock"}, "root_cause": "InventoryRepository.findStock returns null, which causes NullPointerException when accessed in InventoryService.checkStock", "evidence": [{"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "InventoryService.java", "line": 12, "symbol": "demo.order.InventoryService.checkStock", "code": "if (stock.available) {", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}], "call_chain": ["demo.order.OrderService.createOrder", "demo.order.InventoryService.checkStock"], "fix_suggestion": "Ensure InventoryRepository.findStock returns a valid Inventory object instead of null", "uncertainty": "None 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}`

#### runtime-python-login · PARTIAL → PARTIAL

- 旧 Trace：`searchSymbol → searchSymbol → searchSymbol → readFile → findCallers → findCallees → readFile → searchSymbol`
- 新 Trace：`searchSymbol → searchSymbol → searchSymbol → readFile → searchSymbol → readFile → findCallers → findCallees`
- Verified Evidence Before：`[{"file": "repository.py", "code": "return None", "in_trace": false, "in_diagnosis": false}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": true, "in_diagnosis": true}]`
- Verified Evidence After：`[{"file": "repository.py", "code": "return None", "in_trace": true, "in_diagnosis": true}, {"file": "service.py", "code": "return user[\"name\"]", "in_trace": true, "in_diagnosis": true}]`
- Data-flow Chain Before：`{"assignment": {"file": "service.py", "line": 10, "symbol_id": "service.py:8:12:METHOD:service.UserService.login", "code": "user = self.repo.get_user(user_id)", "evidence_type": "ASSIGNMENT", "source_tool": "readFile", "source_step": 4}, "invalid_value_origin": null, "trigger_operation": {"file": "service.py", "line": 12, "symbol_id": "service.py:8:12:METHOD:service.UserService.login", "code": "return user[\"name\"]", "evidence_type": "DEREFERENCE", "source_tool": "readFile", "source_step": 4}, "related_call_edge": null, "source_to_usage_linkage": "OBSERVED_OWNER_TYPE", "candidate_method": "get_user", "callee_symbol": {"symbol_id": "repository.py:3:4:METHOD:repository.UserRepository.get_user", "raw_name": "repository.UserRepository.get_user", "file": "repository.py", "line": 3, "end_line": 4, "symbol_type": "METHOD", "language": "PYTHON", "signature": "get_user(self, user_id)", "source_tool": "searchSymbol", "source_step": 8}}`
- Data-flow Chain After：`{"assignment": {"file": "service.py", "line": 10, "symbol_id": "service.py:8:12:METHOD:service.UserService.login", "code": "user = self.repo.get_user(user_id)", "evidence_type": "ASSIGNMENT", "source_tool": "readFile", "source_step": 4}, "invalid_value_origin": {"file": "repository.py", "line": 4, "symbol_id": "repository.py:3:4:METHOD:repository.UserRepository.get_user", "code": "return None", "evidence_type": "RETURN_VALUE", "source_tool": "readFile", "source_step": 6}, "trigger_operation": {"file": "service.py", "line": 12, "symbol_id": "service.py:8:12:METHOD:service.UserService.login", "code": "return user[\"name\"]", "evidence_type": "DEREFERENCE", "source_tool": "readFile", "source_step": 4}, "related_call_edge": null, "source_to_usage_linkage": "OBSERVED_OWNER_TYPE", "candidate_method": "get_user", "callee_symbol": {"symbol_id": "repository.py:3:4:METHOD:repository.UserRepository.get_user", "raw_name": "repository.UserRepository.get_user", "file": "repository.py", "line": 3, "end_line": 4, "symbol_type": "METHOD", "language": "PYTHON", "signature": "get_user(self, user_id)", "source_tool": "searchSymbol", "source_step": 5}}`
- Canonical Symbols：`[{"raw": "service.UserService.login", "canonical": "UserService.login", "signature": "login(self, user_id)", "id": "service.py:8:12:METHOD:service.UserService.login"}, {"raw": "repository.UserRepository.get_user", "canonical": "UserRepository.get_user", "signature": "get_user(self, user_id)", "id": "repository.py:3:4:METHOD:repository.UserRepository.get_user"}]`
- Verified Call Chain / Projection：`[]` / `[]`
- Model Claim：`{"location": {"file": "service.py", "line": 10, "symbol": "service.UserService.login"}, "call_chain": ["service.UserService.login", "repository.UserRepository.get_user"], "evidence": [{"file": "service.py", "line": 10, "symbol": "service.UserService.login", "code": "return user['name']", "reason": "尝试访问None的'\"name\"'属性。", "kind": "FACT", "source_tool": null, "source_step": null}, {"file": "repository.py", "line": 4, "symbol": "repository.UserRepository.get_user", "code": "return None", "reason": "get_user方法返回None。", "kind": "FACT", "source_tool": null, "source_step": null}]}`
- System Corrected Result：`{"location": {"file": "service.py", "line": 12, "symbol": "service.UserService.login"}, "call_chain": [], "projected_fact_count": 2}`
- Diagnosis Issues：`["证据未见于成功 Observation：service.py:10", "调用链含有未观察到的已解析关系；仅保留已核验前缀", "CALL_EDGE_NOT_VERIFIED: 返回值链仅有局部源码/类型关联，缺少已解析 CALLS 边", "EVIDENCE_PROJECTED_FROM_TOOL: 2 verified facts", "MODEL_LINE_MISMATCH: 使用 Observation 中的真实位置", "EVIDENCE_NOT_FOUND: 模型原稿包含无法核验的源码", "CALL_EDGE_NOT_VERIFIED: 模型原稿包含无法核验的调用边"]`
- FinalDiagnosis：`{"issue_type": "RUNTIME_ERROR", "summary": "UserService.login出现TypeError异常，因为get_user返回None，尝试访问None的'\"name\"'属性。", "location": {"file": "service.py", "line": 12, "symbol": "service.UserService.login"}, "root_cause": "get_user方法返回None，导致在访问user['name']时引发TypeError。", "evidence": [{"file": "repository.py", "line": 4, "symbol": "repository.UserRepository.get_user", "code": "return None", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "service.py", "line": 10, "symbol": "service.UserService.login", "code": "user = self.repo.get_user(user_id)", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}, {"file": "service.py", "line": 12, "symbol": "service.UserService.login", "code": "return user[\"name\"]", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": [], "fix_suggestion": "检查get_user方法的实现，确保它返回一个有效的用户对象，而不是None。", "uncertainty": "get_user方法的实现细节未完全观察到，可能存在其他导致返回None的原因。 该返回值关联仅由局部源码/类型文本支持，静态调用图未解析该边；需运行时确认。", "root_cause_kind": "INFERENCE"}`

#### business-price · PARTIAL → PARTIAL

- 旧 Trace：`searchSymbol → readFile → findCallers → readFile`
- 新 Trace：`searchSymbol → readFile → findCallers → readFile`
- Verified Evidence Before：`[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]`
- Verified Evidence After：`[{"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}, {"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}]`
- Data-flow Chain Before：`null`
- Data-flow Chain After：`null`
- Canonical Symbols：`[{"raw": "PriceService.calculatePrice", "canonical": "PriceService.calculatePrice", "signature": "calculatePrice(double price, int quantity)", "id": "src/PriceService.java:3:9:METHOD:PriceService.calculatePrice"}, {"raw": "OrderService.createOrder", "canonical": "OrderService.createOrder", "signature": "createOrder()", "id": "src/OrderService.java:5:7:METHOD:OrderService.createOrder"}]`
- Verified Call Chain / Projection：`[]` / `["OrderService.createOrder", "PriceService.calculatePrice"]`
- Model Claim：`{"location": {"file": "src/PriceService.java", "line": 6, "symbol": "PriceService.calculatePrice"}, "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "evidence": [{"file": "src/PriceService.java", "line": 6, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "价格计算公式错误", "kind": "FACT", "source_tool": null, "source_step": null}, {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "调用 calculatePrice 方法", "kind": "FACT", "source_tool": null, "source_step": null}]}`
- System Corrected Result：`{"location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "projected_fact_count": 1}`
- Diagnosis Issues：`["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则", "EVIDENCE_PROJECTED_FROM_TOOL: 1 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正", "UNSUPPORTED_CLAIM_REMOVED: 无需求证据的公式断言已移除"]`
- FinalDiagnosis：`{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 4}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}`

#### business-order-return · PARTIAL → PARTIAL

- 旧 Trace：`searchSymbol → readFile → findCallers → findCallees → readFile`
- 新 Trace：`searchSymbol → readFile → findCallers → findCallees → readFile`
- Verified Evidence Before：`[{"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}, {"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}]`
- Verified Evidence After：`[{"file": "src/OrderService.java", "code": "return priceService.calculatePrice(100, 3);", "in_trace": true, "in_diagnosis": true}, {"file": "src/PriceService.java", "code": "return price + quantity * discount;", "in_trace": true, "in_diagnosis": true}]`
- Data-flow Chain Before：`null`
- Data-flow Chain After：`null`
- Canonical Symbols：`[{"raw": "OrderService.createOrder", "canonical": "OrderService.createOrder", "signature": "createOrder()", "id": "src/OrderService.java:5:7:METHOD:OrderService.createOrder"}, {"raw": "PriceService.calculatePrice", "canonical": "PriceService.calculatePrice", "signature": "calculatePrice(double price, int quantity)", "id": "src/PriceService.java:3:9:METHOD:PriceService.calculatePrice"}]`
- Verified Call Chain / Projection：`[]` / `["OrderService.createOrder", "PriceService.calculatePrice"]`
- Model Claim：`{"location": {"file": "src/PriceService.java", "line": 6, "symbol": "PriceService.calculatePrice"}, "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "evidence": [{"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "调用PriceService.calculatePrice方法计算价格", "kind": "FACT", "source_tool": null, "source_step": null}, {"file": "src/PriceService.java", "line": 6, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "价格计算逻辑有误，应该是price * discount + quantity * discount", "kind": "FACT", "source_tool": null, "source_step": null}]}`
- System Corrected Result：`{"location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "projected_fact_count": 0}`
- Diagnosis Issues：`["模型行号 src/PriceService.java:6 与 Observation 不符，已按源码修正为 8", "模型定位行号与源码证据不符，已按已核验代码行修正", "模型声称确定的正确业务公式，但 Observation 中没有业务规则", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正", "UNSUPPORTED_CLAIM_REMOVED: 无需求证据的公式断言已移除"]`
- FinalDiagnosis：`{"issue_type": "BUSINESS_LOGIC_ERROR", "summary": "已定位价格计算实现；是否符合业务规则仍需确认", "location": {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice"}, "root_cause": "当前源码实现可能与预期业务规则不符；正确公式需要需求或测试用例确认。", "evidence": [{"file": "src/OrderService.java", "line": 6, "symbol": "OrderService.createOrder", "code": "return priceService.calculatePrice(100, 3);", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 2}, {"file": "src/PriceService.java", "line": 8, "symbol": "PriceService.calculatePrice", "code": "return price + quantity * discount;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}], "call_chain": ["OrderService.createOrder", "PriceService.calculatePrice"], "fix_suggestion": "核对单价、数量、折扣的业务规则与测试用例，再调整计算表达式。", "uncertainty": "现有源码可确认当前计算表达式，但未提供预期计价规则。", "root_cause_kind": "INFERENCE"}`

#### callchain-registration · PARTIAL → PARTIAL

- 旧 Trace：`searchSymbol → findCallees → findCallees → findCallees → readFile → readFile → readFile → readFile`
- 新 Trace：`searchSymbol → findCallees → findCallers → searchSymbol → findCallers → findCallees → readFile → readFile`
- Verified Evidence Before：`[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": true, "in_diagnosis": true}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": true, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": true, "in_diagnosis": false}]`
- Verified Evidence After：`[{"file": "src/UserService.java", "code": "emailService.sendEmail(email);", "in_trace": true, "in_diagnosis": false}, {"file": "src/EmailService.java", "code": "templateService.render();", "in_trace": true, "in_diagnosis": false}, {"file": "src/TemplateService.java", "code": "repository.getTemplate();", "in_trace": false, "in_diagnosis": false}]`
- Data-flow Chain Before：`null`
- Data-flow Chain After：`null`
- Canonical Symbols：`[{"raw": "UserService.register", "canonical": "UserService.register", "signature": "register(String email)", "id": "src/UserService.java:5:7:METHOD:UserService.register"}, {"raw": "EmailService.sendEmail", "canonical": "EmailService.sendEmail", "signature": "sendEmail(String email)", "id": "src/EmailService.java:5:8:METHOD:EmailService.sendEmail"}, {"raw": "ConfigRepository.getTemplate", "canonical": "ConfigRepository.getTemplate", "signature": "getTemplate()", "id": "src/ConfigRepository.java:3:5:METHOD:ConfigRepository.getTemplate"}, {"raw": "TemplateService.render", "canonical": "TemplateService.render", "signature": "render()", "id": "src/TemplateService.java:5:8:METHOD:TemplateService.render"}]`
- Verified Call Chain / Projection：`[]` / `["UserService.register", "EmailService.sendEmail"]`
- Model Claim：`{"location": {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail"}, "call_chain": ["UserService.register", "EmailService.sendEmail"], "evidence": [{"file": "src/UserService.java", "line": 6, "symbol": "UserService.register", "code": "emailService.sendEmail(email)", "reason": "UserService.register calls EmailService.sendEmail.", "kind": "FACT", "source_tool": null, "source_step": null}, {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail", "code": "String content = templateService.render();", "reason": "EmailService.sendEmail calls TemplateService.render.", "kind": "FACT", "source_tool": null, "source_step": null}]}`
- System Corrected Result：`{"location": {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail"}, "call_chain": ["UserService.register", "EmailService.sendEmail"], "projected_fact_count": 0}`
- Diagnosis Issues：`["CALL_EDGE_NOT_VERIFIED: 请求的完整路径缺少已解析边"]`
- FinalDiagnosis：`{"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "The call chain from UserService.register to ConfigRepository.getTemplate is incomplete.", "location": {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail"}, "root_cause": "The call chain stops at EmailService.sendEmail, and the next outgoing edge to ConfigRepository.getTemplate has not been verified.", "evidence": [{"file": "src/UserService.java", "line": 6, "symbol": "UserService.register", "code": "emailService.sendEmail(email)", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 2}, {"file": "src/EmailService.java", "line": 6, "symbol": "EmailService.sendEmail", "code": "String content = templateService.render();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 8}], "call_chain": ["UserService.register", "EmailService.sendEmail"], "fix_suggestion": "Verify the call from EmailService.sendEmail to TemplateService.render and then from TemplateService.render to ConfigRepository.getTemplate.", "uncertainty": "The call chain is incomplete as it stops at EmailService.sendEmail. Further investigation is needed to verify the next outgoing edge.", "root_cause_kind": "INFERENCE"}`

#### callchain-order-stock · PARTIAL → PARTIAL

- 旧 Trace：`searchSymbol → findCallees → findCallees → findCallees → readFile → readFile → readFile → readFile`
- 新 Trace：`searchSymbol → findCallees → findCallees → findCallees → readFile → readFile → readFile → readFile`
- Verified Evidence Before：`[{"file": "OrderController.java", "code": "orderService.createOrder();", "in_trace": true, "in_diagnosis": true}, {"file": "OrderService.java", "code": "inventoryService.checkStock();", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "inventoryRepository.findStock();", "in_trace": true, "in_diagnosis": false}]`
- Verified Evidence After：`[{"file": "OrderController.java", "code": "orderService.createOrder();", "in_trace": true, "in_diagnosis": true}, {"file": "OrderService.java", "code": "inventoryService.checkStock();", "in_trace": true, "in_diagnosis": true}, {"file": "InventoryService.java", "code": "inventoryRepository.findStock();", "in_trace": true, "in_diagnosis": false}]`
- Data-flow Chain Before：`null`
- Data-flow Chain After：`null`
- Canonical Symbols：`[{"raw": "demo.order.OrderController.createOrder", "canonical": "OrderController.createOrder", "signature": "createOrder()", "id": "OrderController.java:10:12:METHOD:demo.order.OrderController.createOrder"}, {"raw": "demo.order.OrderService.createOrder", "canonical": "OrderService.createOrder", "signature": "createOrder()", "id": "OrderService.java:10:12:METHOD:demo.order.OrderService.createOrder"}, {"raw": "demo.order.InventoryService.checkStock", "canonical": "InventoryService.checkStock", "signature": "checkStock()", "id": "InventoryService.java:10:15:METHOD:demo.order.InventoryService.checkStock"}, {"raw": "demo.order.InventoryRepository.findStock", "canonical": "InventoryRepository.findStock", "signature": "findStock()", "id": "InventoryRepository.java:4:6:METHOD:demo.order.InventoryRepository.findStock"}]`
- Verified Call Chain / Projection：`["OrderController.createOrder", "OrderService.createOrder", "InventoryService.checkStock", "InventoryRepository.findStock"]` / `["OrderController.createOrder", "OrderService.createOrder", "InventoryService.checkStock", "InventoryRepository.findStock"]`
- Model Claim：`{"location": {"file": "InventoryRepository.java", "line": 4, "symbol": "demo.order.InventoryRepository.findStock"}, "call_chain": ["demo.order.OrderController.createOrder", "demo.order.OrderService.createOrder", "demo.order.InventoryService.checkStock", "demo.order.InventoryRepository.findStock"], "evidence": [{"file": "OrderController.java", "line": 11, "symbol": "demo.order.OrderController.createOrder", "code": "orderService.createOrder()", "reason": "OrderController.createOrder calls OrderService.createOrder.", "kind": "FACT", "source_tool": null, "source_step": null}, {"file": "OrderService.java", "line": 11, "symbol": "demo.order.OrderService.createOrder", "code": "inventoryService.checkStock()", "reason": "OrderService.createOrder calls InventoryService.checkStock.", "kind": "FACT", "source_tool": null, "source_step": null}, {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "inventoryRepository.findStock()", "reason": "InventoryService.checkStock calls InventoryRepository.findStock.", "kind": "FACT", "source_tool": null, "source_step": null}, {"file": "InventoryRepository.java", "line": 4, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "InventoryRepository.findStock returns null.", "kind": "FACT", "source_tool": null, "source_step": null}]}`
- System Corrected Result：`{"location": {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock"}, "call_chain": ["OrderController.createOrder", "OrderService.createOrder", "InventoryService.checkStock", "InventoryRepository.findStock"], "projected_fact_count": 3}`
- Diagnosis Issues：`["模型行号 InventoryRepository.java:4 与 Observation 不符，已按源码修正为 5", "模型定位行号与源码证据不符，已按已核验代码行修正", "CALL_CHAIN_PROJECTED_FROM_VERIFIED_EDGES", "EVIDENCE_PROJECTED_FROM_TOOL: 3 verified facts", "MODEL_LINE_MISMATCH: 模型行号已由 Observation 校正"]`
- FinalDiagnosis：`{"issue_type": "CALL_CHAIN_ANALYSIS", "summary": "Traced the call chain from OrderController.createOrder to InventoryRepository.findStock.", "location": {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock"}, "root_cause": "The call chain from OrderController.createOrder to InventoryRepository.findStock is complete and verified.", "evidence": [{"file": "OrderController.java", "line": 11, "symbol": "demo.order.OrderController.createOrder", "code": "orderService.createOrder()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 2}, {"file": "OrderService.java", "line": 11, "symbol": "demo.order.OrderService.createOrder", "code": "inventoryService.checkStock()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 3}, {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "inventoryRepository.findStock()", "reason": "已解析的 CALLS 关系", "kind": "FACT", "source_tool": "call_relation", "source_step": 4}, {"file": "InventoryRepository.java", "line": 5, "symbol": "demo.order.InventoryRepository.findStock", "code": "return null;", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 8}, {"file": "OrderController.java", "line": 11, "symbol": "demo.order.OrderController.createOrder", "code": "orderService.createOrder();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 5}, {"file": "OrderService.java", "line": 11, "symbol": "demo.order.OrderService.createOrder", "code": "inventoryService.checkStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 6}, {"file": "InventoryService.java", "line": 11, "symbol": "demo.order.InventoryService.checkStock", "code": "Inventory stock = inventoryRepository.findStock();", "reason": "readFile 返回的源码", "kind": "FACT", "source_tool": "readFile", "source_step": 7}], "call_chain": ["OrderController.createOrder", "OrderService.createOrder", "InventoryService.checkStock", "InventoryRepository.findStock"], "fix_suggestion": "Ensure that InventoryRepository.findStock returns a valid Inventory object instead of null.", "uncertainty": "None", "root_cause_kind": "INFERENCE"}`

#### config-database-url · UNSUPPORTED → UNSUPPORTED

- 旧 Trace：`无`
- 新 Trace：`无`
- Verified Evidence Before：`[]`
- Verified Evidence After：`[]`
- Data-flow Chain Before：`null`
- Data-flow Chain After：`null`
- Canonical Symbols：`[]`
- Verified Call Chain / Projection：`[]` / `null`
- Model Claim：`null`
- System Corrected Result：`null`
- Diagnosis Issues：`["当前 ToolRegistry 没有配置文件读取与关联能力"]`
- FinalDiagnosis：`null`

#### config-database-username · UNSUPPORTED → UNSUPPORTED

- 旧 Trace：`无`
- 新 Trace：`无`
- Verified Evidence Before：`[]`
- Verified Evidence After：`[]`
- Data-flow Chain Before：`null`
- Data-flow Chain After：`null`
- Canonical Symbols：`[]`
- Verified Call Chain / Projection：`[]` / `null`
- Model Claim：`null`
- System Corrected Result：`null`
- Diagnosis Issues：`["当前 ToolRegistry 没有配置文件读取与关联能力"]`
- FinalDiagnosis：`null`
