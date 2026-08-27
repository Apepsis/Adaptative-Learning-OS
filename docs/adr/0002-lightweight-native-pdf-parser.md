# ADR 0002: pypdf (not Docling) for the first native-text PDF parser

## Context

The blueprint (section 5.4) names Docling as the primary parser, and its
own Phase 2 vertical-slice prompt (section 48) explicitly writes the
pipeline as `PDF -> Docling -> canonical blocks -> ...`, scoped to
native-text PDF only, OCR explicitly excluded from this first slice.

Docling is a much heavier dependency than plain text extraction: it pulls
in its own layout-analysis ML models even for documents that don't need
OCR, adds real weight and build time to the API Docker image, and its
richer structural output (reading order, table/formula detection) isn't
needed for a slice that is deliberately restricted to "extract text and
approximate headings from a native-text PDF."

## Decision

For this first ingestion slice, parse native-text PDFs with `pypdf`
(per-page `extract_text()`) plus a small heuristic in
`app/modules/ingestion/parsing.py` that recovers heading structure from
plain line-based text (numbered headings, "Chapter/Unit/Topic N", short
Title-Case lines). This is verified against a real generated fixture PDF
(`app/tests/fixtures/kinematics.pdf`) with matching unit tests in
`app/tests/modules/ingestion/`.

The **Canonical Document Representation** (blueprint section 8.4) is
unchanged, and `app/modules/ingestion/parsers/base.py` defines a
`DocumentParser` protocol — nothing downstream of parsing knows or cares
which concrete parser produced a `CanonicalDocument`. Docling (or
PaddleOCR, for scanned pages) can be added later as an alternative
`DocumentParser` implementation without touching chunking, embedding,
retrieval, or the API contract.

## Alternatives considered

- **Docling now, as named.** Rejected for this slice: meaningfully larger
  Docker image and slower builds, and its API surface (structural
  block/table iteration) could not be verified here without the ability
  to run it, which is a real risk for code nobody has executed. Plain
  `pypdf` text extraction was actually run against a generated fixture PDF
  during development, which pypdf handles reliably and simply.
- **MinerU.** Explicitly out of scope per blueprint section 5.4 (its own
  license terms need review before wider use) and section 41
  (`ENABLE_MINERU=false` by default).

## Consequences

- Heading/paragraph structure is a heuristic over plain text, not a real
  layout analysis — it will occasionally misclassify a heading or merge
  paragraphs pypdf didn't separate with a blank line. Acceptable for this
  slice: retrieval only needs page-accurate, structurally-reasonable
  chunks, not pixel-perfect layout.
- No OCR, no scanned-PDF support, no table/formula extraction yet
  (blueprint sections 8.6, matches its explicit "no OCR" scoping for this
  slice). DOCX/PPTX/image sources uploaded in Phase 1 remain marked
  `UNSUPPORTED` by the ingestion pipeline until a later slice adds parsers
  for them.
- `apps/api/pyproject.toml` does not depend on `docling`. Adding it later
  is additive (a new parser module + a config flag to select it), not a
  breaking change to this ADR's decision.

## Rollback

Add `app/modules/ingestion/parsers/docling_parser.py` implementing the
same `DocumentParser` protocol, and switch which parser
`app/workers/tasks/ingestion.py` instantiates (ideally behind a
feature flag, e.g. `ENABLE_DOCLING_PARSER`, so both remain available). No
changes needed to chunking, embeddings, retrieval, the DB schema, or the
API contract.
