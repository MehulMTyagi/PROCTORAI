import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampedUuidMixin, utc_now
from app.models.enums import EventStatus, EvidenceStatus, Severity


class IntegrityEvent(TimestampedUuidMixin, Base):
    __tablename__ = "integrity_events"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attempts.id", ondelete="CASCADE"),
    )
    event_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default=EventStatus.DETECTED.value)
    severity: Mapped[str] = mapped_column(String(32), default=Severity.LOW.value)
    confidence: Mapped[float | None] = mapped_column(Float)
    priority_score: Mapped[int] = mapped_column(Integer, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    evidence_status: Mapped[str] = mapped_column(String(32), default=EvidenceStatus.NOT_REQUIRED.value)
    payload: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)

    attempt = relationship("Attempt", back_populates="integrity_events")
    evidence_files = relationship("EvidenceFile", back_populates="event", cascade="all, delete-orphan")
    reviews = relationship("EventReview", back_populates="event", cascade="all, delete-orphan")
