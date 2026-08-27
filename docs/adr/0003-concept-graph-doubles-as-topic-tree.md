# ADR 0003: The concept graph doubles as the topic/subtopic tree (no separate `modules`/`curricula` tables yet)

## Context

The blueprint's domain model (sections 7.2, 7.6, 11) describes two related
but distinct structures: a **curriculum/module tree** (`curricula`,
`modules` — syllabus-driven, e.g. official IB topic numbering, with
`level_min`/`level_max`, `sequence`) and a **concept graph** (`concepts`,
`concept_edges` — semantic relationships like prerequisites, derivations,
confusable pairs). The Phase 4 DoD (blueprint section 44) asks for both
"topics/subtopics" and "concept graph."

The Module Builder (blueprint section 11.9) that would consume a separate
`modules` table generates full lesson content (intuition, derivation,
worked examples, misconceptions, practice tiers) — that's Phase 5 (Learn
UI) territory, not Phase 4. Building a fully separate `curricula`/`modules`
schema now, before anything consumes it, would be exactly the kind of
speculative "later phase" work the blueprint warns against (Risk R1).

## Decision

For this phase, `concepts` carries a `concept_type` field ("topic" |
"subtopic" | "concept" | "skill") and topic/subtopic navigation is an
**emergent view** over the concept graph, built from `PART_OF` edges
(a subtopic concept has a `PART_OF` edge to its parent topic concept) —
not a separate table. The concept extraction prompt is asked to classify
each extracted item's `concept_type` and to emit `PART_OF` edges for
hierarchy, alongside `PREREQUISITE_OF` and the other relation types.

## Alternatives considered

- **Build `curricula`/`modules` now, populate later.** Rejected: an empty
  table nothing writes to or reads from yet is dead schema, and the
  blueprint's own module list keeps `curriculum` and `retrieval`/etc. as
  separate concerns for a reason — mixing "build the schema" with "nothing
  uses it" doesn't actually reduce Phase 5's work, it just moves an empty
  migration earlier.
- **Skip topic/subtopic entirely, ship concept graph only.** Rejected:
  the Phase 4 DoD explicitly asks for a navigable topic tree, and a flat
  list of 40+ concepts with no grouping is a real usability regression
  from what the blueprint promises.

## Consequences

- `concept_type` and `PART_OF` edges are load-bearing for the frontend's
  topic tree view — get the extraction prompt's classification wrong and
  the tree looks flat or misgrouped. Mitigated by keeping the hierarchy
  shallow (topic → subtopic → concept) and by manual edit/merge being
  part of this phase's own DoD, so misclassification is fixable in the UI,
  not just in a re-run of extraction.
- No official syllabus numbering (e.g. "A.1", "3.2") is stored anywhere
  yet — a topic is just a `Concept` row with `concept_type="topic"`.
  Syllabus-driven sequencing (blueprint 11.3: syllabus overrides inferred
  structure) is not implemented in this phase; extraction currently maps
  loosely to whatever structure the sources actually contain.
- No `level_min`/`level_max`/`sequence` metadata exists per topic yet —
  irrelevant until Phase 5's Learn UI or Phase 10's L0-L5 depth scale
  need it.

## Rollback

If a real curriculum/module tree becomes necessary (e.g. to support
multiple curriculum frameworks per subject, syllabus-driven ordering, or
per-module `level_min`/`level_max`), add `curricula`/`modules` tables as
blueprint section 7.2/7.7 describes, and either migrate `concept_type in
("topic", "subtopic")` rows into `modules` rows or keep both and link a
`Concept` to its owning `Module` via a nullable FK. No change needed to
`concept_edges`, `PREREQUISITE_OF` semantics, or the extraction pipeline's
non-hierarchy relations.
