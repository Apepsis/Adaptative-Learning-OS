"""Deterministic mastery-aggregate statistics (blueprint 16.1, 16.5, 16.8).

Pure functions over plain `Observation` records, ordered oldest-to-newest —
the service layer builds these from Attempt/Question rows.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Observation:
    score: float  # 0..1, already computed by the grading engine
    hints_used: int
    hint_count: int  # total hints available on that question (0 if none)
    elapsed_ms: int | None


def recent_accuracy(observations: list[Observation], window: int = 5) -> float:
    if not observations:
        return 0.0
    recent = observations[-window:]
    return round(sum(o.score for o in recent) / len(recent), 4)


def weighted_accuracy(observations: list[Observation], decay: float = 0.85) -> float:
    """Recency-weighted mean score — the most recent observation gets full
    weight, each one further back is discounted by another factor of
    `decay`."""
    if not observations:
        return 0.0
    n = len(observations)
    weights = [decay ** (n - 1 - i) for i in range(n)]
    total_weight = sum(weights)
    return round(sum(w * o.score for w, o in zip(weights, observations, strict=True)) / total_weight, 4)


def hint_independence(observations: list[Observation]) -> float:
    if not observations:
        return 1.0
    per_observation = [
        1.0 if o.hint_count <= 0 else max(0.0, 1 - o.hints_used / o.hint_count) for o in observations
    ]
    return round(sum(per_observation) / len(per_observation), 4)


def mastery_confidence(n_observations: int, n_distinct_questions: int) -> float:
    """Blueprint 16.5: separate from p_mastery itself — a handful of
    correct answers on one question shouldn't read as "confidently
    mastered" the way a dozen correct answers across several questions
    would. Saturates towards 1.0 as both observation count and question
    diversity grow; never reaches it exactly."""
    if n_observations <= 0:
        return 0.0
    observation_term = 1 - math.exp(-n_observations / 8)
    diversity_term = min(1.0, n_distinct_questions / 5)
    return round(0.7 * observation_term + 0.3 * diversity_term, 4)


def speed_index(baseline_ms: float | None, observed_ms: int | None, *, was_fully_correct: bool) -> float | None:
    """Blueprint 16.8: compared against the user's *own* history, and
    never computed for an incorrect answer — "no premiar respuestas
    rápidas incorrectas." Returns None when there isn't enough history or
    correctness yet to say anything."""
    if not was_fully_correct or baseline_ms is None or not observed_ms or observed_ms <= 0:
        return None
    raw = baseline_ms / observed_ms
    return round(min(4.0, max(0.25, raw)), 4)
