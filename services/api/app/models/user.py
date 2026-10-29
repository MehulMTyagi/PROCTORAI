from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base, TimestampedUuidMixin
from app.models.enums import UserRole


class User(TimestampedUuidMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default=UserRole.CANDIDATE.value)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    roll_number: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    program: Mapped[str | None] = mapped_column(String(100), index=True)
    admission_year: Mapped[int | None] = mapped_column(Integer, index=True)
    section: Mapped[str | None] = mapped_column(String(100), index=True)
