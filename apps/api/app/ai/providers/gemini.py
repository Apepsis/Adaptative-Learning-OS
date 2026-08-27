"""Gemini generation provider. API usage verified against the installed
`google-genai` SDK during development: `client.aio.models.generate_content(
model=..., contents=..., config=types.GenerateContentConfig(system_instruction=...))`
and `response.text` are the real, current API shape, not guessed.
"""

from google import genai
from google.genai import errors, types

from app.core.exceptions import AIProviderError


class GeminiProvider:
    """Implements app.ai.providers.base.GenerationProvider structurally."""

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    async def generate(self, *, system_instruction: str, user_message: str, model: str) -> str:
        try:
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=user_message,
                config=types.GenerateContentConfig(system_instruction=system_instruction),
            )
        except errors.APIError as exc:
            raise AIProviderError(f"Gemini request failed: {exc}") from exc

        if not response.text:
            raise AIProviderError("Gemini returned an empty response")
        return response.text
