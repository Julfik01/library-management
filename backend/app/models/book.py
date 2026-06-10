# backend/app/models/book.py
# Book model — tracks copy inventory with DB-level correctness constraints (CP-1).
# Note: GIN full-text index is created in the Alembic migration, not here.

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    isbn: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    total_copies: Mapped[int] = mapped_column(Integer, nullable=False)
    # CP-1: correctness constraints prevent negative/over-total available copies
    available_copies: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("available_copies >= 0", name="ck_books_available_nonnegative"),
        CheckConstraint(
            "available_copies <= total_copies", name="ck_books_available_lte_total"
        ),
        # D-07: GIN full-text index for catalog search (CAT-05) — created in Alembic migration
    )
