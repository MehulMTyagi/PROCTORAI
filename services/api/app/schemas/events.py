from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.base_class import utc_now
from app.models.evidence import EvidenceFile
from app.models.enums import EvidenceStatus, ReviewDecision, Severity
from app.models.integrity_event import IntegrityEvent
from app.models.review import EventReview


class EvidenceFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    attempt_id: UUID
    kind: str
    original_filename: str | None
    mime_type: str
    sha256_hash: str
    size_bytes: int
    duration_ms: int | None
    captured_start_at: datetime | None
    captured_end_at: datetime | None
    retention_until: datetime | None
    download_url: str

    @classmethod
    def from_file(cls, evidence_file: EvidenceFile) -> "EvidenceFileResponse":
        return cls(
            id=evidence_file.id,
            event_id=evidence_file.event_id,
            attempt_id=evidence_file.attempt_id,
            kind=evidence_file.kind,
            original_filename=evidence_file.original_filename,
            mime_type=evidence_file.mime_type,
            sha256_hash=evidence_file.sha256_hash,
            size_bytes=evidence_file.size_bytes,
            duration_ms=evidence_file.duration_ms,
            captured_start_at=evidence_file.captured_start_at,
            captured_end_at=evidence_file.captured_end_at,
            retention_until=evidence_file.retention_until,
            download_url=f"/proctor/events/{evidence_file.event_id}/evidence/{evidence_file.id}",
        )


class IntegrityEventCreate(BaseModel):
    event_type: str = Field(default="APP_FOCUS_LOST", max_length=64)
    severity: str = Field(default=Severity.MEDIUM.value, max_length=32)
    confidence: float | None = Field(default=None, ge=0, le=1)
    priority_score: int = Field(default=5, ge=0, le=100)
    occurred_at: datetime = Field(default_factory=utc_now)
    evidence_status: str = Field(default=EvidenceStatus.NOT_REQUIRED.value, max_length=32)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceFailureCreate(BaseModel):
    reason: str = Field(default="upload_failed", max_length=128)
    detail: str | None = Field(default=None, max_length=1000)


class EventReviewCreate(BaseModel):
    decision: str = Field(default=ReviewDecision.INCONCLUSIVE.value, max_length=32)
    note: str | None = Field(default=None, max_length=1000)


class EventReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: UUID
    reviewer_id: UUID
    decision: str
    note: str | None
    reviewed_at: datetime

    @classmethod
    def from_review(cls, review: EventReview) -> "EventReviewResponse":
        return cls(
            id=review.id,
            event_id=review.event_id,
            reviewer_id=review.reviewer_id,
            decision=review.decision,
            note=review.note,
            reviewed_at=review.reviewed_at,
        )


class IntegrityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    attempt_id: UUID
    assessment_id: UUID
    event_type: str
    status: str
    severity: str
    confidence: float | None
    priority_score: int
    occurred_at: datetime
    received_at: datetime
    evidence_status: str
    metadata: dict[str, Any]
    evidence_files: list[EvidenceFileResponse] = Field(default_factory=list)
    reviews: list[EventReviewResponse] = Field(default_factory=list)

    @classmethod
    def from_event(cls, event: IntegrityEvent, assessment_id: UUID) -> "IntegrityEventResponse":
        return cls(
            id=event.id,
            attempt_id=event.attempt_id,
            assessment_id=assessment_id,
            event_type=event.event_type,
            status=event.status,
            severity=event.severity,
            confidence=event.confidence,
            priority_score=event.priority_score,
            occurred_at=event.occurred_at,
            received_at=event.received_at,
            evidence_status=event.evidence_status,
            metadata=event.payload,
            evidence_files=[EvidenceFileResponse.from_file(item) for item in event.evidence_files],
            reviews=[EventReviewResponse.from_review(item) for item in event.reviews],
        )
