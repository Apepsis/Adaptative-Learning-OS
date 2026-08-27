from typing import Protocol


class GenerationProvider(Protocol):
    """Model-agnostic text generation interface (blueprint section 21.1) —
    services call this, never a specific vendor SDK directly."""

    async def generate(self, *, system_instruction: str, user_message: str, model: str) -> str: ...
