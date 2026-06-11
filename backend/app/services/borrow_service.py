# backend/app/services/borrow_service.py
# Business logic for borrow/return workflow.
#
# Domain rules:
#   - BR-01: Borrow request succeeds only if available_copies > 0.
#   - BR-02: Approving a request creates a Loan and decrements available_copies.
#   - BR-03: Returning a loan marks it returned and increments available_copies.
#   - BR-04: 14-day fixed borrow period (CLAUDE.md constraint — no configurable periods in v1).
#   - CP-1: DB-level CHECK ensures available_copies never goes negative (constraint enforcement).
#   - Atomicity: all multi-step operations use a single session commit.

import datetime
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.borrow_request import BorrowRequest
from app.models.loan import Loan
from app.models.user import User

MAX_CONCURRENT_LOANS = 5
LOAN_PERIOD_DAYS = 14  # Fixed 14-day borrow period (CLAUDE.md constraint)


async def create_borrow_request(db: AsyncSession, student_id: int, book_id: int) -> BorrowRequest:
    # Check for pending request for same student+book
    dup_res = await db.execute(
        select(BorrowRequest).where(
            BorrowRequest.student_id == student_id,
            BorrowRequest.book_id == book_id,
            BorrowRequest.status == 'pending'
        )
    )
    if dup_res.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already have a pending request for this book")

    dup_loan_res = await db.execute(
        select(Loan).where(
            Loan.student_id == student_id,
            Loan.book_id == book_id,
            Loan.status == 'active'
        )
    )
    if dup_loan_res.first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already have an active loan for this book")

    # Ensure book exists
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    # BR-01: availability check
    if book.available_copies <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No copies available")

    br = BorrowRequest(
        student_id=student_id,
        book_id=book_id,
        status="pending",
        requested_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(br)
    await db.commit()
    await db.refresh(br)
    return br


async def approve_borrow_request(db: AsyncSession, borrow_request_id: int, reviewer_id: int) -> int:
    # Transactional approval: lock book row and borrow_request row, check rules, create Loan
    async with db.begin():
        # Load borrow request
        res = await db.execute(select(BorrowRequest).where(BorrowRequest.id == borrow_request_id).with_for_update())
        br = res.scalar_one_or_none()
        if not br:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrow request not found")
        if br.status != "pending":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Borrow request not pending")

        # Check student's active loans against max concurrent limit
        cnt_res = await db.execute(select(func.count()).select_from(Loan).where(Loan.student_id == br.student_id, Loan.status == 'active'))
        (active_count,) = cnt_res.first()
        if active_count is None:
            active_count = 0
        if active_count >= MAX_CONCURRENT_LOANS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Student has reached max concurrent loans ({MAX_CONCURRENT_LOANS})")

        # Lock book row — CP-1: DB CHECK also enforces this
        book_res = await db.execute(select(Book).where(Book.id == br.book_id).with_for_update())
        book = book_res.scalar_one_or_none()
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        if book.available_copies <= 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No available copies to approve request")

        # Decrement available copies
        book.available_copies -= 1

        # Update borrow request
        br.status = 'approved'
        br.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
        br.reviewed_by = reviewer_id

        # Create Loan — BR-04: fixed 14-day period
        now = datetime.datetime.now(datetime.timezone.utc)
        due = now + datetime.timedelta(days=LOAN_PERIOD_DAYS)
        loan = Loan(
            borrow_request_id=br.id,
            student_id=br.student_id,
            book_id=br.book_id,
            status='active',
            loan_date=now,
            due_date=due,
        )
        db.add(loan)
        # Commit happens on context exit

    # Refresh loan outside transaction to ensure it's available
    await db.refresh(loan)

    # Send notification
    user_res = await db.execute(select(User).where(User.id == loan.student_id))
    student = user_res.scalar_one_or_none()
    if student:
        from app.services.notification_service import send_borrow_status_notification
        import asyncio
        asyncio.create_task(send_borrow_status_notification(student.email, "approved", loan.book_id))

    return loan.id


async def reject_borrow_request(db: AsyncSession, borrow_request_id: int, reviewer_id: int, rejection_note: str | None = None) -> None:
    async with db.begin():
        res = await db.execute(select(BorrowRequest).where(BorrowRequest.id == borrow_request_id).with_for_update())
        br = res.scalar_one_or_none()
        if not br:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrow request not found")
        if br.status != 'pending':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Borrow request not pending")
        br.status = 'rejected'
        br.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
        br.reviewed_by = reviewer_id
        br.rejection_note = rejection_note

        student_id = br.student_id
        book_id = br.book_id

    # Send notification
    user_res = await db.execute(select(User).where(User.id == student_id))
    student = user_res.scalar_one_or_none()
    if student:
        from app.services.notification_service import send_borrow_status_notification
        import asyncio
        asyncio.create_task(send_borrow_status_notification(student.email, "rejected", book_id, rejection_note))
    return


async def return_loan(
    db: AsyncSession,
    loan_id: int,
) -> Loan:
    """BR-03: Record the return of an active loan."""
    loan = await db.get(Loan, loan_id)
    if not loan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
    if loan.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Loan is already {loan.status}")

    book = await db.get(Book, loan.book_id)
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

    now = datetime.datetime.now(datetime.timezone.utc)
    loan.status = "returned"
    loan.returned_at = now

    # Restore availability — cap at total_copies
    book.available_copies = min(book.available_copies + 1, book.total_copies)

    await db.commit()
    await db.refresh(loan)
    return loan


async def get_borrow_requests(
    db: AsyncSession,
    student_id: Optional[int] = None,
    status: Optional[str] = None,
) -> list[BorrowRequest]:
    """List borrow requests. Optionally filter by student_id or status."""
    stmt = select(BorrowRequest).order_by(BorrowRequest.requested_at.desc())
    if student_id is not None:
        stmt = stmt.where(BorrowRequest.student_id == student_id)
    if status is not None:
        stmt = stmt.where(BorrowRequest.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_loans(
    db: AsyncSession,
    student_id: Optional[int] = None,
    status: Optional[str] = None,
) -> list[Loan]:
    """List loans. Optionally filter by student_id or status."""
    stmt = select(Loan).order_by(Loan.loan_date.desc())
    if student_id is not None:
        stmt = stmt.where(Loan.student_id == student_id)
    if status is not None:
        stmt = stmt.where(Loan.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())
