"""HTTP contract tests replacing the removed gateway's forwarding tests."""

import asyncio
import json
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest
from fastapi import FastAPI

from app.browser_api import install_browser_api
from app.main import app, index


ROOT = Path(__file__).parents[3]


def run_requests(callback, target=app):
    async def run():
        transport = httpx.ASGITransport(app=target, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await callback(client)
    return asyncio.run(run())


@pytest.mark.parametrize("demo,qualified_name", [
    ("order-demo", "demo.order.InventoryService.checkStock"),
    ("enterprise-order-showcase", "com.repomind.showcase.domain.inventory.StockAllocator.allocate"),
])
def test_browser_routes_reuse_native_results_and_nested_symbol_ids(demo, qualified_name):
    async def check(client):
        body = {"path": str(ROOT / "demo" / demo)}
        native = await client.post("/analysis/repository", json=body)
        browser = await client.post("/api/repositories/analyze", json=body)
        assert native.status_code == browser.status_code == 200
        assert browser.json() == native.json()
        symbol = next(item for item in (await client.get("/api/symbols")).json()
                      if item["qualifiedName"] == qualified_name)
        symbol_id = quote(symbol["id"], safe="")
        for suffix in ("", "/callers", "/callees"):
            native = await client.get("/symbols/" + symbol_id + suffix)
            browser = await client.get("/api/symbols/" + symbol_id + suffix)
            assert native.status_code == browser.status_code == 200
            assert browser.json() == native.json()
        for path, params in [
            ("/symbols", {"qualifiedName": qualified_name}),
            ("/call-graph", {"includeUnresolved": "true"}),
            ("/files/read", {"filePath": symbol["filePath"], "startLine": 1, "endLine": 1}),
            ("/demo/order-demo", {}),
        ]:
            native = await client.get(path, params=params)
            browser = await client.get("/api" + path, params=params)
            assert native.status_code == browser.status_code == 200
            assert browser.json() == native.json()
        for path, payload in [
            ("/context", {"symbolId": symbol["id"]}),
            ("/fault-localization", {"stackTrace":
                f"java.lang.NullPointerException\n at {qualified_name}({Path(symbol['filePath']).name}:{symbol['startLine']})"}),
        ]:
            native = await client.post(path, json=payload)
            browser = await client.post("/api" + path, json=payload)
            assert native.status_code == browser.status_code == 200
            assert browser.json() == native.json()
        assert (await client.get("/health")).json() == {"status": "ok"}
        assert (await client.get("/api/health")).json() == {"status": "ok", "service": "python-service"}
    run_requests(check)


@pytest.mark.parametrize("method,path,payload,status", [
    ("POST", "/repositories/analyze", {}, 422),
    ("POST", "/repositories/analyze", {"path": str(ROOT / "does-not-exist")}, 400),
    ("GET", "/symbols/missing-symbol", None, 404),
    ("GET", "/call-graph", None, 409),
    ("POST", "/agent/chat", {"question": "Trace createOrder"}, 503),
])
def test_browser_errors_keep_gateway_envelope_and_native_detail(monkeypatch, method, path, payload, status):
    import app.main as main
    monkeypatch.setattr(main, "create_llm_provider", lambda: None)
    monkeypatch.setattr(index, "repositoryPath", None)
    async def check(client):
        kwargs = {"json": payload} if payload is not None else {}
        native_path = "/analysis/repository" if path == "/repositories/analyze" else path
        native = await client.request(method, native_path, **kwargs)
        browser = await client.request(method, "/api" + path, **kwargs)
        assert native.status_code == browser.status_code == status
        assert browser.json()["error"] == "PYTHON_SERVICE_ERROR"
        detail = native.json()["detail"]
        message = browser.json()["message"]
        assert (message if isinstance(detail, str) else json.loads(message)) == detail
    run_requests(check)


def test_browser_file_access_keeps_repository_boundary():
    index.analyze(ROOT / "demo/order-demo")
    async def check(client):
        for path in ("../README.md", str(ROOT / "README.md"), ".git/config"):
            response = await client.get("/api/files/read", params={"filePath": path})
            assert response.status_code == 400
            assert response.json()["error"] == "PYTHON_SERVICE_ERROR"
    run_requests(check)


def test_explicit_cors_origins_and_sanitized_internal_error(monkeypatch):
    monkeypatch.setenv("REPOMIND_FRONTEND_ORIGINS", "http://127.0.0.1:5173")
    isolated = FastAPI()
    def fail():
        raise RuntimeError("private failure details")
    isolated = install_browser_api(isolated, [("GET", "/failure", fail)])
    async def check(client):
        headers = {"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST"}
        allowed = await client.options("/api/repositories/analyze", headers=headers)
        assert allowed.status_code == 200
        assert allowed.headers["access-control-allow-origin"] == headers["Origin"]
        denied = await client.options("/api/health", headers={**headers, "Origin": "https://untrusted.example"})
        assert denied.status_code == 400
        assert "access-control-allow-origin" not in denied.headers
        response = await client.get("/api/failure", headers={"Origin": headers["Origin"]})
        assert response.status_code == 500
        assert response.json() == {"error": "INTERNAL_ERROR", "message": "Unexpected server error"}
        assert response.headers["access-control-allow-origin"] == headers["Origin"]
    run_requests(check, isolated)
