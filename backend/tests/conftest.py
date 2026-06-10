# backend/tests/conftest.py
# Test fixtures for async DB session and HTTP client.
# Uses an in-process SQLite DB for schema tests (no external DB needed for structure checks).
# For integration tests that need PostgreSQL specifics (GIN index, CHECK enforcement),
# tests use the function-scoped db_session fixture with Base.metadata.create_all.

import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.database import get_db
from app.models.user import Base

# Test database URL — uses PostgreSQL for CHECK constraint enforcement tests.
# Falls back to SQLite for basic schema existence tests.
# CHECK constraints with SQLite are not enforced by default (requires pragma).
# The CI/integration tests use PostgreSQL to verify constraint enforcement.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://libraryuser:changeme_postgres_password@localhost:5432/library_db"
)


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a fresh async engine for each test function."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """
    Function-scoped async DB session fixture.
    Creates all tables before test, drops all after test.
    """
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with async_session() as session:
        yield session

    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """
    HTTP test client fixture that overrides the get_db dependency
    to use the test DB session.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()
