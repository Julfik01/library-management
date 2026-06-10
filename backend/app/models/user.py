# backend/app/models/user.py
# Defines DeclarativeBase (imported by all other models) and User model.
# PATTERNS.md: SQLAlchemy 2.0 Mapped types pattern.

import datetime

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared DeclarativeBase — all models import this."""
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    # FastAPI docs convention: hashed_password (CONTEXT.md discretion)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # D-03: full_name required for Phase 4 loan search by student name
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # D-discretion: VARCHAR CHECK (not native ENUM) per CONTEXT.md D-05
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student")
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('student','librarian','admin_librarian')",
            name="ck_users_role",
        ),
    )
