import datetime

from fastapi import HTTPException, status
from sqlalchemy import select, func, or_
from app.models.user import User

from app.models.book import Book
from app.models.borrow_request import BorrowRequest
from app.models.loan import Loan
from sqlalchemy.ext.asyncio import AsyncSession

# Business constants
MAX_CONCURRENT_LOANS = 5
LOAN_PERIOD_DAYS = 14


async def create_borrow_request(db: AsyncSession, student_id: int, book_id: int) -> BorrowRequest:
    # Check for active loans or pending requests for the same book
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

    br = BorrowRequest(student_id=student_id, book_id=book_id)
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

        # Check student's active loans
        cnt_res = await db.execute(select(func.count()).select_from(Loan).where(Loan.student_id == br.student_id, Loan.status == 'active'))
        (active_count,) = cnt_res.first()
        if active_count is None:
            active_count = 0
        if active_count >= MAX_CONCURRENT_LOANS:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Student has reached max concurrent loans ({MAX_CONCURRENT_LOANS})")

        # Lock book row
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

        # Create Loan
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
