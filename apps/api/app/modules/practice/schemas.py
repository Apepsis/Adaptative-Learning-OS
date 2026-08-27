import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

QuestionTypeLiteral = Literal["mcq", "numeric", "short_answer"]


class QuestionOption(BaseModel):
    id: str
    text: str


class QuestionCreate(BaseModel):
    concept_id: uuid.UUID | None = None
    question_type: QuestionTypeLiteral
    stem: str = Field(min_length=1, max_length=4000)
    options: list[QuestionOption] | None = None
    correct_option_id: str | None = None
    numeric_answer: float | None = None
    numeric_tolerance: float | None = None
    units: str | None = None
    sample_answer: str | None = None
    hints: list[str] | None = None
    solution_text: str | None = None


class QuestionRead(BaseModel):
    """Full view, including the answer key — for bank management, never
    served during an active practice attempt (see QuestionPracticeView)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    subject_id: uuid.UUID
    concept_id: uuid.UUID | None
    origin: str
    question_type: str
    stem: str
    options: list[QuestionOption] | None
    correct_option_id: str | None
    numeric_answer: float | None
    numeric_tolerance: float | None
    units: str | None
    sample_answer: str | None
    hints: list[str] | None
    solution_text: str | None
    verification_state: str
    created_at: datetime


class QuestionPracticeView(BaseModel):
    """What's shown while actively answering — no answer key, no solution,
    no hints beyond how many exist (blueprint section 20.5: hints are
    revealed one at a time via a dedicated endpoint, not all at once)."""

    id: uuid.UUID
    question_type: str
    stem: str
    options: list[QuestionOption] | None
    units: str | None
    hint_count: int


class QuestionListResponse(BaseModel):
    items: list[QuestionRead]
    total: int


class GenerateQuestionsRequest(BaseModel):
    concept_id: uuid.UUID
    question_type: QuestionTypeLiteral
    count: int = Field(default=3, ge=1, le=10)


class GenerateQuestionsResponse(BaseModel):
    items: list[QuestionRead]


class PracticeSessionCreate(BaseModel):
    concept_ids: list[uuid.UUID] | None = None
    question_count: int = Field(default=10, ge=1, le=50)


class PracticeSessionRead(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    total_questions: int
    current_index: int
    completed_at: datetime | None


class PracticeSessionCurrent(BaseModel):
    session: PracticeSessionRead
    question: QuestionPracticeView | None  # None when the session is complete


class SubmitAttemptRequest(BaseModel):
    question_id: uuid.UUID
    session_id: uuid.UUID | None = None
    raw_answer: dict[str, Any]
    elapsed_ms: int | None = Field(default=None, ge=0)
    hints_used: int = Field(default=0, ge=0)
    solution_revealed: bool = False


class AttemptErrorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    error_type: str
    explanation: str


class AttemptResult(BaseModel):
    id: uuid.UUID
    correctness: str
    score: float
    max_score: float
    feedback: str | None
    correct_option_id: str | None
    numeric_answer: float | None
    sample_answer: str | None
    solution_text: str | None
    errors: list[AttemptErrorRead]


class HintResponse(BaseModel):
    hint_text: str | None
    hints_used: int
    hints_remaining: int
