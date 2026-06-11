# backend/tests/test_books.py
# Integration tests for Book catalog endpoints (CAT-01, CAT-02) and
# Admin book CRUD (ADM-01, ADM-02, ADM-03).
# Tests run against real PostgreSQL DB via Docker Compose.

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.book import Book


# ---------------------------------------------------------------------------
# Helper: seed a librarian and get auth token
# ---------------------------------------------------------------------------

async def seed_librarian_and_get_token(
    client: AsyncClient, db_session: AsyncSession
) -> str:
    """Seed an admin_librarian, login, return access token."""
    from app.services.auth_service import password_hash as ph
    admin = User(
        email="adminbooks@example.com",
        hashed_password=ph.hash("adminpass123"),
        full_name="Admin Books",
        role="admin_librarian",
    )
    db_session.add(admin)
    await db_session.commit()

    resp = await client.post("/auth/login", json={
        "email": "adminbooks@example.com",
        "password": "adminpass123",
    })
    return resp.json()["access_token"]


async def seed_student_and_get_token(
    client: AsyncClient, db_session: AsyncSession, suffix: str = ""
) -> str:
    """Register a student and return access token."""
    resp = await client.post("/auth/register", json={
        "email": f"student{suffix}@books.com",
        "password": "password123",
        "full_name": f"Student {suffix}",
    })
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Admin Book CRUD (ADM-01, ADM-02, ADM-03)
# ---------------------------------------------------------------------------

class TestAdminBookCRUD:
    """ADM-01 through ADM-03: Admin creates, updates, and deletes books."""

    async def test_admin_creates_book(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """ADM-01: POST /admin/books creates a book with available_copies = total_copies."""
        token = await seed_librarian_and_get_token(client, db_session)

        resp = await client.post(
            "/admin/books",
            json={
                "isbn": "978-0-13-110362-7",
                "title": "The C Programming Language",
                "author": "Brian Kernighan",
                "total_copies": 3,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["isbn"] == "978-0-13-110362-7"
        assert data["title"] == "The C Programming Language"
        assert data["total_copies"] == 3
        assert data["available_copies"] == 3  # All copies available on creation
        assert "id" in data

    async def test_admin_create_duplicate_isbn_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """ADM-01: Creating a book with duplicate ISBN returns 409."""
        token = await seed_librarian_and_get_token(client, db_session)

        payload = {
            "isbn": "978-DUP-001",
            "title": "Duplicate Book",
            "author": "Author One",
            "total_copies": 2,
        }
        await client.post(
            "/admin/books",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.post(
            "/admin/books",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409

    async def test_admin_updates_book(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """ADM-02: PUT /admin/books/{id} updates book fields."""
        token = await seed_librarian_and_get_token(client, db_session)

        # Create a book first
        create_resp = await client.post(
            "/admin/books",
            json={"isbn": "978-UPDATE-001", "title": "Old Title", "author": "Old Author", "total_copies": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        book_id = create_resp.json()["id"]

        # Update it
        resp = await client.put(
            f"/admin/books/{book_id}",
            json={"title": "New Title", "author": "New Author"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "New Title"
        assert data["author"] == "New Author"
        assert data["isbn"] == "978-UPDATE-001"  # unchanged

    async def test_admin_update_nonexistent_book_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """ADM-02: Updating a nonexistent book returns 404."""
        token = await seed_librarian_and_get_token(client, db_session)

        resp = await client.put(
            "/admin/books/99999",
            json={"title": "Ghost"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_admin_deletes_book(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """ADM-03: DELETE /admin/books/{id} removes the book."""
        token = await seed_librarian_and_get_token(client, db_session)

        create_resp = await client.post(
            "/admin/books",
            json={"isbn": "978-DEL-001", "title": "To Delete", "author": "Author", "total_copies": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        book_id = create_resp.json()["id"]

        resp = await client.delete(
            f"/admin/books/{book_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get(
            f"/books/{book_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert get_resp.status_code == 404

    async def test_admin_delete_nonexistent_book_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """ADM-03: Deleting a nonexistent book returns 404."""
        token = await seed_librarian_and_get_token(client, db_session)

        resp = await client.delete(
            "/admin/books/99999",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_student_cannot_create_book(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """A student token cannot POST /admin/books (403)."""
        student_token = await seed_student_and_get_token(client, db_session, "booktest")

        resp = await client.post(
            "/admin/books",
            json={"isbn": "978-FORBIDDEN", "title": "Forbidden", "author": "X", "total_copies": 1},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

    async def test_create_book_invalid_total_copies(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """ADM-01: total_copies < 1 returns 422 validation error."""
        token = await seed_librarian_and_get_token(client, db_session)

        resp = await client.post(
            "/admin/books",
            json={"isbn": "978-BAD-001", "title": "Bad", "author": "Bad", "total_copies": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Book catalog search (CAT-01, CAT-02)
# ---------------------------------------------------------------------------

class TestBookSearch:
    """CAT-01: GET /books search by title/author/ISBN with pagination."""

    async def _setup_books(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> str:
        """Seed books and return a student auth token."""
        # Seed admin
        from app.services.auth_service import password_hash as ph
        admin = User(
            email="admin_search@example.com",
            hashed_password=ph.hash("adminpass123"),
            full_name="Admin Search",
            role="admin_librarian",
        )
        db_session.add(admin)
        await db_session.commit()

        login_resp = await client.post("/auth/login", json={
            "email": "admin_search@example.com",
            "password": "adminpass123",
        })
        admin_token = login_resp.json()["access_token"]

        # Seed books
        books_data = [
            {"isbn": "978-001", "title": "Python Crash Course", "author": "Eric Matthes", "total_copies": 5},
            {"isbn": "978-002", "title": "Clean Code", "author": "Robert Martin", "total_copies": 3},
            {"isbn": "978-003", "title": "The Pragmatic Programmer", "author": "David Thomas", "total_copies": 2},
        ]
        for book in books_data:
            await client.post("/admin/books", json=book, headers={"Authorization": f"Bearer {admin_token}"})

        # Register student and return token
        student_resp = await client.post("/auth/register", json={
            "email": "student_search@example.com",
            "password": "password123",
            "full_name": "Search Student",
        })
        return student_resp.json()["access_token"]

    async def test_list_all_books(self, client: AsyncClient, db_session: AsyncSession):
        """GET /books returns all books when no query given."""
        token = await self._setup_books(client, db_session)
        resp = await client.get("/books", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 3
        assert len(data["items"]) >= 3

    async def test_search_by_title(self, client: AsyncClient, db_session: AsyncSession):
        """CAT-01: ?q=Python matches title."""
        token = await self._setup_books(client, db_session)
        resp = await client.get("/books?q=Python", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any("Python" in item["title"] for item in data["items"])

    async def test_search_by_author(self, client: AsyncClient, db_session: AsyncSession):
        """CAT-01: ?q=Martin matches author."""
        token = await self._setup_books(client, db_session)
        resp = await client.get("/books?q=Martin", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any("Martin" in item["author"] for item in data["items"])

    async def test_search_by_isbn(self, client: AsyncClient, db_session: AsyncSession):
        """CAT-01: ?q=978-001 matches ISBN."""
        token = await self._setup_books(client, db_session)
        resp = await client.get("/books?q=978-001", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_search_pagination(self, client: AsyncClient, db_session: AsyncSession):
        """CAT-01: page_size limits results; page changes offset."""
        token = await self._setup_books(client, db_session)
        resp = await client.get(
            "/books?page=1&page_size=2",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 2
        assert data["page"] == 1
        assert data["page_size"] == 2

    async def test_search_no_results(self, client: AsyncClient, db_session: AsyncSession):
        """CAT-01: ?q=ZZZNOMATCH returns empty items list."""
        token = await self._setup_books(client, db_session)
        resp = await client.get(
            "/books?q=ZZZNOMATCH",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    async def test_get_book_detail(self, client: AsyncClient, db_session: AsyncSession):
        """CAT-02: GET /books/{id} returns a single book."""
        from app.services.auth_service import password_hash as ph
        admin = User(
            email="admin_det@example.com",
            hashed_password=ph.hash("adminpass123"),
            full_name="Admin Det",
            role="admin_librarian",
        )
        db_session.add(admin)
        await db_session.commit()
        login_resp = await client.post("/auth/login", json={"email": "admin_det@example.com", "password": "adminpass123"})
        admin_token = login_resp.json()["access_token"]

        create_resp = await client.post(
            "/admin/books",
            json={"isbn": "978-DETAIL", "title": "Detail Book", "author": "Detail Author", "total_copies": 1},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        book_id = create_resp.json()["id"]

        resp = await client.get(f"/books/{book_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == book_id
        assert data["title"] == "Detail Book"

    async def test_get_book_not_found(self, client: AsyncClient, db_session: AsyncSession):
        """CAT-02: GET /books/{id} returns 404 for missing book."""
        token = await seed_student_and_get_token(client, db_session, "notfound")
        resp = await client.get("/books/99999", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404

    async def test_unauthenticated_request_returns_401(self, client: AsyncClient, db_session: AsyncSession):
        """Unauthenticated GET /books returns 401."""
        resp = await client.get("/books")
        assert resp.status_code == 401
