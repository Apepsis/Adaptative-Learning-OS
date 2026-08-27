"""Groups CanonicalPage blocks into retrieval chunks (blueprint section 9).

Respects structure — a chunk never splits mid-block — and tracks the
heading path and page range each chunk came from, which is what makes
citations possible. Token counts are a word-count approximation, good
enough for sizing decisions; exactness isn't required (section 9.2's
350-900 token target is itself a guideline, not a hard contract).
"""

import re

from app.modules.ingestion.schemas import CanonicalDocument, ChunkDraft

DEFAULT_TARGET_TOKENS = 350
DEFAULT_MAX_TOKENS = 900
_HEADING_FLUSH_RATIO = 0.4  # start a new chunk on heading only if buffer is reasonably full
_WHITESPACE_RE = re.compile(r"\s+")


def estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def normalize_text(text: str) -> str:
    """Feeds both the lexical index (fts) and de-duplication comparisons."""
    return _WHITESPACE_RE.sub(" ", text).strip().lower()


def build_chunks(
    document: CanonicalDocument,
    *,
    target_tokens: int = DEFAULT_TARGET_TOKENS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> list[ChunkDraft]:
    chunks: list[ChunkDraft] = []
    heading_stack: list[tuple[int, str]] = []

    buffer_text: list[str] = []
    buffer_tokens = 0
    buffer_page_start: int | None = None
    buffer_page_end: int | None = None
    buffer_heading_path: list[str] = []

    def current_path() -> list[str]:
        return [text for _, text in heading_stack]

    def flush() -> None:
        nonlocal buffer_text, buffer_tokens, buffer_page_start, buffer_page_end
        if buffer_text:
            chunks.append(
                ChunkDraft(
                    text="\n\n".join(buffer_text),
                    heading_path=list(buffer_heading_path),
                    page_start=buffer_page_start or 1,
                    page_end=buffer_page_end or buffer_page_start or 1,
                    token_count=buffer_tokens,
                )
            )
        buffer_text = []
        buffer_tokens = 0
        buffer_page_start = None
        buffer_page_end = None

    for page in document.pages:
        for block in page.blocks:
            if block.type == "heading":
                if buffer_tokens >= target_tokens * _HEADING_FLUSH_RATIO:
                    flush()
                while heading_stack and heading_stack[-1][0] >= block.level:
                    heading_stack.pop()
                heading_stack.append((block.level, block.text))
                # Only re-anchor the path if the buffer is empty (just
                # flushed, or nothing accumulated yet). If it didn't flush
                # above, the buffer still holds text from *before* this
                # heading — relabeling it to the new heading here would
                # mislabel every chunk it's eventually flushed under.
                if not buffer_text:
                    buffer_heading_path = current_path()
                continue

            block_tokens = estimate_tokens(block.text)
            if buffer_text and buffer_tokens + block_tokens > max_tokens:
                flush()
                buffer_heading_path = current_path()
            elif not buffer_text:
                buffer_heading_path = current_path()

            buffer_text.append(block.text)
            buffer_tokens += block_tokens
            buffer_page_start = buffer_page_start or page.number
            buffer_page_end = page.number

            if buffer_tokens >= target_tokens:
                flush()
                buffer_heading_path = current_path()

    flush()
    return chunks
