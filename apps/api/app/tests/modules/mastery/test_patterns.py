import uuid
from datetime import UTC, datetime, timedelta

from app.modules.mastery import patterns

NOW = datetime(2026, 8, 26, tzinfo=UTC)
Q1, Q2 = uuid.uuid4(), uuid.uuid4()


def _event(question_id: uuid.UUID, days_ago: float) -> patterns.ErrorEvent:
    return patterns.ErrorEvent(question_id=question_id, occurred_at=NOW - timedelta(days=days_ago))


def test_no_events_is_not_a_pattern() -> None:
    assert patterns.evaluate_pattern([], now=NOW) is None


def test_two_recent_events_are_not_yet_a_candidate() -> None:
    events = [_event(Q1, 1), _event(Q1, 2)]
    assert patterns.evaluate_pattern(events, now=NOW) is None


def test_three_recent_events_become_a_candidate() -> None:
    events = [_event(Q1, 1), _event(Q1, 2), _event(Q1, 3)]
    assert patterns.evaluate_pattern(events, now=NOW) == "candidate"


def test_five_events_on_one_question_stay_a_candidate_not_confirmed() -> None:
    # Blueprint 15.4 requires diversity across >=2 questions for a
    # "confirmed" pattern — repeated errors on the *same* question aren't
    # enough evidence that it's a general misconception.
    events = [_event(Q1, i) for i in range(5)]
    assert patterns.evaluate_pattern(events, now=NOW) == "candidate"


def test_five_events_across_two_questions_confirm() -> None:
    events = [_event(Q1, 1), _event(Q1, 2), _event(Q1, 3), _event(Q2, 4), _event(Q2, 5)]
    assert patterns.evaluate_pattern(events, now=NOW) == "confirmed"


def test_old_events_decay_and_may_fall_below_candidate() -> None:
    # 3 events all >90 days old each weigh 0.25 -> weighted count 0.75,
    # below the candidate threshold even though the raw count is 3.
    events = [_event(Q1, 100), _event(Q1, 120), _event(Q2, 150)]
    assert patterns.evaluate_pattern(events, now=NOW) is None


def test_mixed_recency_can_reach_candidate_but_not_confirmed() -> None:
    # 4 events at full weight on the same question: candidate, not
    # confirmed (still only one distinct question).
    events = [_event(Q1, 1), _event(Q1, 2), _event(Q1, 3), _event(Q1, 4)]
    assert patterns.evaluate_pattern(events, now=NOW) == "candidate"
