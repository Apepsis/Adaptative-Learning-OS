class DomainError(Exception):
    """Base class for errors raised by service-layer code."""


class NotFoundError(DomainError):
    """Requested entity does not exist, or is not owned by the caller."""


class ConflictError(DomainError):
    """The request conflicts with existing state (e.g. duplicate upload)."""


class ValidationFailedError(DomainError):
    """The request failed a domain validation rule (e.g. disallowed MIME type)."""


class PayloadTooLargeError(DomainError):
    """The uploaded payload exceeds the configured size limit."""


class AIProviderError(DomainError):
    """A configured AI provider is missing config (e.g. no API key) or its
    call failed. Maps to 502 — the request was valid, an upstream
    dependency wasn't."""
