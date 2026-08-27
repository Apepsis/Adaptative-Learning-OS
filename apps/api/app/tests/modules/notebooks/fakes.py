"""Fake AI providers for fast tests. Real embedding/generation correctness
is covered separately (app/tests/modules/retrieval/test_search_slow.py for
embeddings; there is no live-Gemini test since that needs a real API key
and would make network calls in CI). These fakes only need to satisfy the
provider protocols well enough to exercise the chat/retrieval plumbing —
request → chunks found → prompt built → response persisted with citations.
"""


class FakeEmbeddingProvider:
    """Returns a constant vector. Vector search becomes semantically
    meaningless with this fake (everything ties), but lexical (FTS) search
    still ranks on real keyword matches, so chat's citation must still land
    on the right, real chunk in these tests."""

    dimension = 1024

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self.dimension for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1] * self.dimension


class FakeGenerationProvider:
    def __init__(self, response: str = "This is a fake grounded answer.") -> None:
        self.response = response
        self.calls: list[dict] = []

    async def generate(self, *, system_instruction: str, user_message: str, model: str) -> str:
        self.calls.append(
            {"system_instruction": system_instruction, "user_message": user_message, "model": model}
        )
        return self.response
