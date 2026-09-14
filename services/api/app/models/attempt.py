import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampedUuidMixin
from app.models.enums import AttemptStatus


class Attempt(TimestampedUuidMixin, Base):
    __tablename__ = "attempts"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
    )
    status: Mapped[str] = mapped_column(String(32), default=AttemptStatus.NOT_STARTED.value)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    score: Mapped[int | None] = mapped_column(Integer)

    assessment = relationship("Assessment", back_populates="attempts")
    candidate = relationship("User")
    answers = relationship("Answer", back_populates="attempt", cascade="all, delete-orphan")
    integrity_events = relationship(
        "IntegrityEvent",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )


class Answer(TimestampedUuidMixin, Base):
    __tablename__ = "answers"

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attempts.id", ondelete="CASCADE"),
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
    )
    answer_text: Mapped[str | None] = mapped_column(Text)
    selected_option: Mapped[str | None] = mapped_column(String(255))
    score_awarded: Mapped[int | None] = mapped_column(Integer)

    attempt = relationship("Attempt", back_populates="answers")
    question = relationship("Question")
