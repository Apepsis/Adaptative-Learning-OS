"""Thin adapter around `fsrs` (py-fsrs, blueprint section 17) — its real
API (`Card`, `Rating`, `Scheduler`, `State`, `ReviewLog`) was verified by
installing the package (version 6.3.2) and introspecting it directly, the
same way the Gemini SDK shape was verified in Phase 3. `Card` is a plain
data holder; `Scheduler` is stateless algorithm code. We persist a card's
fields ourselves (`mastery.models.ReviewState`) and reconstruct a `Card`
from them on every review — `card_id` is never persisted, since nothing
in the scheduler's behavior depends on it and our own `flashcard_id` is
the real key.
"""

from datetime import datetime

import fsrs

_SCHEDULER = fsrs.Scheduler()

_RATING_BY_NAME: dict[str, fsrs.Rating] = {
    "again": fsrs.Rating.Again,
    "hard": fsrs.Rating.Hard,
    "good": fsrs.Rating.Good,
    "easy": fsrs.Rating.Easy,
}


def rating_from_name(name: str) -> fsrs.Rating:
    try:
        return _RATING_BY_NAME[name]
    except KeyError as exc:
        raise ValueError(f"Unknown FSRS rating {name!r}, expected one of {tuple(_RATING_BY_NAME)}") from exc


def new_card() -> fsrs.Card:
    return fsrs.Card()


def card_from_state(
    *,
    state: int,
    step: int | None,
    stability: float | None,
    difficulty: float | None,
    due: datetime,
    last_review: datetime | None,
) -> fsrs.Card:
    return fsrs.Card(
        state=fsrs.State(state),
        step=step,
        stability=stability,
        difficulty=difficulty,
        due=due,
        last_review=last_review,
    )


def review(
    card: fsrs.Card, rating_name: str, *, review_datetime: datetime, response_ms: int | None
) -> tuple[fsrs.Card, fsrs.ReviewLog]:
    return _SCHEDULER.review_card(
        card, rating_from_name(rating_name), review_datetime=review_datetime, review_duration=response_ms
    )
