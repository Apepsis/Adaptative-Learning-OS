"""Local BGE-M3 embeddings (blueprint sections 5.6, 9.4): zero marginal
cost, no data leaves the machine. First use downloads the model (~2GB)
from Hugging Face, which needs internet access once; after that it's
fully offline. CPU inference is slow but workable for personal use.
"""

import threading

import structlog

logger = structlog.get_logger("ai.embeddings.local_bge")

_DEFAULT_MODEL_NAME = "BAAI/bge-m3"
_DIMENSION = 1024


class LocalBgeEmbeddingProvider:
    """Implements app.ai.embeddings.base.EmbeddingProvider structurally
    (no inheritance needed — it's a Protocol)."""

    dimension = _DIMENSION

    def __init__(self, model_name: str = _DEFAULT_MODEL_NAME) -> None:
        self._model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _ensure_loaded(self):  # noqa: ANN202 - returns the lazily-imported model type
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("embeddings.loading_model", model=self._model_name)
                self._model = SentenceTransformer(self._model_name)
                logger.info("embeddings.model_ready", model=self._model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_loaded()
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [vector.tolist() for vector in embeddings]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
