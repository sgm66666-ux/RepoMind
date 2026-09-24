from pathlib import Path
import asyncio

import httpx

from app.main import app, index


def test_health_endpoint() -> None:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request())
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analysis_and_symbol_endpoints(monkeypatch) -> None:
    for name in (
        "REPOMIND_LLM_PROVIDER",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "REPOMIND_LLM_BASE_URL",
        "REPOMIND_LLM_MODEL",
        "REPOMIND_LLM_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    index.sourceFiles.clear()
    index.symbols.clear()
    index.relations.clear()
    index.analysisReady = False
    demo_path = Path(__file__).parents[3] / "demo" / "order-demo"
    async def request() -> list[httpx.Response]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            responses = []
            responses.append(await client.get("/analysis/status"))
            responses.append(await client.post("/analysis/repository", json={"path": str(demo_path)}))
            responses.append(await client.get("/analysis/status"))
            responses.append(await client.get("/call-graph"))
            responses.append(await client.get("/demo/order-demo"))
            responses.append(await client.get("/symbols", params={"query": "OrderController.createOrder"}))
            controller = responses[-1].json()[0]
            responses.append(await client.get(f"/symbols/{controller['id']}"))
            responses.append(await client.get(f"/symbols/{controller['id']}/callees"))
            responses.append(await client.get("/files/read", params={"filePath": "OrderController.java", "startLine": 9, "endLine": 13}))
            responses.append(await client.post("/context", json={"symbolId": controller["id"], "maxSnippetLines": 10}))
            responses.append(await client.post("/fault-localization", json={"stackTrace": "java.lang.NullPointerException: stock is null\n    at demo.order.InventoryService.checkStock(InventoryService.java:12)"}))
            responses.append(await client.post("/agent/chat", json={"question": "trace", "maxSteps": 2}))
            return responses

    before, response, ready, graph, demo, symbols, detail, callees, file_read, context, fault, agent = asyncio.run(request())
    assert before.json()["analysisReady"] is False
    assert ready.json()["analysisReady"] is True
    assert ready.json()["repositoryPath"] == str(demo_path.resolve())
    assert response.status_code == 200
    body = response.json()
    assert body["symbolCount"] >= 8
    assert body["resolvedCallCount"] == 4
    assert body["languageBreakdown"] == {"JAVA": 6}
    assert graph.status_code == 200
    assert len(graph.json()["edges"]) == 4
    assert all(edge["resolved"] for edge in graph.json()["edges"])
    assert demo.status_code == 200
    assert "InventoryService.java:12" in demo.json()["stackTrace"]
    assert symbols.status_code == 200
    assert detail.status_code == 200
    assert callees.status_code == 200
    assert callees.json()[0]["symbol"]["qualifiedName"] == "demo.order.OrderService.createOrder"
    assert file_read.status_code == 200
    assert file_read.json()["filePath"] == "OrderController.java"
    assert context.status_code == 200
    assert context.json()["targetSymbol"]["qualifiedName"].endswith("OrderController.createOrder")
    assert fault.status_code == 200
    assert fault.json()["status"] == "LOCATED"
    assert agent.status_code == 503
