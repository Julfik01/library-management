# backend/tests/test_integration_smoke.py
# Quick smoke test using SQLite in-memory — runs without Docker/PostgreSQL.
# Used to verify basic auth flow + Phase 2 book/borrow flow before Docker-based tests.
# Not part of the primary test suite — supplementary only.
#
# To run: PYTHONPATH=. python3 tests/test_integration_smoke.py

import asyncio
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("SECRET_KEY", "test_secret_key_at_least_32_chars_long")
os.environ.setdefault("ADMIN_EMAIL", "admin@test.com")
os.environ.setdefault("ADMIN_PASSWORD", "testpass123")

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import app as fastapi_app
from app.database import get_db
import app.models  # noqa: F401 — populate Base.metadata
from app.models.user import Base, User

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


async def run_tests():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        async def override_get_db():
            yield session

        fastapi_app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as client:
            # AUTH-01: Register creates student
            resp = await client.post("/auth/register", json={
                "email": "student@test.com",
                "password": "password123",
                "full_name": "Test Student",
            })
            assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
            data = resp.json()
            # /auth/register returns TokenResponse: {access_token, token_type, user}
            assert "access_token" in data
            assert data["user"]["role"] == "student"
            assert data["user"]["email"] == "student@test.com"
            student_token = data["access_token"]
            print("AUTH-01 register: PASS")

            # AUTH-01: Duplicate email -> 409
            resp2 = await client.post("/auth/register", json={
                "email": "student@test.com",
                "password": "password123",
                "full_name": "Test Student",
            })
            assert resp2.status_code == 409, f"Expected 409, got {resp2.status_code}"
            print("AUTH-01 duplicate email 409: PASS")

            # AUTH-02: Login returns access_token + cookie
            resp = await client.post("/auth/login", json={
                "email": "student@test.com",
                "password": "password123",
            })
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            login_data = resp.json()
            assert "access_token" in login_data
            assert login_data["token_type"] == "bearer"
            assert "user" in login_data
            assert "refresh_token" in resp.cookies
            student_token = login_data["access_token"]
            print("AUTH-02 login access_token + cookie: PASS")

            # AUTH-02: Invalid credentials -> 401
            resp = await client.post("/auth/login", json={
                "email": "student@test.com",
                "password": "wrongpassword",
            })
            assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
            print("AUTH-02 invalid creds 401: PASS")

            # AUTH-03: Refresh with valid cookie
            resp = await client.post("/auth/login", json={
                "email": "student@test.com",
                "password": "password123",
            })
            refresh_resp = await client.post("/auth/refresh")
            assert refresh_resp.status_code == 200, f"Expected 200, got {refresh_resp.status_code}: {refresh_resp.text}"
            assert "access_token" in refresh_resp.json()
            print("AUTH-03 refresh with valid cookie: PASS")

            # AUTH-04: Logout then refresh rejected
            resp = await client.post("/auth/login", json={
                "email": "student@test.com",
                "password": "password123",
            })
            assert resp.status_code == 200
            student_token = resp.json()["access_token"]

            logout_resp = await client.post("/auth/logout")
            assert logout_resp.status_code == 200
            print("AUTH-04 logout: PASS")

            # After logout, try refresh — should fail (cookie was deleted)
            refresh_after_logout = await client.post("/auth/refresh")
            assert refresh_after_logout.status_code in (401, 403), (
                f"Expected 401/403 after logout, got {refresh_after_logout.status_code}: {refresh_after_logout.text}"
            )
            print("AUTH-04 refresh after logout rejected: PASS")

            # Re-login for student operations
            resp = await client.post("/auth/login", json={
                "email": "student@test.com",
                "password": "password123",
            })
            student_token = resp.json()["access_token"]

            # AUTH-07: student hitting /admin/users -> 403
            admin_resp = await client.post(
                "/admin/users",
                json={"email": "lib@test.com", "password": "libpass123", "full_name": "Lib"},
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert admin_resp.status_code == 403, f"Expected 403, got {admin_resp.status_code}"
            print("AUTH-07 student -> /admin/users 403: PASS")

            # AUTH-06: admin creates librarian
            from app.services.auth_service import password_hash as ph

            admin = User(
                email="admin@test.com",
                hashed_password=ph.hash("adminpass123"),
                full_name="Test Admin",
                role="admin_librarian",
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)

            resp = await client.post("/auth/login", json={
                "email": "admin@test.com",
                "password": "adminpass123",
            })
            assert resp.status_code == 200
            admin_token = resp.json()["access_token"]

            resp = await client.post(
                "/admin/users",
                json={"email": "newlib@test.com", "password": "libpass123", "full_name": "New Lib"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
            lib_data = resp.json()
            assert lib_data["role"] == "librarian"
            assert lib_data["email"] == "newlib@test.com"
            print("AUTH-06 admin creates librarian 201: PASS")

            # AUTH-06: duplicate -> 409
            resp = await client.post(
                "/admin/users",
                json={"email": "newlib@test.com", "password": "libpass123", "full_name": "Dup Lib"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert resp.status_code == 409, f"Expected 409, got {resp.status_code}"
            print("AUTH-06 duplicate librarian 409: PASS")

            # ---------------------------------------------------------------
            # Phase 2: Book catalog and borrow/return flow
            # ---------------------------------------------------------------

            # ADM-01: Admin creates a book
            resp = await client.post(
                "/admin/books",
                json={"isbn": "978-SMOKE-001", "title": "Smoke Test Book", "author": "Author", "total_copies": 2},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
            book = resp.json()
            assert book["available_copies"] == 2
            assert book["total_copies"] == 2
            book_id = book["id"]
            print("ADM-01 admin creates book 201: PASS")

            # CAT-01: Search catalog (student)
            resp = await client.get(
                "/books?q=Smoke",
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            search_data = resp.json()
            assert search_data["total"] >= 1
            assert any(b["id"] == book_id for b in search_data["items"])
            print("CAT-01 catalog search: PASS")

            # BR-01: Student submits borrow request
            resp = await client.post(
                "/borrow",
                json={"book_id": book_id},
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
            borrow_request = resp.json()
            assert borrow_request["status"] == "pending"
            request_id = borrow_request["id"]
            print("BR-01 student submits borrow request: PASS")

            # BR-01: Duplicate pending request -> 400
            resp = await client.post(
                "/borrow",
                json={"book_id": book_id},
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
            print("BR-01 duplicate pending request 400: PASS")

            # Login as librarian for approval
            resp = await client.post("/auth/login", json={
                "email": "newlib@test.com",
                "password": "libpass123",
            })
            assert resp.status_code == 200
            lib_token = resp.json()["access_token"]

            # BR-02: Librarian approves request -> creates Loan
            resp = await client.post(
                f"/borrow/{request_id}/approve",
                headers={"Authorization": f"Bearer {lib_token}"},
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            loan = resp.json()
            assert loan["status"] == "active"
            loan_id = loan["id"]
            print("BR-02 librarian approves -> loan created: PASS")

            # Check availability decreased
            resp = await client.get(
                f"/books/{book_id}",
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert resp.json()["available_copies"] == 1
            print("BR-02 availability decremented: PASS")

            # BR-02: Double approve -> 400
            resp = await client.post(
                f"/borrow/{request_id}/approve",
                headers={"Authorization": f"Bearer {lib_token}"},
            )
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
            print("BR-02 double approve 400: PASS")

            # BR-05: Librarian records return
            resp = await client.post(
                f"/loans/{loan_id}/return",
                headers={"Authorization": f"Bearer {lib_token}"},
            )
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            returned_loan = resp.json()
            assert returned_loan["status"] == "returned"
            assert returned_loan["returned_at"] is not None
            print("BR-05 librarian records return: PASS")

            # Check availability restored
            resp = await client.get(
                f"/books/{book_id}",
                headers={"Authorization": f"Bearer {student_token}"},
            )
            assert resp.json()["available_copies"] == 2
            print("BR-05 availability restored: PASS")

            # ADM-03: Admin deletes book
            resp = await client.delete(
                f"/admin/books/{book_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert resp.status_code == 204, f"Expected 204, got {resp.status_code}"
            print("ADM-03 admin deletes book 204: PASS")

            print()
            print("=" * 60)
            print("ALL INTEGRATION TESTS PASSED (SQLite in-memory)")
            print("AUTH-01..04, AUTH-06, AUTH-07: PASS")
            print("ADM-01, ADM-03, CAT-01, BR-01, BR-02, BR-05: PASS")
            print("=" * 60)

    fastapi_app.dependency_overrides.clear()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_tests())
