import datetime

from fastapi import HTTPException, status
from sqlalchemy import select

from app.models.loan import Loan
from app.models.book import Book
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession


async def list_loans(db: AsyncSession, current_user: User, status: str | None = None):
    stmt = select(Loan)
    if current_user.role != "librarian":
        stmt = stmt.where(Loan.student_id == current_user.id)
    if status:
        stmt = stmt.where(Loan.status == status)
    res = await db.execute(stmt)
    return res.scalars().all()


async def return_loan(db: AsyncSession, loan_id: int, current_user: User):
    async with db.begin():
        res = await db.execute(select(Loan).where(Loan.id == loan_id).with_for_update())
        loan = res.scalar_one_or_none()
        if not loan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loan not found")
        # Authorization: student who owns loan or librarian
        if current_user.role != "librarian" and loan.student_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to return this loan")
        if loan.returned_at is not None:
            # idempotent
            return
        # Lock book row
        book_res = await db.execute(select(Book).where(Book.id == loan.book_id).with_for_update())
        book = book_res.scalar_one_or_none()
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        # Mark returned
        now = datetime.datetime.now(datetime.timezone.utc)
        loan.returned_at = now
        loan.status = 'returned'
        # Increment available copies
        book.available_copies += 1
    return
