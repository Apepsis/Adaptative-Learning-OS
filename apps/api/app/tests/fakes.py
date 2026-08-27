"""Fake AI providers shared across test modules (notebooks, curriculum).

Real embedding/generation correctness is covered separately
(app/tests/modules/retrieval/test_search_slow.py for embeddings; there is
no live-Gemini test since that needs a real API key and would make real
network calls in CI). These fakes only need to satisfy the provider
protocols well enough to exercise plumbing — request -> real DB/parser ->
prompt built -> response persisted — without a 2GB model or a live key.
"""

from typing import TypeVar

from pydantic import BaseModel

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class FakeEmbeddingProvider:
    """Returns a constant vector. Vector search becomes semantically
    meaningless with this fake (everything ties), but lexical (FTS) search
    still ranks on real keyword matches, so a real chunk must still surface
    correctly in these tests."""

    dimension = 1024

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self.dimension for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1] * self.dimension


class FakeGenerationProvider:
    def __init__(self, response: str = "This is a fake grounded answer.") -> None:
        self.response = response
        self.structured_response: BaseModel | None = None
        self.calls: list[dict] = []
        self.structured_calls: list[dict] = []

    async def generate(self, *, system_instruction: str, user_message: str, model: str) -> str:
        self.calls.append(
            {"system_instruction": system_instruction, "user_message": user_message, "model": model}
        )
        return self.response

    async def generate_structured(
        self, *, system_instruction: str, user_message: str, model: str, response_schema: type[SchemaT]
    ) -> SchemaT:
        self.structured_calls.append(
            {
                "system_instruction": system_instruction,
                "user_message": user_message,
                "model": model,
                "response_schema": response_schema,
            }
        )
        if self.structured_response is None:
            raise AssertionError(
                "FakeGenerationProvider.structured_response must be set before calling generate_structured"
            )
        if not isinstance(self.structured_response, response_schema):
            raise AssertionError(
                f"structured_response is {type(self.structured_response)}, test expected {response_schema}"
            )
        return self.structured_response
