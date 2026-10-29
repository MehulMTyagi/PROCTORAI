from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.assessment import Assessment
from app.models.enums import AssessmentStatus, QuestionType
from app.models.question import Question


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    role: str
    roll_number: str | None = None
    program: str | None = None
    admission_year: int | None = None
    section: str | None = None


class AssessmentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    duration_minutes: int | None = Field(default=60, gt=0, le=480)
    status: AssessmentStatus = AssessmentStatus.DRAFT
    start_at: datetime | None = None
    end_at: datetime | None = None
    candidate_ids: list[UUID] = Field(default_factory=list, max_length=20_000)
    proctor_ids: list[UUID] = Field(default_factory=list, max_length=500)
    rules: dict[str, Any] = Field(default_factory=dict, max_length=100)


class AssessmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    duration_minutes: int | None = Field(default=None, gt=0, le=480)
    status: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None


class AssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    status: str
    duration_minutes: int | None
    start_at: datetime | None
    end_at: datetime | None
    created_by_id: UUID
    attempt_status: str | None = None


class QuestionCreate(BaseModel):
    prompt: str = Field(min_length=3, max_length=10_000)
    question_type: QuestionType = QuestionType.MCQ
    options: list[dict[str, Any]] | None = Field(default=None, max_length=50)
    correct_answer: str | None = Field(default=None, max_length=1_000)
    points: int = Field(default=1, gt=0, le=100)
    display_order: int = Field(default=0, ge=0)


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    assessment_id: UUID
    prompt: str
    question_type: str
    options: list[dict[str, Any]] | None
    correct_answer: str | None
    points: int
    display_order: int

    @classmethod
    def candidate_view(cls, question: Question) -> "QuestionResponse":
        return cls(
            id=question.id,
            assessment_id=question.assessment_id,
            prompt=question.prompt,
            question_type=question.question_type,
            options=question.options,
            correct_answer=None,
            points=question.points,
            display_order=question.display_order,
        )


class AssessmentDetailResponse(AssessmentResponse):
    questions: list[QuestionResponse] = Field(default_factory=list)
    rules: dict[str, Any] = Field(default_factory=dict)
    candidate_ids: list[UUID] = Field(default_factory=list)
    proctor_ids: list[UUID] = Field(default_factory=list)

    @classmethod
    def from_assessment(cls, assessment: Assessment) -> "AssessmentDetailResponse":
        return cls(
            id=assessment.id,
            title=assessment.title,
            description=assessment.description,
            status=assessment.status,
            duration_minutes=assessment.duration_minutes,
            start_at=assessment.start_at,
            end_at=assessment.end_at,
            created_by_id=assessment.created_by_id,
            questions=[
                QuestionResponse.model_validate(question)
                for question in sorted(assessment.questions, key=lambda item: item.display_order)
            ],
        )


class AssignmentRequest(BaseModel):
    user_id: UUID


class AssessmentAssignments(BaseModel):
    candidate_ids: list[UUID] = Field(default_factory=list, max_length=20_000)
    proctor_ids: list[UUID] = Field(default_factory=list, max_length=500)


class RuleUpdate(BaseModel):
    rules: dict[str, Any] = Field(default_factory=dict)
    config_version: str = "v1"
