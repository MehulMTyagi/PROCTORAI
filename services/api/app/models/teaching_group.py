import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampedUuidMixin


class TeachingGroupAssignment(TimestampedUuidMixin, Base):
    __tablename__ = "teaching_group_assignments"
    __table_args__ = (
        UniqueConstraint(
            "examiner_id",
            "program",
            "admission_year",
            "section",
            name="uq_examiner_teaching_group",
        ),
    )

    examiner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    program: Mapped[str] = mapped_column(String(100))
    admission_year: Mapped[int] = mapped_column(Integer)
    section: Mapped[str] = mapped_column(String(100))

    examiner = relationship("User")
