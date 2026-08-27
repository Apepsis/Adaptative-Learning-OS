# Roadmap

Full architecture: [`blueprint.md`](blueprint.md). This file tracks what's
actually built versus what's next, so a new session (human or Claude Code)
can tell at a glance where the project stands.

**Rule (blueprint Risk R1):** never build a later phase speculatively.
Finish a phase's Definition of Done, update this file, then move to the
next one.

## Status

| Phase | Name | Status |
| ----- | ---- | ------ |
| 0 | Repository foundation | ✅ Done |
| 1 | Library (source upload) | ✅ Done |
| 2 | Parsing + search (native PDF, chunks, embeddings, hybrid retrieval) | ✅ Done |
| 3 | Notebook Mode (grounded chat over sources) | ⬜ Not started |
| 4 | Curriculum Builder (concept graph) | ⬜ Not started |
| 5 | Learn UI (lessons, flashcards, definitions) | ⬜ Not started |
| 6 | Question Bank + basic practice | ⬜ Not started |
| 7 | Learner Model (BKT, FSRS, error patterns) | ⬜ Not started |
| 8 | Planner v1 (OR-Tools) | ⬜ Not started |
| 9 | Adaptive loop (nightly replanning, stability horizon) | ⬜ Not started |
| 10 | Advanced/olympiad (L0-L5, transfer, STEM verification) | ⬜ Not started |
| 11 | Integrations (Google Calendar, web/YouTube ingestion) | ⬜ Not started |
| 12 | Hardening (security, evals, backups, observability) | ⬜ Not started |

**MVP scope** (blueprint section 43) is Phases 0-5 plus basic practice
from Phase 6. Everything else is deliberately deferred.

## What Phase 0 + 1 actually built

- Modular-monolith FastAPI backend (`apps/api/app`) with `identity`,
  `subjects`, and `sources` modules, each following
  `router -> service -> repository -> models`.
- `LOCAL_SINGLE_USER` auth shortcut (blueprint section 27) — every entity
  is still scoped by `user_id` so real auth can drop in later without a
  data model change.
- PostgreSQL with an Alembic migration for `users`, `subjects`, `sources`.
- MinIO-backed object storage with streamed SHA-256 hashing, MIME
  sniffing (not trusting client-supplied extension/content-type), size
  limits, and duplicate detection.
- Next.js frontend (`apps/web`) with Home (API readiness indicator),
  Library (list/upload/detail with status polling), and Subjects
  (list/create).
- Backend tests (pytest, real Postgres/MinIO via docker-compose) covering
  duplicate uploads, spoofed extensions, oversized uploads, deletion,
  cross-user authorization, and task enqueueing. Frontend unit tests
  (Vitest) and a Playwright smoke test.
- CI (`.github/workflows/ci.yml`) running lint/typecheck/tests for both
  apps plus a migration-drift check.
- A static landing page (`site/`) published to GitHub Pages —
  documentation/marketing only; it cannot and does not run the backend.

## What Phase 2 actually built

- Real ingestion pipeline (`app/modules/ingestion/`) replacing the Phase 1
  placeholder task: download from object storage → parse → persist
  `source_pages`/`source_blocks` → chunk → embed → persist `chunks` →
  `READY`. Scoped to **native-text PDF only** — see
  [ADR 0002](../adr/0002-lightweight-native-pdf-parser.md) for why the
  parser is `pypdf` (verified against a real generated fixture PDF) rather
  than Docling for this first slice, behind a `DocumentParser` protocol so
  swapping parsers later doesn't touch anything downstream. DOCX/PPTX/
  image sources uploaded in Phase 1 are marked `UNSUPPORTED` with a clear
  message until a later slice adds parsers for them.
- `SourceStatus` gained real states: `UPLOADED → PARSING → READY` (or
  `FAILED` / `UNSUPPORTED`). The Phase 1 placeholder `QUEUED` state is
  retired — it wasn't part of the blueprint's actual state machine
  (section 8.1), it existed only to prove Celery enqueueing worked before
  a real pipeline existed.
- Local BGE-M3 embeddings (`app/ai/embeddings/`), behind a provider
  interface (`EmbeddingProvider`) so a cloud provider can be added later
  without touching retrieval. Verified for real: a downloaded BGE-M3 model
  correctly ranked a semantically-relevant document above two irrelevant
  ones for a test query (see the "Verification" note below).
- Hybrid retrieval (`app/modules/retrieval/`): pgvector cosine similarity
  + Postgres full-text search (`simple` config, generated `tsvector`
  column), fused with Reciprocal Rank Fusion (blueprint section 9.6).
  `POST /v1/search` — always scoped by `user_id` through a join on
  `sources`, so one user's content can never leak into another's results.
  An empty result set returns `not_found: true` explicitly rather than
  silently returning nothing.
- Migration `0002`: enables the `vector` Postgres extension, creates
  `source_pages`, `source_blocks`, `chunks` (HNSW + GIN indexes).
- Frontend: a `/search` page (global, or scoped to one source via
  `?source_id=`), linked from the source detail page once a source is
  `READY`.
- Tests: fast, dependency-free unit tests for the parsing heuristic,
  chunking, and RRF fusion (21 tests, run in `make test-api`, no
  infrastructure needed) plus a `slow`-marked end-to-end suite
  (`make test-api-slow`) that uploads a real fixture PDF, runs the real
  pipeline, and checks golden queries return the expected page — including
  a cross-user isolation check.

### Verification note (what was actually run, not just written)

This phase's parsing, chunking, and embedding logic was developed and
verified against real code before being committed — not written blind:

- A fixture PDF was generated with `reportlab`, parsed with the actual
  `pypdf`-based parser, and chunked with the actual chunker; the output
  was inspected for correctness (headings detected, heading paths
  correct, page ranges correct). The 21 tests in
  `app/tests/modules/ingestion/` and `app/tests/modules/retrieval/test_ranking.py`
  encode exactly this behavior and were run and passed locally with no
  infrastructure (`pytest app/tests/modules/ingestion app/tests/modules/retrieval/test_ranking.py`
  — 21 passed).
- The real `BAAI/bge-m3` model was downloaded and run through the actual
  `LocalBgeEmbeddingProvider`: it produced 1024-dimensional vectors and
  correctly ranked a semantically relevant document above two irrelevant
  ones for a real query (cosine similarity 0.72 for the relevant doc vs.
  0.36 and 0.28 for the irrelevant ones).
- The `pgvector` SQLAlchemy type and its HNSW index DDL were compiled and
  checked against the Postgres dialect (confirmed it emits
  `USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)`).
- `ruff` and `mypy` were installed and run locally against the full
  backend; all findings were fixed or (for one deliberate FastAPI/ruff
  false-positive pattern) explicitly suppressed with a documented reason.

What was **not** verified here: the full pipeline running inside Docker
against live Postgres/Redis/MinIO (no Docker available in the environment
that built this) — run `make test-api-slow` to confirm that end-to-end.

## Phase 3 preview (next up)

Notebook Mode (blueprint section 2.5, 20): notebooks as a collection of
selected sources, grounded chat backed by the retrieval built in Phase 2,
citations rendered from search results, notes. This is also where an LLM
provider (`app/ai/providers/`, Gemini per blueprint section 21) enters the
codebase for the first time — retrieved content must be treated as
untrusted data, never instructions (blueprint section 10).
