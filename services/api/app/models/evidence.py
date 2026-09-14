import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampedUuidMixin
from app.models.enums import EvidenceKind


class EvidenceFile(TimestampedUuidMixin, Base):
    __tablename__ = "evidence_files"

    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("integrity_events.id", ondelete="CASCADE"),
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("attempts.id", ondelete="CASCADE"),
    )
    kind: Mapped[str] = mapped_column(String(32), default=EvidenceKind.LOG.value)
    storage_key: Mapped[str] = mapped_column(String(512))
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(128))
    sha256_hash: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    captured_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    event = relationship("IntegrityEvent", back_populates="evidence_files")
