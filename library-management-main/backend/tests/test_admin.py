# backend/tests/test_admin.py
# Integration tests for AUTH-06 (admin creates librarian) and AUTH-07 (RBAC enforcement).
# TDD RED: written before implementation to define behavior contracts.

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class TestCreateLibrarian:
    """AUTH-06: Admin librarian can POST /admin/users to create a librarian account."""

    async def test_admin_creates_librarian(self, client: AsyncClient, db_session: AsyncSession):
        """admin_librarian POST /admin/users creates a librarian with role='librarian'."""
        from app.services.auth_service import password_hash as ph
        # Seed an admin user in the test DB
        admin = User(
            email="admin@example.com",
            hashed_password=ph.hash("adminpass123"),
            full_name="Admin User",
            role="admin_librarian",
        )
        db_session.add(admin)
        await db_session.commit()

        login_resp = await client.post("/auth/login", json={
            "email": "admin@example.com",
            "password": "adminpass123",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/admin/users",
            json={
                "email": "newlibrarian@example.com",
                "password": "libpass123",
                "full_name": "New Librarian",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["email"] == "newlibrarian@example.com"
        assert data["role"] == "librarian"
        assert data["full_name"] == "New Librarian"

    async def test_admin_create_duplicate_librarian_returns_409(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Creating a librarian with an existing email returns 409."""
        from app.services.auth_service import password_hash as ph
        admin = User(
            email="admin2@example.com",
            hashed_password=ph.hash("adminpass123"),
            full_name="Admin User 2",
            role="admin_librarian",
        )
        db_session.add(admin)
        await db_session.commit()

        login_resp = await client.post("/auth/login", json={
            "email": "admin2@example.com",
            "password": "adminpass123",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        payload = {
            "email": "duplib@example.com",
            "password": "libpass123",
            "full_name": "Dup Librarian",
        }
        await client.post(
            "/admin/users",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.post(
            "/admin/users",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 409


class TestRBAC:
    """AUTH-07: Backend enforces role-based access — student gets 403 on admin endpoints."""

    async def test_student_forbidden_from_admin_endpoint(self, client: AsyncClient):
        """A student token hitting POST /admin/users returns 403."""
        # Register a student
        await client.post("/auth/register", json={
            "email": "student403@example.com",
            "password": "studentpass123",
            "full_name": "Student User",
        })
        login_resp = await client.post("/auth/login", json={
            "email": "student403@example.com",
            "password": "studentpass123",
        })
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/admin/users",
            json={
                "email": "shouldfail@example.com",
                "password": "libpass123",
                "full_name": "Should Fail",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_request_returns_401(self, client: AsyncClient):
        """Unauthenticated request to admin endpoint returns 401."""
        resp = await client.post(
            "/admin/users",
            json={
                "email": "noauth@example.com",
                "password": "libpass123",
                "full_name": "No Auth",
            },
        )
        assert resp.status_code == 401
