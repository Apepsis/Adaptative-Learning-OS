from app.modules.practice.grading import grade_mcq, grade_numeric


def test_mcq_correct_selection() -> None:
    correctness, score = grade_mcq(correct_option_id="b", selected_option_id="b")
    assert correctness == "correct"
    assert score == 1.0


def test_mcq_incorrect_selection() -> None:
    correctness, score = grade_mcq(correct_option_id="b", selected_option_id="a")
    assert correctness == "incorrect"
    assert score == 0.0


def test_numeric_within_tolerance_is_correct() -> None:
    correctness, score = grade_numeric(correct_value=9.8, tolerance=0.1, submitted_value=9.85)
    assert correctness == "correct"
    assert score == 1.0


def test_numeric_outside_tolerance_is_incorrect() -> None:
    correctness, score = grade_numeric(correct_value=9.8, tolerance=0.1, submitted_value=10.5)
    assert correctness == "incorrect"
    assert score == 0.0


def test_numeric_exact_match_with_zero_tolerance() -> None:
    correctness, _ = grade_numeric(correct_value=42.0, tolerance=0.0, submitted_value=42.0)
    assert correctness == "correct"


def test_numeric_boundary_is_inclusive() -> None:
    correctness, _ = grade_numeric(correct_value=10.0, tolerance=0.5, submitted_value=10.5)
    assert correctness == "correct"


def test_numeric_just_outside_boundary_is_incorrect() -> None:
    correctness, _ = grade_numeric(correct_value=10.0, tolerance=0.5, submitted_value=10.51)
    assert correctness == "incorrect"


def test_negative_tolerance_is_treated_as_zero() -> None:
    # A negative tolerance would be a data error, not a reason to accept a
    # wider range than an exact match.
    correctness, _ = grade_numeric(correct_value=5.0, tolerance=-1.0, submitted_value=5.0)
    assert correctness == "correct"
    correctness, _ = grade_numeric(correct_value=5.0, tolerance=-1.0, submitted_value=5.5)
    assert correctness == "incorrect"
