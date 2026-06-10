# backend/tests/test_auth.py
# Integration tests for AUTH-01 through AUTH-04, AUTH-05.
# Tests run against the real PostgreSQL DB via Docker Compose.
# TDD RED: written before implementation to define behavior contracts.

import pytest
import jwt
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.auth import RegisterRequest


# =============================================================================
# Task 1 tests: auth_service contracts (token, authenticate, require_role)
# =============================================================================

class TestCreateAccessToken:
    """
    Behavior: create_access_token then jwt.decode yields sub and role claims.
    """

    async def test_access_token_contains_sub_and_role(self):
        """create_access_token encodes user_id as sub and role into the token."""
        from app.services.auth_service import create_access_token
        secret = "test-secret-key-at-least-32-chars!!"
        token = create_access_token(user_id=42, role="student", secret=secret)
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["sub"] == "42"
        assert payload["role"] == "student"
        assert payload["type"] == "access"

    async def test_access_token_uses_hs256(self):
        """Token must be decodable only with HS256 (not algorithm=None)."""
        from app.services.auth_service import create_access_token
        secret = "test-secret-key-at-least-32-chars!!"
        token = create_access_token(user_id=1, role="librarian", secret=secret)
        # Must decode with explicit HS256 — algorithm confusion defense
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["sub"] == "1"
        assert payload["role"] == "librarian"

    async def test_refresh_token_contains_sub(self):
        """create_refresh_token encodes user_id as sub."""
        from app.services.auth_service import create_refresh_token
        secret = "test-secret-key-at-least-32-chars!!"
        token = create_refresh_token(user_id=99, secret=secret)
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        assert payload["sub"] == "99"
        assert payload["type"] == "refresh"


class TestAuthenticateUser:
    """
    Behavior: authenticate_user returns None for unknown email, None for wrong
    password, and the User object for valid credentials.
    """

    async def test_authenticate_unknown_email_returns_none(self, db_session: AsyncSession):
        """authenticate_user returns None when email does not exist."""
        from app.services.auth_service import authenticate_user
        result = await authenticate_user(db_session, "nonexistent@example.com", "anypassword")
        assert result is None

    async def test_authenticate_wrong_password_returns_none(self, db_session: AsyncSession):
        """authenticate_user returns None when password is wrong."""
        from app.services.auth_service import authenticate_user, password_hash
        # Insert a user directly
        user = User(
            email="wrongpw@example.com",
            hashed_password=password_hash.hash("correctpassword"),
            full_name="Test User",
            role="student",
        )
        db_session.add(user)
        await db_session.commit()

        result = await authenticate_user(db_session, "wrongpw@example.com", "wrongpassword")
        assert result is None

    async def test_authenticate_valid_credentials_returns_user(self, db_session: AsyncSession):
        """authenticate_user returns the User for valid email and password."""
        from app.services.auth_service import authenticate_user, password_hash
        user = User(
            email="valid@example.com",
            hashed_password=password_hash.hash("validpassword"),
            full_name="Valid User",
            role="student",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        result = await authenticate_user(db_session, "valid@example.com", "validpassword")
        assert result is not None
        assert result.email == "valid@example.com"
        assert result.id == user.id


class TestRequireRole:
    """
    Behavior: require_role dependency raises 403 for wrong role, passes for correct role.
    """

    async def test_student_token_fails_admin_role_check(self, client: AsyncClient):
        """
        A student token hitting an admin_librarian-required endpoint returns 403.
        This test registers a student, logs in, then tries to create a librarian.
        """
        # Register a student
        resp = await client.post("/auth/register", json={
            "email": "student@example.com",
            "password": "studentpass123",
            "full_name": "Student User",
        })
        assert resp.status_code in (200, 201)

        # Login to get access token
        resp = await client.post("/auth/login", json={
            "email": "student@example.com",
            "password": "studentpass123",
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]

        # Try to create a librarian — should return 403
        resp = await client.post(
            "/admin/users",
            json={"email": "new@librarian.com", "password": "libpass123", "full_name": "New Lib"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_admin_token_passes_role_check(self, client: AsyncClient, db_session: AsyncSession):
        """
        An admin_librarian token hitting an admin-required endpoint succeeds.
        The seeded admin (from Alembic migration) provides the admin account.
        """
        import os
        from app.services.auth_service import password_hash as ph
        # Create admin directly in test DB (migration seed not present in test DB)
        admin = User(
            email="testadmin@example.com",
            hashed_password=ph.hash("adminpass123"),
            full_name="Test Admin",
            role="admin_librarian",
        )
        db_session.add(admin)
        await db_session.commit()

        resp = await client.post("/auth/login", json={
            "email": "testadmin@example.com",
            "password": "adminpass123",
        })
        assert resp.status_code == 200
        token = resp.json()["access_token"]

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


# =============================================================================
# Task 2 tests: Full auth API (AUTH-01 through AUTH-05)
# =============================================================================

class TestRegister:
    """AUTH-01: POST /auth/register creates a student user."""

    async def test_register_creates_student(self, client: AsyncClient):
        """POST /auth/register returns user data with role=student."""
        resp = await client.post("/auth/register", json={
            "email": "newstudent@example.com",
            "password": "password123",
            "full_name": "New Student",
        })
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["email"] == "newstudent@example.com"
        assert data["role"] == "student"
        assert data["full_name"] == "New Student"
        assert "id" in data

    async def test_register_duplicate_email_returns_409(self, client: AsyncClient):
        """Registering with an existing email returns 409."""
        payload = {
            "email": "dup@example.com",
            "password": "password123",
            "full_name": "First User",
        }
        await client.post("/auth/register", json=payload)
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 409


class TestLogin:
    """AUTH-02: POST /auth/login returns access_token and sets httpOnly refresh cookie."""

    async def test_login_valid_credentials(self, client: AsyncClient):
        """Valid credentials return access_token and refresh cookie."""
        await client.post("/auth/register", json={
            "email": "login@example.com",
            "password": "password123",
            "full_name": "Login User",
        })
        resp = await client.post("/auth/login", json={
            "email": "login@example.com",
            "password": "password123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        # Refresh token must be in httpOnly cookie
        assert "refresh_token" in resp.cookies

    async def test_login_invalid_credentials_returns_401(self, client: AsyncClient):
        """Invalid credentials return 401."""
        resp = await client.post("/auth/login", json={
            "email": "noone@example.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401


class TestRefresh:
    """AUTH-03: POST /auth/refresh with valid cookie returns new access_token."""

    async def test_refresh_with_valid_cookie(self, client: AsyncClient):
        """After login, /auth/refresh returns a new access_token."""
        await client.post("/auth/register", json={
            "email": "refresh@example.com",
            "password": "password123",
            "full_name": "Refresh User",
        })
        login_resp = await client.post("/auth/login", json={
            "email": "refresh@example.com",
            "password": "password123",
        })
        assert login_resp.status_code == 200
        # Cookie is automatically stored in the test client
        refresh_resp = await client.post("/auth/refresh")
        assert refresh_resp.status_code == 200
        assert "access_token" in refresh_resp.json()


class TestLogout:
    """AUTH-04: POST /auth/logout blocks the refresh token; subsequent refresh fails."""

    async def test_logout_blocks_refresh_token(self, client: AsyncClient):
        """After logout, the same refresh cookie must be rejected."""
        await client.post("/auth/register", json={
            "email": "logout@example.com",
            "password": "password123",
            "full_name": "Logout User",
        })
        await client.post("/auth/login", json={
            "email": "logout@example.com",
            "password": "password123",
        })
        # Logout
        logout_resp = await client.post("/auth/logout")
        assert logout_resp.status_code == 200
        # Try to refresh again — must be blocked
        refresh_resp = await client.post("/auth/refresh")
        assert refresh_resp.status_code in (401, 403)
