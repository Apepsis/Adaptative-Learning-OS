from functools import lru_cache

from app.ai.providers.base import GenerationProvider
from app.core.config import get_settings
from app.core.exceptions import AIProviderError


@lru_cache
def get_generation_provider() -> GenerationProvider:
    settings = get_settings()
    if settings.ai_provider == "gemini":
        if not settings.gemini_api_key:
            raise AIProviderError(
                "GEMINI_API_KEY is not set. Get one at https://aistudio.google.com/apikey "
                "and set it in your .env file to enable chat."
            )
        from app.ai.providers.gemini import GeminiProvider

        return GeminiProvider(settings.gemini_api_key)

    raise NotImplementedError(
        f"AI_PROVIDER={settings.ai_provider!r} is not implemented yet. Use AI_PROVIDER=gemini."
    )
