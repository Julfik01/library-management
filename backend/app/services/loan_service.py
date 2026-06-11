# backend/app/services/loan_service.py
# Read helpers for student loan views and librarian loan search.

from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.loan import Loan
from app.models.user import User
from app.schemas.loan import LoanListItem, PaginatedLoansResponse

DEFAULT_PAGE_SIZE = 10
ACTIVE_STATUSES = ("active", "overdue")


def _loan_read_select():
    return (
        select(
            Loan.id.label("loan_id"),
            Book.title.label("book_title"),
            User.full_name.label("student_name"),
            Loan.loan_date,
            Loan.due_date,
            Loan.returned_at,
            Loan.status,
        )
        .join(User, Loan.student_id == User.id)
        .join(Book, Loan.book_id == Book.id)
    )


def _row_to_item(row) -> LoanListItem:
    status = str(row.status)
    return LoanListItem(
        id=row.loan_id,
        book_title=row.book_title,
        student_name=row.student_name,
        loan_date=row.loan_date,
        due_date=row.due_date,
        returned_at=row.returned_at,
        status=status,  # type: ignore[arg-type]
        is_overdue=status == "overdue",
        outcome=status,
    )


async def count_loans(db: AsyncSession, stmt: Select) -> int:
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = await db.scalar(count_stmt)
    return int(total or 0)


async def _paginate(
    db: AsyncSession,
    stmt: Select,
    page: int,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> PaginatedLoansResponse:
    effective_page_size = DEFAULT_PAGE_SIZE if page_size != DEFAULT_PAGE_SIZE else page_size
    total_items = await count_loans(db, stmt)
    total_pages = max(1, math.ceil(total_items / effective_page_size))
    offset = (page - 1) * effective_page_size
    result = await db.execute(
        stmt.limit(effective_page_size).offset(offset)
    )
    items = [_row_to_item(row) for row in result.all()]
    return PaginatedLoansResponse(
        page=page,
        page_size=effective_page_size,
        total_items=total_items,
        total_pages=total_pages,
        items=items,
    )


async def list_student_loans(
    db: AsyncSession,
    student_id: int,
    status: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> PaginatedLoansResponse:
    if status == "active":
        stmt = (
            _loan_read_select()
            .where(
                Loan.student_id == student_id,
                Loan.status.in_(ACTIVE_STATUSES),
            )
            .order_by(Loan.due_date.asc(), Loan.loan_date.asc(), Loan.id.asc())
        )
    elif status == "history":
        stmt = (
            _loan_read_select()
            .where(
                Loan.student_id == student_id,
                Loan.status == "returned",
            )
            .order_by(Loan.loan_date.desc(), Loan.id.desc())
        )
    else:
        raise ValueError("status must be 'active' or 'history'")

    return await _paginate(db, stmt, page, page_size)


async def search_loans(
    db: AsyncSession,
    q: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> PaginatedLoansResponse:
    search_text = q.strip()
    if not search_text:
        return PaginatedLoansResponse(
            page=page,
            page_size=DEFAULT_PAGE_SIZE,
            total_items=0,
            total_pages=1,
            items=[],
        )

    like = f"%{search_text}%"
    stmt = (
        _loan_read_select()
        .where(
            or_(
                User.full_name.ilike(like),
                Book.title.ilike(like),
            )
        )
        .order_by(Loan.loan_date.desc(), Loan.id.desc())
    )
    return await _paginate(db, stmt, page, page_size)
