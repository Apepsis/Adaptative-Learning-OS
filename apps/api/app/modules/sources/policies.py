from app.core.exceptions import PayloadTooLargeError, ValidationFailedError

# Real (sniffed) MIME type -> canonical source type + typical extensions.
# Extension is only used to flag an obvious mismatch for the user; the
# sniffed MIME type is always the source of truth for what actually gets
# processed (never trust a client-supplied Content-Type or filename alone).
_MIME_TO_SOURCE_TYPE: dict[str, str] = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "image/png": "image",
    "image/jpeg": "image",
    "image/webp": "image",
}

_MIME_TO_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "application/pdf": (".pdf",),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (".docx",),
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": (".pptx",),
    "image/png": (".png",),
    "image/jpeg": (".jpg", ".jpeg"),
    "image/webp": (".webp",),
}


def resolve_source_type(mime_type: str) -> str:
    source_type = _MIME_TO_SOURCE_TYPE.get(mime_type)
    if source_type is None:
        raise ValidationFailedError(f"Unsupported file type: {mime_type}")
    return source_type


def validate_mime_allowed(mime_type: str, allowed_mime_types: list[str]) -> None:
    if mime_type not in allowed_mime_types:
        raise ValidationFailedError(f"Unsupported file type: {mime_type}")


def validate_extension_matches_mime(filename: str | None, mime_type: str) -> None:
    if not filename or "." not in filename:
        return
    extension = filename[filename.rfind(".") :].lower()
    expected = _MIME_TO_EXTENSIONS.get(mime_type)
    if expected is not None and extension not in expected:
        raise ValidationFailedError(
            f"File extension '{extension}' does not match detected file type '{mime_type}'"
        )


def extension_for_mime(mime_type: str) -> str:
    extensions = _MIME_TO_EXTENSIONS.get(mime_type)
    return extensions[0] if extensions else ""


def validate_size(size_bytes: int, max_bytes: int) -> None:
    if size_bytes <= 0:
        raise ValidationFailedError("Uploaded file is empty")
    if size_bytes > max_bytes:
        raise PayloadTooLargeError(
            f"File is {size_bytes} bytes, which exceeds the {max_bytes} byte limit"
        )
