# ADR 0004: Study guide is a subject artifact, not a notebook artifact

## Context

The blueprint's Notebook Mode (section 24.10) defines
`POST /notebooks/{id}/artifacts/study-guide` — a study guide generated
from a notebook's selected sources. Phase 3 deferred this (see the "Known
gaps" note for Phase 3 in `docs/architecture/roadmap.md`) because a
notebook is a curated, possibly narrow or overlapping set of sources, and
generating a coherent study guide from an arbitrary source subset before
the concept graph existed would have meant re-deriving structure Phase 4
now provides for free.

Phase 5 (Learn UI, blueprint section 22.3) also lists "Study Guide" as a
deliverable, this time clearly in the context of a **subject's** learning
material — alongside Lessons, Flashcards, and Definitions, all of which
are subject/concept-scoped in this codebase (Phase 4's concept graph is
per-subject, not per-notebook).

## Decision

Implement the study guide as a subject-scoped artifact:
`POST /v1/subjects/{id}/study-guide/generate`, backed by a `study_guides`
table (one regenerable row per subject) in `app/modules/learn/`. Generation
is grounded in the subject's **approved concepts** (from Phase 4) and
their evidence excerpts — a coherent structure to summarize, rather than
an arbitrary bag of chunks from whatever sources happen to be in one
notebook.

## Alternatives considered

- **Implement it as a notebook artifact, as blueprint 24.10 literally
  specifies.** Rejected for now: would either duplicate the subject-scoped
  concept-graph-driven generation this phase already needs, or ignore the
  concept graph entirely and fall back to raw chunk summarization (a
  worse study guide, and duplicate LLM-prompt-engineering effort).
- **Wait and do both.** Rejected: the notebook-scoped version doesn't add
  functionality yet without a real use case ("I want a guide to just
  these 3 sources, not my whole subject") that hasn't been requested.

## Consequences

- A user cannot currently generate a study guide scoped to an arbitrary
  notebook's source subset — only per-subject, from approved concepts.
- Sources not yet mapped into the concept graph (i.e., before "Build
  curriculum" has run, or sources outside any subject) don't contribute
  to the study guide even if they're in a notebook.

## Rollback

Add `POST /notebooks/{id}/artifacts/study-guide` as blueprint 24.10
describes, generating from the notebook's active sources' chunks directly
(bypassing the concept graph) for cases where a subject-wide, concept-
driven guide isn't what the user wants. Both can coexist — they solve
different problems and would share little code beyond the LLM call
pattern.
