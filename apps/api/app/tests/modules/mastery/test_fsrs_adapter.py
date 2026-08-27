from datetime import UTC, datetime

import fsrs
import pytest

from app.modules.mastery import fsrs_adapter


def test_new_card_starts_in_learning_state() -> None:
    card = fsrs_adapter.new_card()
    assert card.state == fsrs.State.Learning


def test_rating_from_name_maps_all_four_ratings() -> None:
    assert fsrs_adapter.rating_from_name("again") == fsrs.Rating.Again
    assert fsrs_adapter.rating_from_name("hard") == fsrs.Rating.Hard
    assert fsrs_adapter.rating_from_name("good") == fsrs.Rating.Good
    assert fsrs_adapter.rating_from_name("easy") == fsrs.Rating.Easy


def test_rating_from_name_rejects_unknown_rating() -> None:
    with pytest.raises(ValueError, match="Unknown FSRS rating"):
        fsrs_adapter.rating_from_name("perfect")


def test_review_a_new_card_schedules_it_into_the_future() -> None:
    now = datetime(2026, 8, 26, tzinfo=UTC)
    card = fsrs_adapter.new_card()

    updated_card, log = fsrs_adapter.review(card, "good", review_datetime=now, response_ms=4000)

    assert updated_card.due > now
    assert updated_card.stability is not None
    assert log.rating == fsrs.Rating.Good
    assert log.review_datetime == now


def test_again_schedules_sooner_than_easy() -> None:
    now = datetime(2026, 8, 26, tzinfo=UTC)

    again_card, _ = fsrs_adapter.review(fsrs_adapter.new_card(), "again", review_datetime=now, response_ms=None)
    easy_card, _ = fsrs_adapter.review(fsrs_adapter.new_card(), "easy", review_datetime=now, response_ms=None)

    assert again_card.due <= easy_card.due


def test_card_from_state_round_trips_and_can_be_reviewed_again() -> None:
    now = datetime(2026, 8, 26, tzinfo=UTC)
    first_card, _ = fsrs_adapter.review(fsrs_adapter.new_card(), "good", review_datetime=now, response_ms=None)

    reconstructed = fsrs_adapter.card_from_state(
        state=first_card.state.value,
        step=first_card.step,
        stability=first_card.stability,
        difficulty=first_card.difficulty,
        due=first_card.due,
        last_review=first_card.last_review,
    )

    later = first_card.due
    second_card, _ = fsrs_adapter.review(reconstructed, "good", review_datetime=later, response_ms=None)
    assert second_card.due >= later
