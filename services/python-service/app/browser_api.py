"""Browser-facing transport compatibility; code intelligence stays in native handlers."""

import json
import os
from collections.abc import Callable

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException


def install_browser_api(app: FastAPI, routes: list[tuple[str, str, Callable]]) -> CORSMiddleware:
    origins = os.getenv(
        "REPOMIND_FRONTEND_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    @app.get("/api/health")
    def browser_health() -> dict[str, str]:
        return {"status": "ok", "service": "python-service"}

    for method, path, handler in routes:
        app.add_api_route("/api" + path, handler, methods=[method])

    def service_error(detail: object, status: int, headers: dict | None = None) -> JSONResponse:
        message = detail if isinstance(detail, str) else json.dumps(
            jsonable_encoder(detail), ensure_ascii=False, separators=(",", ":")
        )
        return JSONResponse(
            status_code=status, content={"error": "PYTHON_SERVICE_ERROR", "message": message},
            headers=headers,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        if request.url.path.startswith("/api/"):
            return service_error(exc.detail, exc.status_code, exc.headers)
        return await http_exception_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        if request.url.path.startswith("/api/"):
            return service_error(exc.errors(), 422)
        return await request_validation_exception_handler(request, exc)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=500, content={
                "error": "INTERNAL_ERROR", "message": "Unexpected server error",
            })
        return PlainTextResponse("Internal Server Error", status_code=500)

    # Wrap ServerErrorMiddleware too, so allowed origins receive CORS headers
    # on sanitized unexpected errors as well as ordinary handler responses.
    return CORSMiddleware(
        app,
        allow_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
