from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base, TimestampedUuidMixin


class IdentityReference(TimestampedUuidMixin, Base):
    """University-supplied reference photo for one candidate account."""

    __tablename__ = "identity_references"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    relative_path: Mapped[str] = mapped_column(String(255))
    sha256_hash: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(255), default="university_import")

    user = relationship("User")
