import pytest

from app.modules.mastery import bkt

_MCQ = bkt.BKT_PARAMS_BY_QUESTION_TYPE["mcq"]  # p_transition=0.12, p_slip=0.10, p_guess=0.20


def test_correct_answer_matches_hand_derived_blueprint_formula() -> None:
    # Blueprint 16.2: P(L|correct) = P(L)(1-P(S)) / [P(L)(1-P(S)) + (1-P(L))P(G)]
    # = 0.2*0.9 / (0.2*0.9 + 0.8*0.2) = 0.18/0.34 = 9/17
    # P(L_next) = 9/17 + (1 - 9/17)*0.12
    expected = 9 / 17 + (1 - 9 / 17) * 0.12
    result = bkt.update_mastery(0.2, score=1.0, params=_MCQ)
    assert result == pytest.approx(expected)
    assert result == pytest.approx(0.5858823529411765)


def test_incorrect_answer_matches_hand_derived_blueprint_formula() -> None:
    # P(L|incorrect) = P(L)*P(S) / [P(L)*P(S) + (1-P(L))(1-P(G))]
    # = 0.2*0.1 / (0.2*0.1 + 0.8*0.8) = 0.02/0.66 = 1/33
    expected = 1 / 33 + (1 - 1 / 33) * 0.12
    result = bkt.update_mastery(0.2, score=0.0, params=_MCQ)
    assert result == pytest.approx(expected)
    assert result == pytest.approx(0.14666666666666667)


def test_partial_credit_interpolates_between_correct_and_incorrect() -> None:
    incorrect = bkt.update_mastery(0.2, score=0.0, params=_MCQ)
    half = bkt.update_mastery(0.2, score=0.5, params=_MCQ)
    correct = bkt.update_mastery(0.2, score=1.0, params=_MCQ)
    assert incorrect < half < correct


def test_repeated_correct_answers_converge_upward() -> None:
    p = 0.2
    history = [p]
    for _ in range(10):
        p = bkt.update_mastery(p, score=1.0, params=_MCQ)
        history.append(p)
    assert all(b >= a for a, b in zip(history, history[1:], strict=False))
    assert history[-1] > 0.9


def test_repeated_incorrect_answers_stay_low() -> None:
    p = 0.2
    for _ in range(10):
        p = bkt.update_mastery(p, score=0.0, params=_MCQ)
    # Never converges to exactly 0 — P(T) always injects some learning
    # probability, and P(G) means a wrong answer never fully rules out
    # knowledge either.
    assert 0.0 < p < 0.2


@pytest.mark.parametrize("bad_score", [-0.01, 1.01])
def test_update_mastery_rejects_score_out_of_range(bad_score: float) -> None:
    with pytest.raises(ValueError, match="score"):
        bkt.update_mastery(0.2, score=bad_score, params=_MCQ)


@pytest.mark.parametrize("bad_p", [-0.01, 1.01])
def test_update_mastery_rejects_p_mastery_out_of_range(bad_p: float) -> None:
    with pytest.raises(ValueError, match="p_mastery"):
        bkt.update_mastery(bad_p, score=1.0, params=_MCQ)


def test_bkt_params_validates_probability_bounds() -> None:
    with pytest.raises(ValueError, match="p_slip"):
        bkt.BktParams(p_transition=0.1, p_slip=1.5, p_guess=0.1)


def test_bootstrap_params_exist_for_every_practice_question_type() -> None:
    for question_type in ("mcq", "numeric", "short_answer"):
        assert question_type in bkt.BKT_PARAMS_BY_QUESTION_TYPE
