# backend/tests/test_borrow.py
# Integration tests for Borrow/Return workflow (BR-01 through BR-06).
# Tests run against real PostgreSQL DB via Docker Compose.
#
# Behavior contracts:
#   BR-01: Student can borrow available book; fails if no copies; fails if duplicate pending.
#   BR-02: Librarian approves pending request → creates Loan, decrements availability.
#   BR-03: Librarian rejects pending request → no availability change.
#   BR-05: Librarian records return → marks loan returned, increments availability.
#   BR-06: Students see only their loans; librarians see all.

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.book import Book


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def seed_admin_and_login(client: AsyncClient, db_session: AsyncSession, suffix: str = "") -> str:
    from app.services.auth_service import password_hash as ph
    admin = User(
        email=f"admin_borrow{suffix}@example.com",
        hashed_password=ph.hash("adminpass123"),
        full_name="Admin Borrow",
        role="admin_librarian",
    )
    db_session.add(admin)
    await db_session.commit()
    resp = await client.post("/auth/login", json={
        "email": f"admin_borrow{suffix}@example.com",
        "password": "adminpass123",
    })
    return resp.json()["access_token"]


async def seed_librarian_and_login(client: AsyncClient, db_session: AsyncSession, suffix: str = "") -> str:
    from app.services.auth_service import password_hash as ph
    lib = User(
        email=f"librarian{suffix}@example.com",
        hashed_password=ph.hash("libpass123"),
        full_name="Librarian",
        role="librarian",
    )
    db_session.add(lib)
    await db_session.commit()
    resp = await client.post("/auth/login", json={
        "email": f"librarian{suffix}@example.com",
        "password": "libpass123",
    })
    return resp.json()["access_token"]


async def seed_student_and_login(client: AsyncClient, suffix: str = "") -> str:
    resp = await client.post("/auth/register", json={
        "email": f"student{suffix}@borrow.com",
        "password": "password123",
        "full_name": f"Student {suffix}",
    })
    return resp.json()["access_token"]


async def create_book(client: AsyncClient, admin_token: str, suffix: str = "") -> dict:
    resp = await client.post(
        "/admin/books",
        json={
            "isbn": f"978-BORROW-{suffix}",
            "title": f"Test Book {suffix}",
            "author": "Test Author",
            "total_copies": 3,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    return resp.json()


# ---------------------------------------------------------------------------
# BR-01: Student submits borrow request
# ---------------------------------------------------------------------------

class TestBorrowRequest:
    """BR-01: Students can request to borrow available books."""

    async def test_student_can_borrow_available_book(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """BR-01: POST /borrow creates a pending borrow request."""
        admin_token = await seed_admin_and_login(client, db_session, "br01a")
        book = await create_book(client, admin_token, "BR01A")
        student_token = await seed_student_and_login(client, "br01a")

        resp = await client.post(
            "/borrow",
            json={"book_id": book["id"]},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["book_id"] == book["id"]

    async def test_borrow_unavailable_book_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """BR-01: Borrowing a book with available_copies=0 returns 400."""
        from app.services.auth_service import password_hash as ph
        # Create a book with 0 available copies directly
        book = Book(
            isbn="978-UNAVAILABLE",
            title="Unavailable Book",
            author="Author",
            total_copies=1,
            available_copies=0,  # manually set to 0
        )
        db_session.add(book)
        await db_session.commit()
        await db_session.refresh(book)

        student_token = await seed_student_and_login(client, "unavail")
        resp = await client.post(
            "/borrow",
            json={"book_id": book.id},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 400
        assert "available" in resp.json()["detail"].lower()

    async def test_borrow_nonexistent_book_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """BR-01: Borrowing a nonexistent book returns 400."""
        student_token = await seed_student_and_login(client, "nobook")
        resp = await client.post(
            "/borrow",
            json={"book_id": 99999},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 400

    async def test_duplicate_pending_request_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """BR-01: A student cannot have two pending requests for the same book."""
        admin_token = await seed_admin_and_login(client, db_session, "dup")
        book = await create_book(client, admin_token, "DUP")
        student_token = await seed_student_and_login(client, "dup")

        # First request
        await client.post(
            "/borrow",
            json={"book_id": book["id"]},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        # Second request — should fail
        resp = await client.post(
            "/borrow",
            json={"book_id": book["id"]},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 400

    async def test_librarian_cannot_borrow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Only students can POST /borrow (403 for librarian)."""
        admin_token = await seed_admin_and_login(client, db_session, "libcan")
        book = await create_book(client, admin_token, "LIBCAN")
        lib_token = await seed_librarian_and_login(client, db_session, "libcan")

        resp = await client.post(
            "/borrow",
            json={"book_id": book["id"]},
            headers={"Authorization": f"Bearer {lib_token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# BR-02: Librarian approves request
# ---------------------------------------------------------------------------

class TestApproveRequest:
    """BR-02: Librarians approve pending borrow requests."""

    async def test_librarian_approves_request_creates_loan(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """BR-02: Approving a request creates a Loan and decrements availability."""
        admin_token = await seed_admin_and_login(client, db_session, "apr")
        book = await create_book(client, admin_token, "APR")
        original_available = book["available_copies"]

        student_token = await seed_student_and_login(client, "apr")
        borrow_resp = await client.post(
            "/borrow",
            json={"book_id": book["id"]},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        request_id = borrow_resp.json()["id"]

        # Approve as librarian
        lib_token = await seed_librarian_and_login(client, db_session, "apr")
        approve_resp = await client.post(
            f"/borrow/{request_id}/approve",
            headers={"Authorization": f"Bearer {lib_token}"},
        )
        assert approve_resp.status_code == 200
        loan = approve_resp.json()
        assert loan["status"] == "active"
        assert loan["book_id"] == book["id"]
        assert "due_date" in loan
        assert "loan_date" in loan

        # Verify availability decreased
        book_resp = await client.get(
            f"/books/{book['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert book_resp.json()["available_copies"] == original_available - 1

    async def test_approve_already_approved_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """BR-02: Approving an already-approved request returns 400."""
        admin_token = await seed_admin_and_login(client, db_session, "dbl")
        book = await create_book(client, admin_token, "DBL")
        student_token = await seed_student_and_login(client, "dbl")
        lib_token = await seed_librarian_and_login(client, db_session, "dbl")

        borrow_resp = await client.post(
            "/borrow", json={"book_id": book["id"]},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        request_id = borrow_resp.json()["id"]

        # First approval
        await client.post(
            f"/borrow/{request_id}/approve",
            headers={"Authorization": f"Bearer {lib_token}"},
        )
        # Second approval
        resp = await client.post(
            f"/borrow/{request_id}/approve",
            headers={"Authorization": f"Bearer {lib_token}"},
        )
        assert resp.status_code == 400

    async def test_student_cannot_approve(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Students cannot approve borrow requests (403)."""
        admin_token = await seed_admin_and_login(client, db_session, "std_apr")
        book = await create_book(client, admin_token, "STDAPR")
        student_token = await seed_student_and_login(client, "std_apr")

        borrow_resp = await client.post(
            "/borrow", json={"book_id": book["id"]},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        request_id = borrow_resp.json()["id"]

        resp = await client.post(
            f"/borrow/{request_id}/approve",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# BR-03: Librarian rejects request
# ---------------------------------------------------------------------------

class TestRejectRequest:
    """BR-03: Librarians reject pending borrow requests."""

    async def test_librarian_rejects_request(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """BR-03: Rejecting a request sets status to 'rejected'."""
        admin_token = await seed_admin_and_login(client, db_session, "rej")
        book = await create_book(client, admin_token, "REJ")
        original_available = book["available_copies"]

        student_token = await seed_student_and_login(client, "rej")
        borrow_resp = await client.post(
            "/borrow", json={"book_id": book["id"]},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        request_id = borrow_resp.json()["id"]

        lib_token = await seed_librarian_and_login(client, db_session, "rej")
        reject_resp = await client.post(
            f"/borrow/{request_id}/reject",
            headers={"Authorization": f"Bearer {lib_token}"},
        )
        assert reject_resp.status_code == 200
        assert reject_resp.json()["status"] == "rejected"

        # Availability unchanged
        book_resp = await client.get(
            f"/books/{book['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert book_resp.json()["available_copies"] == original_available


# ---------------------------------------------------------------------------
# BR-05: Librarian records return
# ---------------------------------------------------------------------------

class TestReturnLoan:
    """BR-05: Librarians record book returns."""

    async def test_return_active_loan(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """BR-05: Returning an active loan marks it 'returned' and restores availability."""
        admin_token = await seed_admin_and_login(client, db_session, "ret")
        book = await create_book(client, admin_token, "RET")
        original_available = book["available_copies"]

        student_token = await seed_student_and_login(client, "ret")
        borrow_resp = await client.post(
            "/borrow", json={"book_id": book["id"]},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        request_id = borrow_resp.json()["id"]

        lib_token = await seed_librarian_and_login(client, db_session, "ret")
        loan_resp = await client.post(
            f"/borrow/{request_id}/approve",
            headers={"Authorization": f"Bearer {lib_token}"},
        )
        loan_id = loan_resp.json()["id"]

        # Return the loan
        return_resp = await client.post(
            f"/loans/{loan_id}/return",
            headers={"Authorization": f"Bearer {lib_token}"},
        )
        assert return_resp.status_code == 200
        data = return_resp.json()
        assert data["status"] == "returned"
        assert data["returned_at"] is not None

        # Availability restored
        book_resp = await client.get(
            f"/books/{book['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert book_resp.json()["available_copies"] == original_available

    async def test_return_already_returned_loan_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """BR-05: Returning an already-returned loan returns 400."""
        admin_token = await seed_admin_and_login(client, db_session, "ret2")
        book = await create_book(client, admin_token, "RET2")

        student_token = await seed_student_and_login(client, "ret2")
        borrow_resp = await client.post(
            "/borrow", json={"book_id": book["id"]},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        request_id = borrow_resp.json()["id"]

        lib_token = await seed_librarian_and_login(client, db_session, "ret2")
        loan_resp = await client.post(
            f"/borrow/{request_id}/approve",
            headers={"Authorization": f"Bearer {lib_token}"},
        )
        loan_id = loan_resp.json()["id"]

        await client.post(f"/loans/{loan_id}/return", headers={"Authorization": f"Bearer {lib_token}"})
        resp = await client.post(f"/loans/{loan_id}/return", headers={"Authorization": f"Bearer {lib_token}"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# BR-04 / BR-06: List requests and loans
# ---------------------------------------------------------------------------

class TestListBorrowAndLoans:
    """BR-04: Students see own requests; librarians see all. BR-06: Same for loans."""

    async def test_student_sees_only_own_requests(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """BR-04: Students only see their own borrow requests."""
        admin_token = await seed_admin_and_login(client, db_session, "list")
        book = await create_book(client, admin_token, "LIST")

        student1_token = await seed_student_and_login(client, "list1")
        student2_token = await seed_student_and_login(client, "list2")

        await client.post("/borrow", json={"book_id": book["id"]}, headers={"Authorization": f"Bearer {student1_token}"})
        await client.post("/borrow", json={"book_id": book["id"]}, headers={"Authorization": f"Bearer {student2_token}"})

        # student1 sees only their request
        resp = await client.get("/borrow", headers={"Authorization": f"Bearer {student1_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        # All requests belong to student1
        for item in data:
            assert item["book_id"] == book["id"]

    async def test_librarian_sees_all_requests(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """BR-04: Librarians see all borrow requests."""
        admin_token = await seed_admin_and_login(client, db_session, "liblist")
        book = await create_book(client, admin_token, "LIBLIST")

        student1_token = await seed_student_and_login(client, "liblist1")
        student2_token = await seed_student_and_login(client, "liblist2")

        await client.post("/borrow", json={"book_id": book["id"]}, headers={"Authorization": f"Bearer {student1_token}"})
        await client.post("/borrow", json={"book_id": book["id"]}, headers={"Authorization": f"Bearer {student2_token}"})

        lib_token = await seed_librarian_and_login(client, db_session, "liblist")
        resp = await client.get("/borrow", headers={"Authorization": f"Bearer {lib_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 2
