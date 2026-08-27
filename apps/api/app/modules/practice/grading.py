"""Deterministic graders (blueprint section 14.2's grading order: exact/
deterministic first). MCQ and numeric never need an LLM call; only short
answer does (see service.py) — matching blueprint section 3.5's principle
of using an LLM only when the problem actually requires it.
"""

from app.modules.practice.models import Correctness


def grade_mcq(*, correct_option_id: str, selected_option_id: str) -> tuple[str, float]:
    if selected_option_id == correct_option_id:
        return Correctness.CORRECT.value, 1.0
    return Correctness.INCORRECT.value, 0.0


def grade_numeric(*, correct_value: float, tolerance: float, submitted_value: float) -> tuple[str, float]:
    if abs(submitted_value - correct_value) <= max(tolerance, 0.0):
        return Correctness.CORRECT.value, 1.0
    return Correctness.INCORRECT.value, 0.0
