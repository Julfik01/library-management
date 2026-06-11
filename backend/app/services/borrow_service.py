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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.borrow_request import BorrowRequest
from app.models.loan import Loan
from app.models.user import User

LOAN_PERIOD_DAYS = 14  # Fixed 14-day borrow period (CLAUDE.md constraint)


async def create_borrow_request(
    db: AsyncSession,
    student_id: int,
    book_id: int,
) -> BorrowRequest:
    """
    BR-01: Create a borrow request if the book exists and has available copies.

    Raises ValueError if:
      - Book not found
      - No copies available

    Students may only have one pending/active request per book (enforced here).
    """
    # Check book exists
    book = await db.get(Book, book_id)
    if not book:
        raise ValueError("Book not found")

    # BR-01: availability check
    if book.available_copies <= 0:
        raise ValueError("No copies available")

    # Prevent duplicate pending requests for same student+book
    result = await db.execute(
        select(BorrowRequest).where(
            BorrowRequest.student_id == student_id,
            BorrowRequest.book_id == book_id,
            BorrowRequest.status == "pending",
        )
    )
    if result.scalar_one_or_none():
        raise ValueError("You already have a pending request for this book")

    borrow_request = BorrowRequest(
        student_id=student_id,
        book_id=book_id,
        status="pending",
        requested_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(borrow_request)
    await db.commit()
    await db.refresh(borrow_request)
    return borrow_request


async def approve_borrow_request(
    db: AsyncSession,
    request_id: int,
    librarian_id: int,
) -> Loan:
    """
    BR-02: Approve a pending borrow request.
      - Sets request status to 'approved'
      - Creates a Loan with 14-day period
      - Decrements available_copies

    Raises ValueError if:
      - Request not found
      - Request already processed (not pending)
      - Book has no available copies (race condition guard)
    """
    borrow_request = await db.get(BorrowRequest, request_id)
    if not borrow_request:
        raise ValueError("Borrow request not found")
    if borrow_request.status != "pending":
        raise ValueError(f"Request is already {borrow_request.status}")

    book = await db.get(Book, borrow_request.book_id)
    if not book:
        raise ValueError("Book not found")

    # CP-1: Check availability (DB constraint is also a guard, but early check gives clearer error)
    if book.available_copies <= 0:
        raise ValueError("No copies available")

    now = datetime.datetime.now(datetime.timezone.utc)

    # Update request
    borrow_request.status = "approved"
    borrow_request.reviewed_at = now
    borrow_request.reviewed_by = librarian_id

    # Decrement availability — DB CHECK prevents going negative
    book.available_copies -= 1

    # Create Loan — BR-04: fixed 14-day period
    loan = Loan(
        borrow_request_id=borrow_request.id,
        student_id=borrow_request.student_id,
        book_id=borrow_request.book_id,
        status="active",
        loan_date=now,
        due_date=now + datetime.timedelta(days=LOAN_PERIOD_DAYS),
    )
    db.add(loan)
    await db.commit()
    await db.refresh(loan)
    return loan


async def reject_borrow_request(
    db: AsyncSession,
    request_id: int,
    librarian_id: int,
) -> BorrowRequest:
    """
    Reject a pending borrow request. Does not affect availability.

    Raises ValueError if:
      - Request not found
      - Request already processed (not pending)
    """
    borrow_request = await db.get(BorrowRequest, request_id)
    if not borrow_request:
        raise ValueError("Borrow request not found")
    if borrow_request.status != "pending":
        raise ValueError(f"Request is already {borrow_request.status}")

    now = datetime.datetime.now(datetime.timezone.utc)
    borrow_request.status = "rejected"
    borrow_request.reviewed_at = now
    borrow_request.reviewed_by = librarian_id
    await db.commit()
    await db.refresh(borrow_request)
    return borrow_request


async def return_loan(
    db: AsyncSession,
    loan_id: int,
) -> Loan:
    """
    BR-03: Record the return of an active loan.
      - Sets loan status to 'returned' and records returned_at timestamp
      - Increments available_copies

    Raises ValueError if:
      - Loan not found
      - Loan is not active (already returned or overdue-closed)
    """
    loan = await db.get(Loan, loan_id)
    if not loan:
        raise ValueError("Loan not found")
    if loan.status != "active":
        raise ValueError(f"Loan is already {loan.status}")

    book = await db.get(Book, loan.book_id)
    if not book:
        raise ValueError("Book not found")

    now = datetime.datetime.now(datetime.timezone.utc)
    loan.status = "returned"
    loan.returned_at = now

    # Restore availability
    book.available_copies = min(book.available_copies + 1, book.total_copies)

    await db.commit()
    await db.refresh(loan)
    return loan


async def get_borrow_requests(
    db: AsyncSession,
    student_id: Optional[int] = None,
    status: Optional[str] = None,
) -> list[BorrowRequest]:
    """
    List borrow requests. Optionally filter by student_id or status.
    Librarians see all; students see only their own (enforced by caller).
    """
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
    """
    List loans. Optionally filter by student_id or status.
    Librarians see all; students see only their own (enforced by caller).
    """
    stmt = select(Loan).order_by(Loan.loan_date.desc())
    if student_id is not None:
        stmt = stmt.where(Loan.student_id == student_id)
    if status is not None:
        stmt = stmt.where(Loan.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())
