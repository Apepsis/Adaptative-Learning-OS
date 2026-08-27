"""Native-text PDF parser (blueprint section 8.5's fast path).

Deliberately does not attempt OCR or scanned-page detection — a page that
extracts to empty/near-empty text just produces an empty page in the
canonical document. That gap is closed in a later phase once an OCR
fallback exists (blueprint section 8.6); see
docs/adr/0002-lightweight-native-pdf-parser.md for why this parser is
pypdf rather than Docling for this first slice.
"""

from pathlib import Path

from pypdf import PdfReader

from app.modules.ingestion.parsing import parse_page_text
from app.modules.ingestion.schemas import CanonicalDocument


class PyPdfParser:
    name = "pypdf"
    version = "1"

    def parse(self, file_path: Path, *, title: str) -> CanonicalDocument:
        reader = PdfReader(str(file_path))
        pages = [
            parse_page_text(page_number, page.extract_text() or "")
            for page_number, page in enumerate(reader.pages, start=1)
        ]
        return CanonicalDocument(title=title, pages=pages)
