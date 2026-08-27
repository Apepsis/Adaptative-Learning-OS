from pathlib import Path
from typing import Protocol

from app.modules.ingestion.schemas import CanonicalDocument


class DocumentParser(Protocol):
    """Every parser produces a CanonicalDocument (blueprint section 8.4).

    Nothing outside this package should know which concrete parser ran —
    that's the whole point of the canonical representation.
    """

    name: str
    version: str

    def parse(self, file_path: Path, *, title: str) -> CanonicalDocument: ...
