# backend/tests/test_loans.py
# API integration tests for Phase 4 loan read endpoints.
# Covers LOAN-02 (active loans), LOAN-03 (history), LOAN-04 (search), LOAN-05 (pagination).
# T-04-01: student owns only their loans; librarian search requires role.

import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.borrow_request import BorrowRequest
from app.models.loan import Loan
from app.models.user import User
from app.services.auth_service import password_hash as ph

NOW = datetime.datetime(2026, 6, 11, 12, 0, 0, tzinfo=datetime.timezone.utc)
DAY = datetime.timedelta(days=1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client: AsyncClient, email: str, password: str) -> str:
    """Register a student, log in, and return the access token."""
    await client.post(
        "/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0].title()},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _login_seeded(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _seed_loan(
    db: AsyncSession,
    *,
    student: User,
    title: str,
    status: str = "active",
    loan_date: datetime.datetime,
    due_date: datetime.datetime,
    returned_at: datetime.datetime | None = None,
) -> Loan:
    book = Book(
        title=title,
        author="Test Author",
        isbn=f"ISBN-{title[:8].replace(' ', '-')}",
        total_copies=5,
        available_copies=5,
    )
    db.add(book)
    await db.flush()

    br = BorrowRequest(student_id=student.id, book_id=book.id, status="approved")
    db.add(br)
    await db.flush()

    loan = Loan(
        student_id=student.id,
        book_id=book.id,
        borrow_request_id=br.id,
        status=status,
        loan_date=loan_date,
        due_date=due_date,
        returned_at=returned_at,
    )
    db.add(loan)
    await db.flush()
    return loan


# ---------------------------------------------------------------------------
# GET /loans/me — student active and history views
# ---------------------------------------------------------------------------


class TestGetMyLoans:
    """LOAN-02, LOAN-03: Student can view their active loans and full borrow history."""

    @pytest.mark.asyncio
    async def test_active_loans_returns_student_active_only(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """GET /loans/me?status=active returns only active loans for the authenticated user."""
        student = User(
            email="loans.active@test.com",
            hashed_password=ph.hash("pass1234"),
            full_name="Active Student",
            role="student",
        )
        db_session.add(student)
        await db_session.flush()

        await _seed_loan(
            db_session,
            student=student,
            title="Active Book",
            loan_date=NOW - 2 * DAY,
            due_date=NOW + 12 * DAY,
        )
        await _seed_loan(
            db_session,
            student=student,
            title="Returned Book",
            status="returned",
            loan_date=NOW - 20 * DAY,
            due_date=NOW - 6 * DAY,
            returned_at=NOW - 5 * DAY,
        )
        await db_session.commit()

        token = await _login_seeded(client, "loans.active@test.com", "pass1234")
        resp = await client.get(
            "/loans/me?status=active",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] == 1
        assert data["items"][0]["book_title"] == "Active Book"

    @pytest.mark.asyncio
    async def test_history_returns_returned_loans(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """/loans/me?status=history returns only returned loans sorted newest-first."""
        student = User(
            email="loans.history@test.com",
            hashed_password=ph.hash("pass1234"),
            full_name="History Student",
            role="student",
        )
        db_session.add(student)
        await db_session.flush()

        await _seed_loan(
            db_session,
            student=student,
            title="Old History Book",
            status="returned",
            loan_date=NOW - 30 * DAY,
            due_date=NOW - 16 * DAY,
            returned_at=NOW - 15 * DAY,
        )
        await _seed_loan(
            db_session,
            student=student,
            title="New History Book",
            status="returned",
            loan_date=NOW - 5 * DAY,
            due_date=NOW + 9 * DAY,
            returned_at=NOW - 1 * DAY,
        )
        await db_session.commit()

        token = await _login_seeded(client, "loans.history@test.com", "pass1234")
        resp = await client.get(
            "/loans/me?status=history",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] == 2
        # Newest first
        assert data["items"][0]["book_title"] == "New History Book"
        assert data["items"][1]["book_title"] == "Old History Book"

    @pytest.mark.asyncio
    async def test_student_cannot_see_other_students_loans(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """T-04-01: /loans/me is scoped to the authenticated user only."""
        owner = User(
            email="owner@test.com",
            hashed_password=ph.hash("pass1234"),
            full_name="Owner Student",
            role="student",
        )
        spy = User(
            email="spy@test.com",
            hashed_password=ph.hash("pass1234"),
            full_name="Spy Student",
            role="student",
        )
        db_session.add(owner)
        db_session.add(spy)
        await db_session.flush()

        await _seed_loan(
            db_session,
            student=owner,
            title="Owner Secret Book",
            loan_date=NOW - 1 * DAY,
            due_date=NOW + 13 * DAY,
        )
        await db_session.commit()

        # Spy logs in and calls /loans/me — must not see owner's loans
        token = await _login_seeded(client, "spy@test.com", "pass1234")
        resp = await client.get(
            "/loans/me?status=active",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total_items"] == 0

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        """/loans/me without a token returns 401."""
        resp = await client.get("/loans/me")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_paginated_response_shape(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Response includes required pagination envelope fields."""
        student = User(
            email="loans.paged@test.com",
            hashed_password=ph.hash("pass1234"),
            full_name="Paged Student",
            role="student",
        )
        db_session.add(student)
        await db_session.flush()
        await db_session.commit()

        token = await _login_seeded(client, "loans.paged@test.com", "pass1234")
        resp = await client.get(
            "/loans/me?status=active",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for key in ("page", "page_size", "total_items", "total_pages", "items"):
            assert key in data, f"Missing key '{key}' in response"


# ---------------------------------------------------------------------------
# GET /loans/search — librarian loan search
# ---------------------------------------------------------------------------


class TestLoanSearch:
    """LOAN-04, LOAN-05: Librarian can search all loans by student name or book title."""

    async def _seed_librarian(self, db: AsyncSession, email: str) -> User:
        lib = User(
            email=email,
            hashed_password=ph.hash("libpass123"),
            full_name="Test Librarian",
            role="librarian",
        )
        db.add(lib)
        await db.flush()
        return lib

    @pytest.mark.asyncio
    async def test_student_cannot_access_search(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """T-04-01 RBAC: /loans/search returns 403 for student role."""
        student = User(
            email="searchspy@test.com",
            hashed_password=ph.hash("pass1234"),
            full_name="Search Spy",
            role="student",
        )
        db_session.add(student)
        await db_session.commit()

        token = await _login_seeded(client, "searchspy@test.com", "pass1234")
        resp = await client.get(
            "/loans/search?q=anything",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_search_returns_401(self, client: AsyncClient):
        """/loans/search without a token returns 401."""
        resp = await client.get("/loans/search?q=test")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_librarian_search_by_book_title(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Librarian can find loans by book title substring."""
        lib = await self._seed_librarian(db_session, "lib.searcher@test.com")
        student = User(
            email="s.searchable@test.com",
            hashed_password=ph.hash("pass1234"),
            full_name="Search Target Student",
            role="student",
        )
        db_session.add(student)
        await db_session.flush()

        await _seed_loan(
            db_session,
            student=student,
            title="Unique Searchable Title",
            loan_date=NOW - 1 * DAY,
            due_date=NOW + 13 * DAY,
        )
        await db_session.commit()

        token = await _login_seeded(client, "lib.searcher@test.com", "libpass123")
        resp = await client.get(
            "/loans/search?q=Searchable",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] == 1
        assert data["items"][0]["book_title"] == "Unique Searchable Title"

    @pytest.mark.asyncio
    async def test_librarian_search_by_student_name(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Librarian can find loans by student name substring."""
        lib = await self._seed_librarian(db_session, "lib.namesearch@test.com")
        student = User(
            email="nikolai.special@test.com",
            hashed_password=ph.hash("pass1234"),
            full_name="Nikolai Specialov",
            role="student",
        )
        db_session.add(student)
        await db_session.flush()

        await _seed_loan(
            db_session,
            student=student,
            title="Some Random Book",
            loan_date=NOW - 2 * DAY,
            due_date=NOW + 12 * DAY,
        )
        await db_session.commit()

        token = await _login_seeded(client, "lib.namesearch@test.com", "libpass123")
        resp = await client.get(
            "/loans/search?q=Nikolai",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_items"] == 1
        assert "Nikolai" in data["items"][0]["student_name"]

    @pytest.mark.asyncio
    async def test_search_pagination_response_shape(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Search response includes all required pagination envelope keys."""
        lib = await self._seed_librarian(db_session, "lib.pageshape@test.com")
        await db_session.commit()

        token = await _login_seeded(client, "lib.pageshape@test.com", "libpass123")
        resp = await client.get(
            "/loans/search?q=nothing&page=1&page_size=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        for key in ("page", "page_size", "total_items", "total_pages", "items"):
            assert key in data

    @pytest.mark.asyncio
    async def test_admin_librarian_can_also_search(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """admin_librarian role must also be allowed to call /loans/search."""
        admin = User(
            email="adminlib.search@test.com",
            hashed_password=ph.hash("adminpass123"),
            full_name="Admin Librarian",
            role="admin_librarian",
        )
        db_session.add(admin)
        await db_session.commit()

        token = await _login_seeded(client, "adminlib.search@test.com", "adminpass123")
        resp = await client.get(
            "/loans/search?q=anything",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
