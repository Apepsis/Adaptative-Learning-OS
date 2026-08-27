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
| 3 | Notebook Mode (grounded chat over sources) | ✅ Done |
| 4 | Curriculum Builder (concept graph) | ✅ Done |
| 5 | Learn UI (lessons, flashcards, definitions) | ✅ Done |
| 6 | Question Bank + basic practice | ✅ Done |
| 7 | Learner Model (BKT, FSRS, error patterns) | ⬜ Not started |
| 8 | Planner v1 (OR-Tools) | ⬜ Not started |
| 9 | Adaptive loop (nightly replanning, stability horizon) | ⬜ Not started |
| 10 | Advanced/olympiad (L0-L5, transfer, STEM verification) | ⬜ Not started |
| 11 | Integrations (Google Calendar, web/YouTube ingestion) | ⬜ Not started |
| 12 | Hardening (security, evals, backups, observability) | ⬜ Not started |

**MVP scope** (blueprint section 43) is Phases 0-5 plus basic practice
from Phase 6. **That MVP is now complete.** The full loop described in
the blueprint's conclusion (section 54) is real, end to end: upload a
source → it's parsed, chunked, embedded, and searchable → concepts are
extracted into a graph → lessons/definitions/flashcards/a study guide are
generated from it → you can ask questions grounded in your sources with
citations → you can practice questions (written or generated) with
hints, timing, and error feedback. Phases 7-12 (adaptive mastery
modeling, FSRS, the OR-Tools planner, olympiad-depth verification,
external integrations, production hardening) are a distinct, larger
second stage — not started, and not silently implied by anything above.

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

## What Phase 3 actually built

- `app/ai/providers/`: a `GenerationProvider` protocol and a Gemini
  implementation (`app/ai/providers/gemini.py`), using the real
  `google-genai` SDK — its API shape (`client.aio.models.generate_content`,
  `types.GenerateContentConfig(system_instruction=...)`, `response.text`)
  was verified by installing the package and introspecting it directly,
  not guessed. `FAST_MODEL`/`REASONING_MODEL` now default to real model
  names (`gemini-2.5-flash` / `gemini-2.5-pro`) instead of blank, so chat
  works out of the box once `GEMINI_API_KEY` is set — still fully
  overridable via env, never hardcoded elsewhere (blueprint section 21.1).
  No `GEMINI_API_KEY` → chat fails fast with a clear `AIProviderError`
  (HTTP 502) telling the user where to get one, rather than a confusing
  downstream error.
- `app/modules/notebooks/`: notebooks, notebook-source associations
  ("active sources"), notes, and grounded chat backed directly by Phase
  2's `hybrid_search`. `POST /v1/notebooks/{id}/chat`.
- **Prompt-injection defense is structural, not a hope** (blueprint
  section 10): retrieved evidence is formatted as a numbered, clearly
  delimited data block inside the *user* turn — it never touches the
  system instruction, which is a fixed constant the request payload
  cannot reach. `app/tests/modules/notebooks/test_prompt_formatting.py`
  pins this down directly, including a test that evidence containing
  "ignore all previous instructions" ends up quoted under a citation
  marker, never merged into the system prompt.
- **Honest not-found handling** (blueprint sections 20.4, 31.4): a
  notebook with no sources, or a query with no matching evidence, returns
  a clear message *without calling the LLM at all* — cheaper and more
  reliably honest than hoping the model says "I don't know."
- Every chat turn (user and assistant) is persisted to
  `notebook_messages` with citations, so history survives a page reload.
- Frontend: `/notebooks` (list/create), `/notebooks/[id]` (source
  management + chat UI with inline citation links back to the source),
  `/notebooks/[id]/notes`.
- Tests: fast plumbing tests for notebook/source/note CRUD and the full
  chat flow use `FakeEmbeddingProvider`/`FakeGenerationProvider`
  (`app/tests/modules/notebooks/fakes.py`) — real chunks from the real
  parser, fake vectors, so tests don't need the 2GB model or a live
  Gemini key. Real embedding correctness stays covered by Phase 2's
  `slow`-marked suite; there is deliberately no live-Gemini test (would
  need a real API key and make real network calls from CI).

### Known gaps

- No streaming responses yet (blueprint mentions SSE for the tutor,
  section 24.9) — chat is request/response. Acceptable for the first
  slice; revisit if response latency makes it feel unresponsive.
- No study guide / flashcard / quiz artifact generation yet (blueprint
  section 24.10's other endpoints) — deferred to keep this phase to what
  the MVP Notebook DoD (section 44) actually requires: multiple
  notebooks, active source selection, grounded chat, notes.
- `SOURCE_ONLY` / `QUOTE_REQUIRED` mode (blueprint section 20.4) isn't a
  separate mode yet — the current system instruction already forbids
  outside knowledge, but there's no explicit LITERAL/PARAPHRASE/
  NOT_FOUND/RELATED_ONLY classification. Worth adding when the tutor
  (Phase 6+) needs it more precisely.

## What Phase 4 actually built

- `app/modules/curriculum/`: `concepts`, `concept_aliases`, `concept_edges`,
  `concept_evidence`. **No separate `curricula`/`modules` tables** — see
  [ADR 0003](../adr/0003-concept-graph-doubles-as-topic-tree.md): a
  `concept_type` field ("topic"/"subtopic"/"concept"/"skill") plus
  `PART_OF` edges give a navigable topic tree as an emergent view over the
  concept graph, rather than a second schema nothing would consume before
  Phase 5.
- `POST /v1/subjects/{id}/curriculum/build`: samples up to 60 chunks from
  the subject's processed sources (syllabus-tagged sources prioritized),
  asks Gemini for **structured JSON output** (`response_schema` +
  `response.parsed` — this API shape was verified by installing
  `google-genai` and inspecting the real field definitions, same as the
  chat provider in Phase 3), and persists concepts/edges/evidence.
- **Normalization**: exact-name and alias matching only (blueprint
  11.5's first two steps) — embedding-similarity fuzzy matching and LLM
  adjudication for ambiguous near-duplicates are deferred and listed as a
  known gap below. Re-running "Build curriculum" after adding more
  sources updates existing concepts rather than duplicating them
  (verified by a test that runs extraction twice and checks the concept
  count stays the same).
- **Cycle rejection is real, not just described**: `app/modules/curriculum/graph.py`
  is a pure, dependency-free graph traversal, checked directly with 6
  unit tests, and a build-time test that feeds the extractor a
  deliberately cyclic pair of edges (A→B→A) and confirms only one is
  persisted.
- **Manual edit/merge** (the other half of the Phase 4 DoD): approve/
  reject a proposed concept, edit its name/definition, delete it, or
  merge one concept into another — merge reassigns edges and evidence
  (dropping anything that would become a self-loop or duplicate) and adds
  the absorbed concept's name as an alias of the surviving one.
- Frontend: `/subjects/[id]` — a "Build curriculum" button with a result
  summary, concepts grouped into Topics/Subtopics/Concepts/Skills
  sections, each with inline approve/reject, a relationships expander
  (lazy-loaded), and a merge-into selector.
- Tests: 6 fast, dependency-free tests for `would_create_cycle`, plus
  build/CRUD/merge/cycle/cross-user-isolation tests using
  `FakeGenerationProvider.structured_response` (extended in this phase to
  support `generate_structured`, relocated to the shared
  `app/tests/fakes.py` since both notebooks and curriculum tests need it
  now). ruff and mypy clean across all 98 backend files.

### Known gaps

- Concept normalization is exact-match only — near-duplicate concepts
  extracted with slightly different names (e.g. "Newton's 2nd Law" vs
  "Newton's second law of motion") won't auto-merge; the manual merge UI
  is the mitigation until embedding-similarity dedup lands.
- No syllabus-driven ordering (blueprint 11.3): if a syllabus source is
  present, extraction reads it like any other source rather than treating
  it as the authoritative structure to map everything else onto.
- Confidence scores on edges are stored but not surfaced or acted on
  anywhere yet (always defaults to 1.0 from the model).

## What Phase 5 actually built

Mostly presentation over data Phase 4 already produced, plus one new LLM
generation pass:

- **Lesson view** (`/subjects/[id]/concepts/[id]`): a concept's
  definition, its PART_OF parent, PREREQUISITE_OF prerequisites (and
  other relations), and — new this phase — the actual evidence **text**
  it was extracted from, not just chunk ids. `ChunkRepository` gained
  `get_with_source_title_for_user` for this; the curriculum module's
  `ConceptDetailRead.evidence` field replaced the old bare
  `evidence_chunk_ids` (a real API shape change, made freely since
  nothing external depends on it yet).
- **Definitions** (`/subjects/[id]/definitions`): a filterable list —
  genuinely just a read + filter over existing concept data, no new
  backend endpoint needed.
- **Flashcards** (`app/modules/learn/`, `flashcards` table): generation is
  **deterministic, not an LLM call** — one flashcard per concept/skill
  (not per topic/subtopic — a "what is Kinematics?" flashcard tests a
  label, not a fact) that has a definition and doesn't already have one.
  Free, instant, and re-running generation doesn't duplicate. Manual
  flashcard creation/edit/delete also supported. FSRS review scheduling
  (blueprint 7.10's `review_state`) is still Phase 7 — this is content
  only.
- **Study guide** (`study_guides` table, one regenerable row per subject):
  the one new LLM call this phase — Gemini synthesizes the subject's
  approved concepts and their relationships into a Markdown guide. Scoped
  to the *subject* rather than a *notebook* — see
  [ADR 0004](../adr/0004-study-guide-scoped-to-subject.md) for why, since
  blueprint 24.10 describes it as a notebook artifact. Rendered with
  `react-markdown` on the frontend.
- Tests: flashcard generation's concept-type filtering and idempotency,
  manual CRUD, study guide generation/regeneration/empty-state, using the
  same `FakeGenerationProvider` pattern as Phases 3-4. ruff and mypy clean
  across all 106 backend files.

### Known gaps

- No spaced-repetition scheduling for flashcards yet (Phase 7).
- The study guide has no explicit "regenerate only if concepts changed"
  logic — every "Regenerate" click makes a fresh LLM call even if nothing
  changed since the last one.
- Lesson view doesn't yet render LaTeX/formulas specially — evidence text
  is shown as extracted plain text (matches Phase 2's pypdf-based parser,
  which doesn't preserve formula structure either).

## What Phase 6 actually built — MVP complete

- `app/modules/practice/`: `questions`, `practice_sessions`, `attempts`,
  `attempt_errors`. Type-specific columns (not a generic
  `answer_schema`/`markscheme` JSONB) for MCQ/numeric/short-answer — see
  [ADR 0005](../adr/0005-simplified-question-schema.md) for why.
- **Grading order matches blueprint section 14.2 exactly**: MCQ and
  numeric are graded by pure, dependency-free functions
  (`app/modules/practice/grading.py`, 8 unit tests) — no LLM call at all.
  Only short answer needs one, and it does grading *and* error
  classification in a single structured call rather than two.
- **Manual authoring and LLM generation both produce real questions**:
  generation is grounded in one concept's evidence (reusing Phase 4's
  `get_concept`), using the same `generate_structured` + `response.parsed`
  pattern as curriculum extraction. Generated questions get a
  **structural-validity check** (options well-formed and exactly one
  correct, tolerance non-negative, a sample answer present) before being
  marked `verified` — not the full independent-solver verification
  blueprint section 13.6 describes for STEM types (no solver is built).
  Anything that fails is persisted `quarantined` for review, and — this
  was a real bug caught during testing, not just a design intention —
  **excluded from practice session selection** by an explicit repository
  filter, with a regression test proving a quarantined question can't be
  picked.
- **Basic error classification** (the DoD's explicit fourth requirement):
  every non-correct attempt gets a one-sentence classification from the
  blueprint's own taxonomy (`app/modules/practice/models.py`'s
  `AttemptError`), grounded in the actual correct-vs-submitted difference
  — never a guess dressed up as a specific category.
- **Hints are revealed one at a time**, not exposed with the question
  (`GET /questions/{id}/hints/{index}`), matching blueprint 20.5.
  Practice sessions never leak the answer key while a question is active
  — `QuestionPracticeView` is a deliberately narrower schema than the
  bank-management `QuestionRead`.
- Frontend: `/subjects/[id]/questions` (bank list, manual authoring form,
  generate-from-concept form, start-session button) and
  `/subjects/[id]/practice/[sessionId]` (the actual practice flow — timed
  answer submission, progressive hints, graded feedback with error
  explanation, session completion).
- Tests: 8 pure grading tests, question-shape validation, session
  creation/progression/completion, MCQ/numeric/short-answer attempt
  grading (correct and incorrect paths), solution-reveal handling,
  cross-user authorization, and the quarantine-exclusion regression.
  ruff and mypy clean across all 122 backend files.

### Known gaps (deliberately deferred, not silently skipped)

- No independent-solver STEM verification (blueprint 13.6) — structural
  validity only.
- No streaming grading/generation responses.
- No misconception catalog linking recurring error patterns across
  attempts (blueprint section 15.4) — each `AttemptError` stands alone.
- No item origin beyond `user`/`generated` (no official/textbook/teacher
  import pipeline, blueprint 13.1-13.2).
- No question difficulty auto-classification (`difficulty_level` exists
  as a column but nothing populates it yet — that's Phase 10's L0-L5
  depth scale).

## Phase 7+ preview

Everything from here is genuinely a second stage, not a continuation of
the MVP loop: the Learner Model (BKT, FSRS, error-pattern aggregation
into misconceptions), the Adaptive Planner (OR-Tools CP-SAT scheduling
against exam dates and availability), advanced/olympiad depth (L0-L5
gating, transfer scoring, SymPy/Pint-based STEM verification), external
integrations (Google Calendar, web/YouTube ingestion), and production
hardening (security review, adversarial RAG evals, backups, full
observability). See blueprint sections 16-21, 7, 12, 28-31 for what each
of these actually requires — they're substantial enough that none should
be started without their own scoped, verified vertical slice, the same
way each phase above was.
