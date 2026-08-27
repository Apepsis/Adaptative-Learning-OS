import base64
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.main import app as fastapi_app

_MINIMAL_PDF = b"%PDF-1.4\n%%EOF\n"
_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.mark.asyncio
async def test_upload_pdf_succeeds_and_enqueues_ingestion(client: AsyncClient) -> None:
    files = {"file": ("lecture-notes.pdf", _MINIMAL_PDF, "application/pdf")}

    with patch("app.modules.sources.service.ingest_source_task") as mock_task:
        response = await client.post("/v1/sources/upload", files=files)

    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "UPLOADED"
    assert body["type"] == "pdf"
    assert body["mime_type"] == "application/pdf"

    mock_task.delay.assert_called_once_with(body["id"])


@pytest.mark.asyncio
async def test_upload_duplicate_file_is_rejected(client: AsyncClient) -> None:
    files = {"file": ("notes.pdf", _MINIMAL_PDF, "application/pdf")}
    with patch("app.modules.sources.service.ingest_source_task"):
        first = await client.post("/v1/sources/upload", files=files)
    assert first.status_code == 202

    files_again = {"file": ("notes-renamed.pdf", _MINIMAL_PDF, "application/pdf")}
    with patch("app.modules.sources.service.ingest_source_task"):
        second = await client.post("/v1/sources/upload", files=files_again)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_upload_rejects_mismatched_extension(client: AsyncClient) -> None:
    """A PNG's real bytes with a spoofed .pdf filename/content-type must be
    caught by MIME sniffing, not trusted from the client."""
    files = {"file": ("totally-a-pdf.pdf", _ONE_PIXEL_PNG, "application/pdf")}

    response = await client.post("/v1/sources/upload", files=files)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_mime_type(client: AsyncClient) -> None:
    files = {"file": ("archive.zip", b"PK\x03\x04fake-zip-bytes", "application/zip")}

    response = await client.post("/v1/sources/upload", files=files)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(client: AsyncClient) -> None:
    tiny_settings = get_settings().model_copy(update={"max_upload_mb": 1})
    fastapi_app.dependency_overrides[get_settings] = lambda: tiny_settings
    try:
        oversized_content = _MINIMAL_PDF + b"0" * (2 * 1024 * 1024)
        files = {"file": ("huge.pdf", oversized_content, "application/pdf")}
        with patch("app.modules.sources.service.ingest_source_task"):
            response = await client.post("/v1/sources/upload", files=files)
    finally:
        fastapi_app.dependency_overrides.pop(get_settings, None)

    assert response.status_code == 413
