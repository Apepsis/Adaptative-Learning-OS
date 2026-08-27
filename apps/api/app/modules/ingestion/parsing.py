"""Turns raw per-page extracted text into CanonicalPage blocks.

Plain-text extraction (pypdf) gives us a stream of lines with no
structural markup, so headings have to be recovered heuristically:
numbered headings ("3.2 Projectile Motion"), "Chapter/Unit/Topic N", or
short Title-Case lines that don't end in sentence punctuation. Everything
else is merged into paragraph blocks, joining consecutive body lines
until a heading or a blank line breaks the run.

This intentionally does not try to be a full layout analyzer — that's
what Docling/PaddleOCR are for in a later phase, once scanned/complex
documents are in scope (see docs/adr/0002-lightweight-native-pdf-parser.md).
"""

import re

from app.modules.ingestion.schemas import CanonicalBlock, CanonicalPage

_NUMBERED_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+\S")
_SENTENCE_END_RE = re.compile(r"[.!?:;,]\s*$")
_MAX_HEADING_LENGTH = 90
_MAX_HEADING_WORDS = 12
_TITLE_CASE_RATIO_THRESHOLD = 0.8


def _looks_like_heading(line: str) -> tuple[bool, int]:
    """Returns (is_heading, level). Level 1 is top-level, higher nests deeper."""
    if not line or len(line) > _MAX_HEADING_LENGTH:
        return False, 0

    numbered = _NUMBERED_HEADING_RE.match(line)
    if numbered:
        level = numbered.group(1).count(".") + 1
        return True, level

    if line.lower().startswith(("chapter ", "unit ", "topic ")):
        return True, 1

    if _SENTENCE_END_RE.search(line):
        return False, 0

    words = line.split()
    if not words:
        return False, 0

    def _is_titleish(word: str) -> bool:
        return word[0].isupper() or not word[0].isalpha()

    title_case_ratio = sum(_is_titleish(w) for w in words) / len(words)
    if title_case_ratio >= _TITLE_CASE_RATIO_THRESHOLD and len(words) <= _MAX_HEADING_WORDS:
        return True, 2

    return False, 0


def parse_page_text(page_number: int, raw_text: str) -> CanonicalPage:
    blocks: list[CanonicalBlock] = []
    paragraph_buffer: list[str] = []

    def flush_paragraph() -> None:
        if paragraph_buffer:
            blocks.append(CanonicalBlock(type="paragraph", text=" ".join(paragraph_buffer)))
            paragraph_buffer.clear()

    for raw_line in raw_text.split("\n"):
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            continue
        is_heading, level = _looks_like_heading(line)
        if is_heading:
            flush_paragraph()
            blocks.append(CanonicalBlock(type="heading", text=line, level=level))
        else:
            paragraph_buffer.append(line)

    flush_paragraph()
    return CanonicalPage(number=page_number, blocks=blocks)
