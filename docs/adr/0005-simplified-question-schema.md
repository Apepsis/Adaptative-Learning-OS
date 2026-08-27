# ADR 0005: Type-specific question columns instead of a generic answer_schema/markscheme

## Context

The blueprint's `questions` table (section 7.8) uses generic
`answer_schema JSONB` and `markscheme JSONB` columns to support an
open-ended set of question types (multiple choice, numeric, symbolic,
short text, derivation, proof/explanation, multipart, handwritten image)
with per-type validation logic living entirely in application code that
interprets the JSON shape.

Phase 6's DoD (blueprint section 44) asks for exactly three types: MCQ,
numeric, short answer.

## Decision

`Question` (`app/modules/practice/models.py`) uses explicit, typed
columns for each supported type instead of a generic schema: `options` +
`correct_option_id` for MCQ, `numeric_answer` + `numeric_tolerance` +
`units` for numeric, `sample_answer` for short answer. `question_type`
selects which columns are meaningful for a given row (enforced in the
service layer, not a DB constraint).

## Alternatives considered

- **Generic `answer_schema` JSONB now, as blueprint specifies.** Rejected
  for this phase: with only three types and no multipart/derivation/
  handwritten support yet, a generic schema buys flexibility nothing
  currently exercises, at the cost of losing column-level type safety and
  making the grading code do JSON-shape validation it wouldn't otherwise
  need. mypy/Pydantic can check explicit columns; they can't meaningfully
  check "this JSONB blob has the shape grading code expects."

## Consequences

- Adding a new question type (symbolic, multipart, derivation, uploaded
  handwritten image — blueprint 14.1) means a migration to add columns,
  not just new application logic. Given this project's phase-by-phase
  pace, that's an acceptable, deliberate cost.
- The grading engine (`app/modules/practice/grading.py`) dispatches on
  `question_type` to a specific, typed grading function per type rather
  than a generic rubric interpreter.

## Rollback

If a fourth type needs a shape none of the existing columns fit (e.g.
multipart with per-part marks), either add more typed columns (consistent
with this ADR) or, if the type proliferation becomes unwieldy, migrate to
a generic `answer_schema`/`markscheme` JSONB as blueprint 7.8 originally
specified — the grading dispatch's per-type functions would become
per-type JSON-shape interpreters instead, without changing the
`Attempt`/`AttemptError` tables or the practice session flow around them.
