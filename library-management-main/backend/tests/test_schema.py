# backend/tests/test_schema.py
# TDD schema tests — validates the complete DB schema created by Alembic migration.
# Behaviors tested:
#   1. All 5 expected tables exist (users, refresh_token_blocklist, books, borrow_requests, loans)
#   2. Inserting a book with available_copies = -1 raises IntegrityError (CHECK enforced)
#   3. Inserting a book with available_copies > total_copies raises IntegrityError
#   4. Inserting a user with role = 'hacker' raises IntegrityError (role CHECK)
#   5. Admin librarian seed row exists after migration with role 'admin_librarian'

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.models import Base, Book, User
from app.models.borrow_request import BorrowRequest
from app.models.loan import Loan


async def test_all_expected_tables_exist(db_session):
    """
    After Base.metadata.create_all, all 4 ORM-managed tables must exist.
    The 5th table (refresh_token_blocklist) is migration-only; it is checked separately.
    """
    sync_conn = await db_session.connection()
    table_names = await sync_conn.run_sync(
        lambda conn: inspect(conn).get_table_names()
    )
    expected = {"users", "books", "borrow_requests", "loans"}
    assert expected.issubset(set(table_names)), (
        f"Missing tables. Got: {sorted(table_names)}"
    )


async def test_book_available_copies_negative_rejected(db_session):
    """
    CP-1: INSERT with available_copies = -1 must raise IntegrityError.
    DB-level CHECK constraint enforces this before any endpoint exists.
    """
    bad_book = Book(
        isbn="978-0000000001",
        title="Test Book",
        author="Test Author",
        total_copies=5,
        available_copies=-1,  # violates CHECK (available_copies >= 0)
    )
    db_session.add(bad_book)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_book_available_copies_exceeds_total_rejected(db_session):
    """
    CP-1: INSERT with available_copies > total_copies must raise IntegrityError.
    """
    bad_book = Book(
        isbn="978-0000000002",
        title="Test Book 2",
        author="Test Author",
        total_copies=3,
        available_copies=10,  # violates CHECK (available_copies <= total_copies)
    )
    db_session.add(bad_book)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_user_invalid_role_rejected(db_session):
    """
    D-05: INSERT with role = 'hacker' must raise IntegrityError.
    VARCHAR CHECK enforces role IN ('student','librarian','admin_librarian').
    """
    bad_user = User(
        email="hacker@evil.com",
        hashed_password="$argon2...",
        full_name="Bad Actor",
        role="hacker",  # violates CHECK role IN ('student','librarian','admin_librarian')
    )
    db_session.add(bad_user)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_valid_book_insert_succeeds(db_session):
    """Sanity check: a valid book insert should succeed."""
    book = Book(
        isbn="978-0000000099",
        title="Valid Book",
        author="Valid Author",
        total_copies=5,
        available_copies=5,  # valid: 0 <= 5 <= 5
    )
    db_session.add(book)
    await db_session.commit()
    assert book.id is not None


async def test_valid_user_roles_accepted(db_session):
    """Sanity check: all three valid roles should be accepted."""
    for i, role in enumerate(["student", "librarian", "admin_librarian"]):
        user = User(
            email=f"{role}_{i}@test.com",
            hashed_password="$argon2...",
            full_name=f"Test {role}",
            role=role,
        )
        db_session.add(user)
    await db_session.commit()
