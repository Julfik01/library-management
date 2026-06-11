import datetime

import pytest

from app.models.book import Book
from app.models.user import User
from app.models.borrow_request import BorrowRequest
from app.models.loan import Loan
from app.services.borrow_service import create_borrow_request, approve_borrow_request
from app.services.loan_service import return_loan
from app.tasks.overdue_jobs import mark_overdue_once


async def test_return_idempotent(db_session):
    # Create student, librarian, and book
    student = User(email='s1@test', hashed_password='$argon2', full_name='S', role='student')
    librarian = User(email='l1@test', hashed_password='$argon2', full_name='L', role='librarian')
    book = Book(isbn='978-1', title='T', author='A', total_copies=2, available_copies=2)
    db_session.add_all([student, librarian, book])
    await db_session.commit()
    await db_session.refresh(student)
    await db_session.refresh(librarian)
    await db_session.refresh(book)

    # Student creates borrow request
    br = await create_borrow_request(db_session, student.id, book.id)
    await db_session.commit()  # Close the implicit transaction from refresh()
    
    # Librarian approves
    loan_id = await approve_borrow_request(db_session, br.id, reviewer_id=librarian.id)
    # Refresh loan
    loan = await db_session.get(Loan, loan_id)
    assert loan is not None
    await db_session.commit()
    # Return loan
    await return_loan(db_session, loan_id, student)
    returned_loan = await db_session.get(Loan, loan_id)
    assert returned_loan.returned_at is not None
    await db_session.commit()
    # available_copies incremented to 2 again
    b = await db_session.get(Book, book.id)
    assert b.available_copies == 2
    # Calling return again should be idempotent
    await return_loan(db_session, loan_id, student)
    b2 = await db_session.get(Book, book.id)
    assert b2.available_copies == 2


async def test_overdue_job_marks_and_notifies(db_session):
    # Create student and book and loan that is overdue
    student = User(email='s2@test', hashed_password='$argon2', full_name='S2', role='student')
    book = Book(isbn='978-2', title='T2', author='A2', total_copies=1, available_copies=0)
    db_session.add_all([student, book])
    await db_session.commit()
    await db_session.refresh(student)
    await db_session.refresh(book)

    # Create borrow_request and loan manually
    br = BorrowRequest(student_id=student.id, book_id=book.id, status='approved')
    db_session.add(br)
    await db_session.commit()
    await db_session.refresh(br)

    past = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
    loan = Loan(borrow_request_id=br.id, student_id=student.id, book_id=book.id, status='active', loan_date=past, due_date=past)
    db_session.add(loan)
    await db_session.commit()
    await db_session.refresh(loan)

    # Run job
    await mark_overdue_once(db_session)

    updated = await db_session.get(Loan, loan.id)
    assert updated.status == 'overdue'
    assert updated.overdue_notified_at is not None
