# backend/app/models/refresh_token_blocklist.py
# SQLAlchemy ORM model for the refresh_token_blocklist table.
# D-04: Server-side refresh token invalidation on logout (AUTH-04, T-02-04).
# Table was created by migration 001_initial_schema.py.
#
# Design: table stores ONLY blocked tokens.
#   - A token NOT in this table is valid.
#   - A token IN this table is invalidated (must be rejected at /auth/refresh).
# On logout: INSERT the token hash.
# On refresh: SELECT — if row found, reject with 401.

import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class RefreshTokenBlocklist(Base):
    """Stores SHA-256 hashes of refresh tokens invalidated on logout."""
    __tablename__ = "refresh_token_blocklist"

    id: Mapped[int] = mapped_column(primary_key=True)
    # SHA-256 hex digest of the raw refresh token string (64 chars)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
