from app.modules.ingestion.chunking import build_chunks, estimate_tokens, normalize_text
from app.modules.ingestion.schemas import CanonicalBlock, CanonicalDocument, CanonicalPage


def _doc(*pages: CanonicalPage) -> CanonicalDocument:
    return CanonicalDocument(title="test", pages=list(pages))


def test_small_document_becomes_a_single_chunk() -> None:
    page = CanonicalPage(
        number=1,
        blocks=[
            CanonicalBlock(type="heading", text="Intro", level=1),
            CanonicalBlock(type="paragraph", text="A short paragraph."),
        ],
    )
    chunks = build_chunks(_doc(page), target_tokens=350, max_tokens=900)
    assert len(chunks) == 1
    assert chunks[0].heading_path == ["Intro"]
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1


def test_chunk_never_spans_a_block_it_hasnt_seen() -> None:
    # Regression guard: a chunk's text must be built only from block text
    # actually iterated, never truncated mid-block.
    page = CanonicalPage(
        number=1,
        blocks=[CanonicalBlock(type="paragraph", text="one two three four five")],
    )
    chunks = build_chunks(_doc(page), target_tokens=2, max_tokens=3)
    assert chunks[0].text == "one two three four five"


def test_heading_path_tracks_nesting_and_pops_on_sibling() -> None:
    pages = [
        CanonicalPage(
            number=1,
            blocks=[
                CanonicalBlock(type="heading", text="Chapter 3", level=1),
                CanonicalBlock(type="heading", text="3.2 Section", level=2),
                CanonicalBlock(type="paragraph", text="Body under 3.2."),
            ],
        ),
        CanonicalPage(
            number=2,
            blocks=[
                CanonicalBlock(type="heading", text="3.3 Section", level=2),
                CanonicalBlock(type="paragraph", text="Body under 3.3."),
            ],
        ),
    ]
    chunks = build_chunks(_doc(*pages), target_tokens=2, max_tokens=3)
    paths = [c.heading_path for c in chunks]
    assert ["Chapter 3", "3.2 Section"] in paths
    assert ["Chapter 3", "3.3 Section"] in paths


def test_chunk_splits_when_max_tokens_exceeded() -> None:
    page = CanonicalPage(
        number=1,
        blocks=[
            CanonicalBlock(type="paragraph", text="alpha beta gamma"),
            CanonicalBlock(type="paragraph", text="delta epsilon zeta"),
        ],
    )
    chunks = build_chunks(_doc(page), target_tokens=100, max_tokens=3)
    assert len(chunks) == 2
    assert chunks[0].text == "alpha beta gamma"
    assert chunks[1].text == "delta epsilon zeta"


def test_page_range_spans_multiple_pages_when_not_split() -> None:
    pages = [
        CanonicalPage(number=1, blocks=[CanonicalBlock(type="paragraph", text="short")]),
        CanonicalPage(number=2, blocks=[CanonicalBlock(type="paragraph", text="also short")]),
    ]
    chunks = build_chunks(_doc(*pages), target_tokens=100, max_tokens=200)
    assert len(chunks) == 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 2


def test_empty_document_produces_no_chunks() -> None:
    assert build_chunks(_doc()) == []


def test_estimate_tokens_counts_words() -> None:
    assert estimate_tokens("one two three") == 3
    assert estimate_tokens("") == 1  # never zero, avoids div-by-zero downstream


def test_normalize_text_collapses_whitespace_and_lowercases() -> None:
    assert normalize_text("  Hello   World \n\tFoo  ") == "hello world foo"
