from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.base_class import utc_now
from app.models.enums import EvidenceStatus, Severity
from app.models.integrity_event import IntegrityEvent


class IntegrityEventCreate(BaseModel):
    event_type: str = Field(default="APP_FOCUS_LOST", max_length=64)
    severity: str = Field(default=Severity.MEDIUM.value, max_length=32)
    confidence: float | None = Field(default=None, ge=0, le=1)
    priority_score: int = Field(default=5, ge=0, le=100)
    occurred_at: datetime = Field(default_factory=utc_now)
    evidence_status: str = Field(default=EvidenceStatus.NOT_REQUIRED.value, max_length=32)
    metadata: dict[str, Any] = Field(default_factory=dict)


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
        )
