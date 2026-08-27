"""Error pattern detection (blueprint 15.4) — deterministic, not an LLM
call: turns a run of same-typed errors into a "candidate" and then a
"confirmed" misconception once there's enough, diverse, reasonably recent
evidence. The blueprint gives the >=3 / >=5-across-2-questions counts but
not a decay formula; the step decay here is a documented, testable choice
— see docs/adr/0006-learner-model-simplifications.md.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

CANDIDATE_THRESHOLD = 3.0  # weighted event count
CONFIRMED_THRESHOLD = 5.0  # weighted event count
CONFIRMED_MIN_DISTINCT_QUESTIONS = 2


@dataclass(frozen=True)
class ErrorEvent:
    question_id: uuid.UUID
    occurred_at: datetime


def _decay_weight(age_days: float) -> float:
    if age_days <= 30:
        return 1.0
    if age_days <= 90:
        return 0.5
    return 0.25


def evaluate_pattern(events: list[ErrorEvent], *, now: datetime) -> str | None:
    """Returns None (not even a candidate yet), "candidate", or
    "confirmed" for one (concept, error_type) pair's error history."""
    if not events:
        return None
    weighted_count = sum(_decay_weight((now - e.occurred_at).total_seconds() / 86400) for e in events)
    distinct_questions = len({e.question_id for e in events})
    if weighted_count >= CONFIRMED_THRESHOLD and distinct_questions >= CONFIRMED_MIN_DISTINCT_QUESTIONS:
        return "confirmed"
    if weighted_count >= CANDIDATE_THRESHOLD:
        return "candidate"
    return None
