from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.base_class import utc_now
from app.models.attempt import Answer, Attempt
from app.models.session_health import SessionHeartbeat


class AttemptStartRequest(BaseModel):
    assessment_id: UUID


class AttemptStartResponse(BaseModel):
    attempt_id: UUID
    assessment_id: UUID
    status: str


class AnswerSaveRequest(BaseModel):
    question_id: UUID
    answer_text: str | None = None
    selected_option: str | None = None


class AnswerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attempt_id: UUID
    question_id: UUID
    answer_text: str | None
    selected_option: str | None
    score_awarded: int | None


class AttemptDetailResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    candidate_id: UUID
    status: str
    started_at: datetime | None
    submitted_at: datetime | None
    score: int | None
    answers: list[AnswerResponse] = Field(default_factory=list)

    @classmethod
    def from_attempt(cls, attempt: Attempt) -> "AttemptDetailResponse":
        return cls(
            id=attempt.id,
            assessment_id=attempt.assessment_id,
            candidate_id=attempt.candidate_id,
            status=attempt.status,
            started_at=attempt.started_at,
            submitted_at=attempt.submitted_at,
            score=attempt.score,
            answers=[AnswerResponse.model_validate(answer) for answer in attempt.answers],
        )


class SubmitResponse(BaseModel):
    attempt_id: UUID
    status: str
    score: int
    total_points: int
    answers: list[AnswerResponse]


class SessionHeartbeatCreate(BaseModel):
    client_sent_at: datetime = Field(default_factory=utc_now)
    status: str = Field(default="OK", max_length=32)
    metrics: dict[str, object] = Field(default_factory=dict)


class SessionHeartbeatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attempt_id: UUID
    client_sent_at: datetime
    server_received_at: datetime
    status: str
    metrics: dict[str, object]

    @classmethod
    def from_heartbeat(cls, heartbeat: SessionHeartbeat) -> "SessionHeartbeatResponse":
        return cls.model_validate(heartbeat)
