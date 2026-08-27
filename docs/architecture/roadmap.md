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
| 2 | Parsing + search (Docling, OCR, chunks, embeddings, hybrid retrieval) | ⬜ Not started |
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
- PostgreSQL (pgvector image, extension not yet enabled — that's Phase 2)
  with an Alembic migration for `users`, `subjects`, `sources`.
- MinIO-backed object storage with streamed SHA-256 hashing, MIME
  sniffing (not trusting client-supplied extension/content-type), size
  limits, and duplicate detection.
- A placeholder Celery ingestion task (`ingest_source_placeholder`) that
  proves the async pipeline end-to-end: upload -> `UPLOADED` -> task
  enqueued -> `QUEUED`. No parsing/OCR/embedding yet — that's Phase 2.
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

## Phase 2 preview (next up)

Per blueprint section 48, scope Phase 2 to native-text PDF only first:

```
PDF -> Docling -> canonical blocks -> structural chunks -> embeddings
  -> Postgres FTS -> pgvector -> hybrid search -> citations
```

Explicitly out of scope for the first Phase 2 slice: OCR, DOCX/PPTX
parsing, concept extraction, the tutor. Acceptance: a golden query set
against a fixture PDF returns the expected page in the top 10 results at
an agreed rate, and a query with no answer in the sources returns an
explicit `NOT_FOUND` rather than a hallucinated one.
