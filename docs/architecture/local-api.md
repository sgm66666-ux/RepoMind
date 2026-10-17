# 本地 API 架构

Vue 通过同源 `/api` 请求访问 FastAPI。开发与预览模式由 Vite 提供代理；AST、Symbol Index、Call Graph、Fault Localization、Agent Loop、Tool Calling 和 Ollama Provider 的实现不变。

原 Spring Boot 模块只做 JSON 转发、路径转换、错误封装和 CORS，没有独立业务计算、认证、权限或 Filter。当前用 [browser_api.py](../../services/python-service/app/browser_api.py) 注册薄兼容入口，直接复用原有 FastAPI handler 和同一份内存索引，不再需要单独的 Java 服务。

## 接口兼容

| 浏览器路径 | 复用的原生路径 |
| --- | --- |
| POST /api/repositories/analyze | POST /analysis/repository |
| GET /api/symbols | GET /symbols |
| GET /api/symbols/{id} | GET /symbols/{id} |
| GET /api/symbols/{id}/callers | GET /symbols/{id}/callers |
| GET /api/symbols/{id}/callees | GET /symbols/{id}/callees |
| GET /api/call-graph | GET /call-graph |
| GET /api/files/read | GET /files/read |
| POST /api/context | POST /context |
| GET /api/demo/order-demo | GET /demo/order-demo |
| POST /api/fault-localization | POST /fault-localization |
| POST /api/agent/chat | POST /agent/chat |

成功结果使用原 handler，不重建或改写业务数据。Symbol ID 保留带路径的路由匹配，前端传输时仍需 URL 编码。

浏览器错误保留 `{error, message}`：业务 HTTP 错误使用 `PYTHON_SERVICE_ERROR` 并保留原状态码；未预期错误返回不包含内部细节的 `INTERNAL_ERROR`。原生 API 的 `detail` 错误格式不变，LLM 未配置仍返回 503。Vite 无法连接 FastAPI 时返回结构化 503。

`GET /health` 仍返回 `{status: "ok"}`；`GET /api/health` 保留 `status`、`service` 字段，服务身份改为真实的 `python-service`。前端分别探测存活接口与分析接口，不把模型已安装或进程存活视为 LLM 推理成功。

## 本地启动与部署

[scripts/start-demo.ps1](../../scripts/start-demo.ps1) 只启动 FastAPI 和 Vite，默认端口 8000、5173。可用 `-PythonPort`、`-FrontendPort` 在独立端口验证；[就绪检查](../../scripts/check-readiness.ps1) 同时检查后端和前端代理链路。平台运行不需要 Java/Maven；Java Demo 的独立 Maven 测试仍保留。

[api-proxy.ts](../../services/frontend/api-proxy.ts) 用 `REPOMIND_PYTHON_SERVICE_URL` 配置后端目标，默认 `http://127.0.0.1:8000`。`npm run preview` 也支持同一代理；`npm run build` 的静态产物不包含服务器，不能代替部署时的 API 转发。

部署构建产物时，需同源转发 `/api`；也可构建前将 `VITE_API_BASE_URL` 指向 FastAPI 的源地址（不追加 `/api`），并明确配置后端的 CORS 源。

## 安全与能力边界

- 默认启动仅监听回环地址。CORS 默认允许 `http://localhost:5173`、`http://127.0.0.1:5173`，通过 `REPOMIND_FRONTEND_ORIGINS` 覆盖；不启用跨域凭证。
- Vite 开发和预览禁用自身的默认 CORS 放行，避免将后端白名单扩大到其他 localhost 端口；代理保留 FastAPI 返回的 CORS 头。
- CORS 不是认证。项目原先及当前均没有登录、权限或租户隔离；分析路径仍由可信本机用户指定，不能据此声称适合直接公开部署。
- 文件读取仍使用 [CodeReader](../../services/python-service/app/repository/reader.py) 的根目录边界、路径规范化和 Java/Python 后缀检查，没有改成任意文件下载。
- 索引仍属于单个 FastAPI 进程，重启需要重新分析；运行 Agent 时不要并发切换仓库。
- 静态路径不证明运行时执行，源码事实与模型推断仍分离；本地模型的格式错误与证据不足不会因删除网关而消失。

## 验证入口

- Python：在 `services/python-service` 运行 `python -m pytest -p no:cacheprovider`。
- 前端：在 `services/frontend` 运行 `npm test`、`npm run build`；包含真实本地 HTTP 代理的传输测试。
- 启动服务后，在前端目录运行 `npm run test:integration`，可通过 `REPOMIND_FRONTEND_URL` 指定地址。该脚本使用真实 Ollama 和浏览器，检查四个现有 Demo；结果和截图仅写入忽略的 `logs/gateway-removal-integration/`，任何场景失败均返回非零状态。需已安装 Edge，或设置 `REPOMIND_BROWSER_EXECUTABLE`。
- 企业 Java Demo：在 `demo/enterprise-order-showcase` 运行 `mvn test`。原网关控制器测试随模块移除，其 HTTP 契约由 Python 兼容层和 Vite 传输测试覆盖。
