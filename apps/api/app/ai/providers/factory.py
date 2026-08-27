from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel

from app.ai.providers.base import GenerationProvider
from app.core.config import get_settings
from app.core.exceptions import AIProviderError

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class _UnconfiguredProvider:
    """Stands in for a real provider when no API key is set. Callers that
    never actually need generation (blueprint 14.2: MCQ/numeric grading is
    LLM-free) can hold this without error — it only raises once a caller
    tries to actually generate something, e.g. short-answer grading or
    error classification on a wrong answer."""

    def __init__(self, message: str) -> None:
        self._message = message

    async def generate(self, *, system_instruction: str, user_message: str, model: str) -> str:
        raise AIProviderError(self._message)

    async def generate_structured(
        self, *, system_instruction: str, user_message: str, model: str, response_schema: type[SchemaT]
    ) -> SchemaT:
        raise AIProviderError(self._message)


@lru_cache
def get_generation_provider() -> GenerationProvider:
    settings = get_settings()
    if settings.ai_provider == "gemini":
        if not settings.gemini_api_key:
            return _UnconfiguredProvider(
                "GEMINI_API_KEY is not set. Get one at https://aistudio.google.com/apikey "
                "and set it in your .env file to enable AI features."
            )
        from app.ai.providers.gemini import GeminiProvider

        return GeminiProvider(settings.gemini_api_key)

    raise NotImplementedError(
        f"AI_PROVIDER={settings.ai_provider!r} is not implemented yet. Use AI_PROVIDER=gemini."
    )
