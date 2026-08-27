"""Canonical Document Representation (blueprint section 8.4).

Every parser must produce this shape, regardless of the underlying library
(pypdf today; Docling/PaddleOCR are documented future upgrades — see
docs/adr/0002-lightweight-native-pdf-parser.md). Nothing downstream of
parsing should ever import a parser-specific type.
"""

from typing import Literal

from pydantic import BaseModel

BlockType = Literal["heading", "paragraph"]


class CanonicalBlock(BaseModel):
    type: BlockType
    text: str
    level: int = 0  # heading nesting level; 0 for non-headings


class CanonicalPage(BaseModel):
    number: int
    blocks: list[CanonicalBlock]


class CanonicalDocument(BaseModel):
    title: str
    language: str = "en"
    pages: list[CanonicalPage]


class ChunkDraft(BaseModel):
    """Output of chunking, before embedding/persistence."""

    text: str
    heading_path: list[str]
    page_start: int
    page_end: int
    token_count: int
