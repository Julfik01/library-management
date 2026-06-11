# backend/tests/test_loan_service.py
# Service-level tests for loan read helpers: ordering, filtering, and pagination metadata.
# Phase 4 — LOAN-02, LOAN-03, LOAN-04, LOAN-05

import datetime

import pytest
import pytest_asyncio
from sqlalchemy import text

from app.models.book import Book
from app.models.borrow_request import BorrowRequest
from app.models.loan import Loan
from app.models.user import User
from app.services.loan_service import DEFAULT_PAGE_SIZE, list_student_loans, search_loans

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime.datetime(2026, 6, 11, 12, 0, 0, tzinfo=datetime.timezone.utc)
DAY = datetime.timedelta(days=1)


async def _make_user(db, *, email: str, role: str = "student") -> User:
    user = User(
        email=email,
        hashed_password="hashed",
        full_name=email.split("@")[0].replace(".", " ").title(),
        role=role,
    )
    db.add(user)
    await db.flush()
    return user


async def _make_book(db, *, title: str) -> Book:
    book = Book(
        title=title,
        author="Author",
        isbn=f"ISBN-{title[:5]}",
        total_copies=5,
        available_copies=5,
    )
    db.add(book)
    await db.flush()
    return book


async def _make_borrow_request(db, *, student: User, book: Book) -> BorrowRequest:
    br = BorrowRequest(
        student_id=student.id,
        book_id=book.id,
        status="approved",
    )
    db.add(br)
    await db.flush()
    return br


async def _make_loan(
    db,
    *,
    student: User,
    book: Book,
    borrow_request: BorrowRequest,
    status: str = "active",
    loan_date: datetime.datetime,
    due_date: datetime.datetime,
    returned_at: datetime.datetime | None = None,
) -> Loan:
    loan = Loan(
        student_id=student.id,
        book_id=book.id,
        borrow_request_id=borrow_request.id,
        status=status,
        loan_date=loan_date,
        due_date=due_date,
        returned_at=returned_at,
    )
    db.add(loan)
    await db.flush()
    return loan


# ---------------------------------------------------------------------------
# list_student_loans — active view
# ---------------------------------------------------------------------------


class TestListStudentLoansActive:
    @pytest.mark.asyncio
    async def test_active_loans_sorted_by_due_soonest_first(self, db_session):
        """Active loans must sort by due_date ASC (soonest due first)."""
        student = await _make_user(db_session, email="alice@test.com")
        book1 = await _make_book(db_session, title="Book Alpha")
        book2 = await _make_book(db_session, title="Book Beta")
        br1 = await _make_borrow_request(db_session, student=student, book=book1)
        br2 = await _make_borrow_request(db_session, student=student, book=book2)

        # Loan2 is due sooner than loan1
        loan_date = NOW - 3 * DAY
        _loan1 = await _make_loan(
            db_session,
            student=student,
            book=book1,
            borrow_request=br1,
            loan_date=loan_date,
            due_date=NOW + 10 * DAY,
        )
        _loan2 = await _make_loan(
            db_session,
            student=student,
            book=book2,
            borrow_request=br2,
            loan_date=loan_date,
            due_date=NOW + 2 * DAY,
        )
        await db_session.commit()

        result = await list_student_loans(db_session, student_id=student.id, status="active")
        assert len(result.items) == 2
        # Soonest due first — book2 (due +2d) before book1 (due +10d)
        assert result.items[0].book_title == "Book Beta"
        assert result.items[1].book_title == "Book Alpha"

    @pytest.mark.asyncio
    async def test_active_view_excludes_returned_loans(self, db_session):
        """Returned loans must not appear in the active view."""
        student = await _make_user(db_session, email="bob@test.com")
        book = await _make_book(db_session, title="Gone Book")
        br = await _make_borrow_request(db_session, student=student, book=book)

        await _make_loan(
            db_session,
            student=student,
            book=book,
            borrow_request=br,
            status="returned",
            loan_date=NOW - 20 * DAY,
            due_date=NOW - 6 * DAY,
            returned_at=NOW - 5 * DAY,
        )
        await db_session.commit()

        result = await list_student_loans(db_session, student_id=student.id, status="active")
        assert result.items == []
        assert result.total_items == 0

    @pytest.mark.asyncio
    async def test_overdue_loans_appear_in_active_view(self, db_session):
        """Overdue loans are a sub-state of active and must appear in the active view."""
        student = await _make_user(db_session, email="carol@test.com")
        book = await _make_book(db_session, title="Overdue Book")
        br = await _make_borrow_request(db_session, student=student, book=book)

        await _make_loan(
            db_session,
            student=student,
            book=book,
            borrow_request=br,
            status="overdue",
            loan_date=NOW - 20 * DAY,
            due_date=NOW - 6 * DAY,
        )
        await db_session.commit()

        result = await list_student_loans(db_session, student_id=student.id, status="active")
        assert len(result.items) == 1
        assert result.items[0].is_overdue is True

    @pytest.mark.asyncio
    async def test_active_view_scoped_to_student(self, db_session):
        """Active loans from another student must not appear."""
        student_a = await _make_user(db_session, email="dave@test.com")
        student_b = await _make_user(db_session, email="eve@test.com")
        book = await _make_book(db_session, title="Shared Book")
        br = await _make_borrow_request(db_session, student=student_b, book=book)

        await _make_loan(
            db_session,
            student=student_b,
            book=book,
            borrow_request=br,
            loan_date=NOW - 2 * DAY,
            due_date=NOW + 12 * DAY,
        )
        await db_session.commit()

        result = await list_student_loans(db_session, student_id=student_a.id, status="active")
        assert result.items == []


# ---------------------------------------------------------------------------
# list_student_loans — history view
# ---------------------------------------------------------------------------


class TestListStudentLoansHistory:
    @pytest.mark.asyncio
    async def test_history_sorts_newest_loan_first(self, db_session):
        """History view must sort by loan_date DESC (newest first)."""
        student = await _make_user(db_session, email="frank@test.com")
        book1 = await _make_book(db_session, title="Old Book")
        book2 = await _make_book(db_session, title="New Book")
        br1 = await _make_borrow_request(db_session, student=student, book=book1)
        br2 = await _make_borrow_request(db_session, student=student, book=book2)

        await _make_loan(
            db_session,
            student=student,
            book=book1,
            borrow_request=br1,
            status="returned",
            loan_date=NOW - 30 * DAY,
            due_date=NOW - 16 * DAY,
            returned_at=NOW - 15 * DAY,
        )
        await _make_loan(
            db_session,
            student=student,
            book=book2,
            borrow_request=br2,
            status="returned",
            loan_date=NOW - 5 * DAY,
            due_date=NOW + 9 * DAY,
            returned_at=NOW - 1 * DAY,
        )
        await db_session.commit()

        result = await list_student_loans(db_session, student_id=student.id, status="history")
        assert len(result.items) == 2
        # Newest loan first — book2 (loan 5 days ago) before book1 (loan 30 days ago)
        assert result.items[0].book_title == "New Book"
        assert result.items[1].book_title == "Old Book"

    @pytest.mark.asyncio
    async def test_history_excludes_active_loans(self, db_session):
        """Active loans must not appear in the history view."""
        student = await _make_user(db_session, email="grace@test.com")
        book = await _make_book(db_session, title="Active Only")
        br = await _make_borrow_request(db_session, student=student, book=book)

        await _make_loan(
            db_session,
            student=student,
            book=book,
            borrow_request=br,
            status="active",
            loan_date=NOW - 2 * DAY,
            due_date=NOW + 12 * DAY,
        )
        await db_session.commit()

        result = await list_student_loans(db_session, student_id=student.id, status="history")
        assert result.items == []


# ---------------------------------------------------------------------------
# Pagination metadata
# ---------------------------------------------------------------------------


class TestPaginationMetadata:
    @pytest.mark.asyncio
    async def test_pagination_metadata_stable_with_page_size_10(self, db_session):
        """total_pages is computed correctly and page_size is locked at DEFAULT_PAGE_SIZE."""
        student = await _make_user(db_session, email="hank@test.com")
        # Create 12 returned loans so pagination spans 2 pages at page_size=10
        for i in range(12):
            book = await _make_book(db_session, title=f"History Book {i:02d}")
            br = await _make_borrow_request(db_session, student=student, book=book)
            await _make_loan(
                db_session,
                student=student,
                book=book,
                borrow_request=br,
                status="returned",
                loan_date=NOW - (30 - i) * DAY,
                due_date=NOW - (16 - i) * DAY,
                returned_at=NOW - (15 - i) * DAY,
            )
        await db_session.commit()

        result_p1 = await list_student_loans(
            db_session, student_id=student.id, status="history", page=1
        )
        assert result_p1.total_items == 12
        assert result_p1.total_pages == 2
        assert result_p1.page_size == DEFAULT_PAGE_SIZE
        assert len(result_p1.items) == 10

        result_p2 = await list_student_loans(
            db_session, student_id=student.id, status="history", page=2
        )
        assert len(result_p2.items) == 2
        assert result_p2.page == 2


# ---------------------------------------------------------------------------
# search_loans
# ---------------------------------------------------------------------------


class TestSearchLoans:
    @pytest.mark.asyncio
    async def test_search_matches_student_full_name(self, db_session):
        """search_loans must match on student full_name (case-insensitive)."""
        student = await _make_user(db_session, email="ingrid.nilsson@test.com")
        book = await _make_book(db_session, title="Some Book")
        br = await _make_borrow_request(db_session, student=student, book=book)
        await _make_loan(
            db_session,
            student=student,
            book=book,
            borrow_request=br,
            loan_date=NOW - 2 * DAY,
            due_date=NOW + 12 * DAY,
        )
        await db_session.commit()

        result = await search_loans(db_session, q="Ingrid")
        assert result.total_items == 1
        assert "Ingrid" in result.items[0].student_name

    @pytest.mark.asyncio
    async def test_search_matches_book_title(self, db_session):
        """search_loans must match on book title (case-insensitive)."""
        student = await _make_user(db_session, email="jan@test.com")
        book = await _make_book(db_session, title="Python Patterns")
        br = await _make_borrow_request(db_session, student=student, book=book)
        await _make_loan(
            db_session,
            student=student,
            book=book,
            borrow_request=br,
            loan_date=NOW - 1 * DAY,
            due_date=NOW + 13 * DAY,
        )
        await db_session.commit()

        result = await search_loans(db_session, q="python")
        assert result.total_items == 1
        assert result.items[0].book_title == "Python Patterns"

    @pytest.mark.asyncio
    async def test_search_returns_newest_first(self, db_session):
        """Search results default to most recent loan first."""
        student = await _make_user(db_session, email="kim@test.com")
        book1 = await _make_book(db_session, title="Kim Old Book")
        book2 = await _make_book(db_session, title="Kim New Book")
        br1 = await _make_borrow_request(db_session, student=student, book=book1)
        br2 = await _make_borrow_request(db_session, student=student, book=book2)

        await _make_loan(
            db_session,
            student=student,
            book=book1,
            borrow_request=br1,
            loan_date=NOW - 20 * DAY,
            due_date=NOW - 6 * DAY,
        )
        await _make_loan(
            db_session,
            student=student,
            book=book2,
            borrow_request=br2,
            loan_date=NOW - 1 * DAY,
            due_date=NOW + 13 * DAY,
        )
        await db_session.commit()

        result = await search_loans(db_session, q="Kim")
        assert len(result.items) == 2
        # Newest first — book2 (1 day ago) before book1 (20 days ago)
        assert result.items[0].book_title == "Kim New Book"
        assert result.items[1].book_title == "Kim Old Book"

    @pytest.mark.asyncio
    async def test_search_no_match_returns_empty(self, db_session):
        """A query that matches nothing returns an empty items list."""
        result = await search_loans(db_session, q="NoMatchXYZ")
        assert result.items == []
        assert result.total_items == 0

    @pytest.mark.asyncio
    async def test_search_pagination_metadata(self, db_session):
        """search_loans paginates correctly across multiple pages."""
        student = await _make_user(db_session, email="lena@test.com")
        for i in range(15):
            book = await _make_book(db_session, title=f"Lena Book {i:02d}")
            br = await _make_borrow_request(db_session, student=student, book=book)
            await _make_loan(
                db_session,
                student=student,
                book=book,
                borrow_request=br,
                loan_date=NOW - (20 - i) * DAY,
                due_date=NOW + i * DAY,
            )
        await db_session.commit()

        result = await search_loans(db_session, q="Lena", page=1)
        assert result.total_items == 15
        assert result.total_pages == 2
        assert len(result.items) == DEFAULT_PAGE_SIZE
