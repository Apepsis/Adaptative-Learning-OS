"""Bayesian Knowledge Tracing (blueprint sections 16.2-16.4).

Pure functions only — no I/O, no ORM. The service layer fetches/persists
`concept_mastery`; this module just computes the next P(mastery) given a
prior and an observed outcome.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class BktParams:
    """Bootstrap parameters (blueprint 16.3): "no universales — defaults
    por question type... luego calibrar con datos." These are the
    untrained defaults; nothing recalibrates them from observed data yet
    (see docs/adr/0006-learner-model-simplifications.md)."""

    p_transition: float  # P(T): probability of learning the skill this turn
    p_slip: float  # P(S): probability a student who knows it slips
    p_guess: float  # P(G): probability a student who doesn't know it guesses right

    def __post_init__(self) -> None:
        for name, value in (
            ("p_transition", self.p_transition),
            ("p_slip", self.p_slip),
            ("p_guess", self.p_guess),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value}")


# Blueprint 16.3 gives P(L0)=0.20, P(T)=0.12, P(S)=0.10, P(G)=0.20 explicitly
# for 4-option MCQ; P(L0) is a prior on the *concept* (not per question
# type) so it lives here as a single constant. Numeric/short-answer aren't
# in the blueprint's worked example — their guess probability is set much
# lower (you can't luck into the right numeric value the way you can pick
# 1-of-4 options) and short-answer's slip is a little higher (LLM grading
# of free text is noisier than exact-match grading). See
# docs/adr/0006-learner-model-simplifications.md.
BOOTSTRAP_PRIOR_MASTERY = 0.20

BKT_PARAMS_BY_QUESTION_TYPE: dict[str, BktParams] = {
    "mcq": BktParams(p_transition=0.12, p_slip=0.10, p_guess=0.20),
    "numeric": BktParams(p_transition=0.12, p_slip=0.10, p_guess=0.05),
    "short_answer": BktParams(p_transition=0.12, p_slip=0.15, p_guess=0.05),
}


def _posterior_correct(p_mastery: float, params: BktParams) -> float:
    numerator = p_mastery * (1 - params.p_slip)
    denominator = numerator + (1 - p_mastery) * params.p_guess
    return numerator / denominator if denominator > 0 else p_mastery


def _posterior_incorrect(p_mastery: float, params: BktParams) -> float:
    numerator = p_mastery * params.p_slip
    denominator = numerator + (1 - p_mastery) * (1 - params.p_guess)
    return numerator / denominator if denominator > 0 else p_mastery


def update_mastery(p_mastery: float, *, score: float, params: BktParams) -> float:
    """Blueprint 16.2's two update rules, generalized to partial credit
    (16.4): `score` in [0, 1] interpolates between the "incorrect" and
    "correct" posterior rather than rounding everything to a coin flip.
    score=1.0 and score=0.0 reduce exactly to the blueprint's two cases.
    """
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"score must be in [0, 1], got {score}")
    if not 0.0 <= p_mastery <= 1.0:
        raise ValueError(f"p_mastery must be in [0, 1], got {p_mastery}")

    p_correct = _posterior_correct(p_mastery, params)
    p_incorrect = _posterior_incorrect(p_mastery, params)
    p_post = score * p_correct + (1 - score) * p_incorrect
    return p_post + (1 - p_post) * params.p_transition
