# ADR 0006: Phase 7 learner-model simplifications (BKT bootstrap, misconceptions, transfer score)

## Context

Blueprint sections 15-17 specify the learner model at a level of detail
that assumes either a trained/calibrated system or a multi-user dataset
neither of which exist yet (single personal user, day one of practice
data). Three places needed a concrete, documented choice where the
blueprint describes the target shape but not the bootstrap behavior:

1. **BKT bootstrap parameters** (16.2-16.3): the blueprint gives one
   worked example — `P(L0)=0.20, P(T)=0.12, P(S)=0.10, P(G)=0.20` — for
   4-option MCQ, and says defaults should vary "por question type" without
   giving numeric/short-answer values.
2. **Misconception object + pattern detection** (15.2, 15.4): described as
   a catalog (`misconceptions`) linked to attempts via `misconception_id`,
   with candidate/confirmed thresholds (`>=3` errors, `>=5` across `>=2`
   questions) but no decay formula for how old evidence should count.
3. **Transfer score** (16.7): its formula assumes attempts are tagged
   `transfer=true`, but nothing in the product (question generation,
   manual authoring, practice sessions) marks a question as testing a
   "transfer" context yet.

## Decisions

**BKT bootstrap.** `app/modules/mastery/bkt.py` keeps the blueprint's MCQ
numbers exactly, and adds `numeric`/`short_answer` variants: much lower
`P(G)` (0.05 vs 0.20 — you can't luck into an exact numeric value the way
you can pick 1-of-4 options), and a slightly higher `P(S)` for
short-answer (0.15 — LLM grading of free text is noisier than exact-match
numeric/MCQ grading). `P(L0)=0.20` stays a single constant (it's a prior
on the *concept*, not the question type being answered). None of this is
calibrated from observed data — that's explicitly out of scope until
there's enough practice history to justify it (mirrors the IRT
deferral in blueprint 16.6's own reasoning).

**Misconceptions are per-user, not a shared catalog.** `misconceptions`
(`app/modules/mastery/models.py`) is keyed by `(user_id, concept_id,
error_type)` rather than a standalone catalog table with a separate
per-user link — this is a personal, single-user LOS (blueprint section
27), so a shared catalog buys nothing a per-user row doesn't already give,
and avoids a join table nothing else needs yet.

**Pattern detection uses a documented step decay**, not blueprint's
unspecified one: full weight within 30 days, 0.5x for 31-90 days, 0.25x
beyond that (`app/modules/mastery/patterns.py`). Candidate at weighted
count >=3; confirmed at weighted count >=5 *and* >=2 distinct questions
(the diversity requirement is load-bearing — encoded directly in
`test_five_events_on_one_question_stay_a_candidate_not_confirmed`).

**Transfer score is not computed.** `concept_mastery.transfer_score`
exists (matches blueprint 7.9's schema) but always reads `0.0` — nothing
tags an attempt as a transfer-context observation, so computing 16.7's
formula would be evidence-free arithmetic dressed up as a number. Real
whenever question generation or manual authoring adds a `transfer`
flag.

## Alternatives considered

- **Skip transfer_score entirely (no column).** Rejected: keeping the
  column matches the blueprint schema and costs nothing; a UI or future
  phase reading it gets an honest `0.0` (never-computed) rather than a
  missing field to special-case.
- **Global misconception catalog + per-user progress table.** Rejected
  for now as the multi-user-shaped version of a problem this project
  doesn't have yet — revisit if this ever supports more than one user.

## Consequences

- `mastery_confidence` (16.5) is deliberately *not* a five-factor blend of
  every listed input (observations, diversity, recency, difficulty,
  hints) — it uses observation count + question diversity only.
  Recency and hints already show up elsewhere (`weighted_accuracy`,
  `hint_independence`) as their own fields; folding them into confidence
  too would double-count the same evidence under a different name.
- Bootstrap BKT params will misestimate mastery for the first several
  attempts on any concept, same as any cold-start model — expected, and
  why `mastery_confidence` exists as a separate, low-until-proven signal.

## Rollback

Recalibrating BKT params from observed data, building a shared
misconception catalog, or wiring up a real `transfer` flag on attempts are
all additive changes to `app/modules/mastery/` — none require touching
`concept_mastery`'s or `misconceptions`' existing columns or the
`practice` module's attempt-submission flow that feeds them.
