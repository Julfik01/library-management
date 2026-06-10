# backend/app/models/loan.py
# Loan model — active/returned/overdue loans with 14-day fixed period.
# D-05: VARCHAR + CHECK for status. D-06: overdue_notified_at for idempotent email.

import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.user import Base


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    borrow_request_id: Mapped[int] = mapped_column(
        ForeignKey("borrow_requests.id"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    # D-05: VARCHAR CHECK for status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    loan_date: Mapped[datetime.datetime] = mapped_column(nullable=False)
    # Fixed 14-day borrow period (CLAUDE.md constraint — no configurable periods in v1)
    due_date: Mapped[datetime.datetime] = mapped_column(nullable=False)
    returned_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    # D-06: NULL = not notified; timestamp = first overdue email sent (idempotent sentinel)
    overdue_notified_at: Mapped[datetime.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('active','returned','overdue')", name="ck_loans_status"
        ),
    )
