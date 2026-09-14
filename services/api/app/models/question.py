import uuid
from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampedUuidMixin
from app.models.enums import QuestionType


class Question(TimestampedUuidMixin, Base):
    __tablename__ = "questions"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
    )
    prompt: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String(32), default=QuestionType.MCQ.value)
    options: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    correct_answer: Mapped[str | None] = mapped_column(Text)
    points: Mapped[int] = mapped_column(Integer, default=1)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    assessment = relationship("Assessment", back_populates="questions")
