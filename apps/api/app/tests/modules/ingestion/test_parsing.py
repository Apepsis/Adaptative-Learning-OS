from app.modules.ingestion.parsing import parse_page_text


def test_numbered_heading_is_detected_with_correct_level() -> None:
    page = parse_page_text(1, "3.2 Projectile Motion\nSome body text here.")
    assert page.blocks[0].type == "heading"
    assert page.blocks[0].text == "3.2 Projectile Motion"
    assert page.blocks[0].level == 2


def test_chapter_prefix_is_a_level_one_heading() -> None:
    page = parse_page_text(1, "Chapter 3: Kinematics\nBody text.")
    assert page.blocks[0].type == "heading"
    assert page.blocks[0].level == 1


def test_sentence_ending_line_is_never_a_heading() -> None:
    page = parse_page_text(1, "This Is A Short Title-Case Sentence.")
    assert page.blocks[0].type == "paragraph"


def test_consecutive_body_lines_merge_into_one_paragraph() -> None:
    page = parse_page_text(
        1,
        "This is the first line of a paragraph\nand this continues it\nand so does this.",
    )
    assert len(page.blocks) == 1
    assert page.blocks[0].type == "paragraph"
    assert page.blocks[0].text == (
        "This is the first line of a paragraph and this continues it and so does this."
    )


def test_blank_line_breaks_a_paragraph_into_two_blocks() -> None:
    page = parse_page_text(1, "First paragraph text here.\n\nSecond paragraph text here.")
    paragraphs = [b for b in page.blocks if b.type == "paragraph"]
    assert len(paragraphs) == 2


def test_heading_interrupts_and_restarts_paragraph_buffering() -> None:
    page = parse_page_text(1, "Intro text before heading.\n3.3 Range of a Projectile\nBody after heading.")
    assert [b.type for b in page.blocks] == ["paragraph", "heading", "paragraph"]


def test_empty_page_produces_no_blocks() -> None:
    page = parse_page_text(1, "")
    assert page.blocks == []


def test_page_number_is_preserved() -> None:
    page = parse_page_text(7, "Chapter 1\nBody.")
    assert page.number == 7
