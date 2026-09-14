import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampedUuidMixin, utc_now
from app.models.enums import ReviewDecision


class EventReview(TimestampedUuidMixin, Base):
    __tablename__ = "event_reviews"

    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("integrity_events.id", ondelete="CASCADE"),
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    decision: Mapped[str] = mapped_column(String(32), default=ReviewDecision.INCONCLUSIVE.value)
    note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    event = relationship("IntegrityEvent", back_populates="reviews")
    reviewer = relationship("User")
