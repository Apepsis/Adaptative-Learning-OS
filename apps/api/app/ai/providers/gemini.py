"""Gemini generation provider. API usage verified against the installed
`google-genai` SDK during development: `client.aio.models.generate_content(
model=..., contents=..., config=types.GenerateContentConfig(system_instruction=...))`,
`response.text`, structured output via `response_schema` + `response_mime_type=
"application/json"`, and `response.parsed` (declared field: "First candidate
from the parsed response if response_schema is provided") are the real,
current API shape — confirmed by introspecting the installed package, not
guessed.
"""

from google import genai
from google.genai import errors, types

from app.ai.providers.base import SchemaT
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

    async def generate_structured(
        self, *, system_instruction: str, user_message: str, model: str, response_schema: type[SchemaT]
    ) -> SchemaT:
        try:
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
        except errors.APIError as exc:
            raise AIProviderError(f"Gemini request failed: {exc}") from exc

        parsed = response.parsed
        if parsed is None:
            raise AIProviderError("Gemini did not return a response matching the requested schema")
        if not isinstance(parsed, response_schema):
            # Defensive: the SDK's declared type is broader (BaseModel | dict
            # | Enum); a mismatch here means the model deviated from the
            # schema in a way the SDK couldn't coerce.
            raise AIProviderError(
                f"Gemini's structured response was not a {response_schema.__name__}: {type(parsed)}"
            )
        return parsed
