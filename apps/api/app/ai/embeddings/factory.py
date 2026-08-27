from functools import lru_cache

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import get_settings


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    settings = get_settings()
    if settings.embedding_provider == "bge_m3":
        from app.ai.embeddings.local_bge import LocalBgeEmbeddingProvider

        return LocalBgeEmbeddingProvider()

    raise NotImplementedError(
        f"EMBEDDING_PROVIDER={settings.embedding_provider!r} is not implemented yet. "
        "Use EMBEDDING_PROVIDER=bge_m3 (local, default) until a cloud provider ships."
    )
