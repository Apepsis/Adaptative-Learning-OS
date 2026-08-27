"""Request-scoped observability.

This is intentionally lightweight: a request-id + latency logging middleware.
Full distributed tracing (OpenTelemetry SDK, exporters, sampling policy) is
Phase 12 (Hardening) scope per docs/architecture/roadmap.md and should not be
half-wired in earlier phases.
"""

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response

logger = structlog.get_logger("http")


def configure_telemetry(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        response.headers["x-request-id"] = request_id
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response
