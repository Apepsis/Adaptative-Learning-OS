import asyncio

import redis.asyncio as redis_asyncio
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    ValidationFailedError,
)
from app.core.logging import configure_logging
from app.core.telemetry import configure_telemetry
from app.db.session import get_engine
from app.modules.identity.router import router as identity_router
from app.modules.retrieval.router import router as retrieval_router
from app.modules.sources.router import router as sources_router
from app.modules.subjects.router import router as subjects_router
from app.storage.client import get_storage_client

settings = get_settings()
configure_logging(settings.app_env)

app = FastAPI(title="Adaptive Learning OS API", version="0.1.0")

configure_telemetry(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_response(status_code: int, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def _not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
    return _error_response(status.HTTP_404_NOT_FOUND, exc)


@app.exception_handler(ConflictError)
async def _conflict_handler(_request: Request, exc: ConflictError) -> JSONResponse:
    return _error_response(status.HTTP_409_CONFLICT, exc)


@app.exception_handler(ValidationFailedError)
async def _validation_handler(_request: Request, exc: ValidationFailedError) -> JSONResponse:
    return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, exc)


@app.exception_handler(PayloadTooLargeError)
async def _too_large_handler(_request: Request, exc: PayloadTooLargeError) -> JSONResponse:
    return _error_response(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, exc)


app.include_router(identity_router)
app.include_router(subjects_router)
app.include_router(sources_router)
app.include_router(retrieval_router)


@app.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def health_ready() -> dict[str, str]:
    checks: dict[str, str] = {}

    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001 - readiness probe reports, never crashes
        checks["database"] = f"error: {exc}"

    try:
        client = redis_asyncio.from_url(settings.redis_url)
        try:
            await asyncio.wait_for(client.ping(), timeout=3)
            checks["redis"] = "ok"
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"

    try:
        await get_storage_client().list_buckets()
        checks["object_storage"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["object_storage"] = f"error: {exc}"

    if all(value == "ok" for value in checks.values()):
        return {"status": "ok", **checks}

    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=checks)
