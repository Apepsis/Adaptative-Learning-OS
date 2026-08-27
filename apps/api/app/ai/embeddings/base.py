from typing import Protocol


class EmbeddingProvider(Protocol):
    """Model-agnostic embedding interface (blueprint section 21.1) — the
    rest of the domain never imports a specific provider directly, only
    this protocol, resolved via app.ai.embeddings.factory."""

    dimension: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...
