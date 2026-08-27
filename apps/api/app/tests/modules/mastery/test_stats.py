import pytest

from app.modules.mastery import stats


def _obs(score: float, hints_used: int = 0, hint_count: int = 0, elapsed_ms: int | None = 1000) -> stats.Observation:
    return stats.Observation(score=score, hints_used=hints_used, hint_count=hint_count, elapsed_ms=elapsed_ms)


def test_recent_accuracy_empty_is_zero() -> None:
    assert stats.recent_accuracy([]) == 0.0


def test_recent_accuracy_uses_only_the_window() -> None:
    observations = [_obs(0.0)] * 10 + [_obs(1.0)] * 5
    assert stats.recent_accuracy(observations, window=5) == 1.0


def test_weighted_accuracy_weighs_recent_observations_more() -> None:
    # Older wrong, newer right — the recency weighting should pull the
    # average above the unweighted 0.5.
    observations = [_obs(0.0), _obs(1.0)]
    assert stats.weighted_accuracy(observations) > 0.5


def test_weighted_accuracy_empty_is_zero() -> None:
    assert stats.weighted_accuracy([]) == 0.0


def test_hint_independence_full_when_no_hints_available() -> None:
    assert stats.hint_independence([_obs(1.0, hints_used=0, hint_count=0)]) == 1.0


def test_hint_independence_zero_when_all_hints_used() -> None:
    assert stats.hint_independence([_obs(1.0, hints_used=3, hint_count=3)]) == 0.0


def test_hint_independence_partial() -> None:
    assert stats.hint_independence([_obs(1.0, hints_used=1, hint_count=2)]) == 0.5


def test_mastery_confidence_zero_observations() -> None:
    assert stats.mastery_confidence(0, 0) == 0.0


def test_mastery_confidence_increases_with_more_observations() -> None:
    low = stats.mastery_confidence(1, 1)
    high = stats.mastery_confidence(20, 5)
    assert 0.0 < low < high <= 1.0


def test_mastery_confidence_increases_with_diversity_at_fixed_observation_count() -> None:
    narrow = stats.mastery_confidence(10, 1)
    diverse = stats.mastery_confidence(10, 5)
    assert diverse > narrow


def test_speed_index_none_when_incorrect() -> None:
    assert stats.speed_index(1000, 500, was_fully_correct=False) is None


def test_speed_index_none_without_baseline() -> None:
    assert stats.speed_index(None, 500, was_fully_correct=True) is None


def test_speed_index_clamped_upper() -> None:
    assert stats.speed_index(100_000, 100, was_fully_correct=True) == 4.0


def test_speed_index_clamped_lower() -> None:
    assert stats.speed_index(100, 100_000, was_fully_correct=True) == 0.25


def test_speed_index_reasonable_ratio() -> None:
    assert stats.speed_index(1000, 500, was_fully_correct=True) == pytest.approx(2.0)
