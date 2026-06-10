"""Initial schema — complete 5-phase database schema

Revision ID: 001
Revises:
Create Date: 2026-06-11

D-01: Phase 1 creates ALL tables for all 5 phases in a single migration.
D-02: Single migration file — all tables, FKs, constraints, and indexes.

Tables created (FK dependency order):
  1. users — no FKs
  2. refresh_token_blocklist — no FKs (D-04: required for server-side logout)
  3. books — no FKs
  4. borrow_requests — FK -> users, FK -> books
  5. loans — FK -> borrow_requests, FK -> users, FK -> books

Constraints:
  - users.role VARCHAR CHECK IN ('student','librarian','admin_librarian')
  - books.available_copies CHECK >= 0 (CP-1)
  - books.available_copies CHECK <= total_copies (CP-1)
  - borrow_requests.status VARCHAR CHECK IN ('pending','approved','rejected') (D-05)
  - loans.status VARCHAR CHECK IN ('active','returned','overdue') (D-05)

Indexes (D-07):
  - UNIQUE ix_users_email
  - UNIQUE ix_books_isbn
  - ix_borrow_requests_status (for pending queue query)
  - ix_loans_due_date (for nightly overdue job)
  - GIN ix_books_fulltext on to_tsvector('english', title || ' ' || author) — CAT-05

Seed (D-10, AUTH-05):
  - admin_librarian user from ADMIN_EMAIL + ADMIN_PASSWORD env vars, argon2-hashed
"""

import os
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # =========================================================================
    # 1. users — no FKs
    # =========================================================================
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "hashed_password", sa.String(255), nullable=False
        ),  # FastAPI docs convention
        sa.Column("full_name", sa.String(255), nullable=False),  # D-03
        sa.Column(
            "role", sa.String(20), nullable=False, server_default="student"
        ),  # D-05
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "role IN ('student','librarian','admin_librarian')", name="ck_users_role"
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)  # D-07

    # =========================================================================
    # 2. refresh_token_blocklist — no FKs (D-04)
    # Required for server-side refresh token invalidation on logout (AUTH-04).
    # =========================================================================
    op.create_table(
        "refresh_token_blocklist",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "token_hash", sa.String(64), nullable=False, unique=True
        ),  # SHA-256 of token
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # =========================================================================
    # 3. books — no FKs
    # =========================================================================
    op.create_table(
        "books",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("isbn", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("total_copies", sa.Integer, nullable=False),
        sa.Column(
            "available_copies", sa.Integer, nullable=False
        ),  # CP-1 constraints below
        sa.CheckConstraint(
            "available_copies >= 0", name="ck_books_available_nonnegative"
        ),
        sa.CheckConstraint(
            "available_copies <= total_copies", name="ck_books_available_lte_total"
        ),
    )
    op.create_index("ix_books_isbn", "books", ["isbn"], unique=True)  # D-07
    # D-07: GIN full-text index for catalog search (CAT-05)
    # Must be created via raw SQL — SQLAlchemy Index() does not support GIN with expressions
    op.execute(
        "CREATE INDEX ix_books_fulltext ON books "
        "USING gin(to_tsvector('english', title || ' ' || author))"
    )

    # =========================================================================
    # 4. borrow_requests — FK -> users, FK -> books
    # =========================================================================
    op.create_table(
        "borrow_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "student_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "book_id", sa.Integer, sa.ForeignKey("books.id"), nullable=False
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="pending"
        ),  # D-05
        sa.Column(
            "requested_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "reviewed_by",
            sa.Integer,
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "status IN ('pending','approved','rejected')",
            name="ck_borrow_requests_status",
        ),
    )
    op.create_index(
        "ix_borrow_requests_status", "borrow_requests", ["status"]
    )  # D-07

    # =========================================================================
    # 5. loans — FK -> borrow_requests, FK -> users, FK -> books
    # =========================================================================
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "borrow_request_id",
            sa.Integer,
            sa.ForeignKey("borrow_requests.id"),
            nullable=False,
        ),
        sa.Column(
            "student_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "book_id", sa.Integer, sa.ForeignKey("books.id"), nullable=False
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="active"
        ),  # D-05
        sa.Column("loan_date", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "due_date", sa.TIMESTAMP(timezone=True), nullable=False
        ),  # 14-day fixed period
        sa.Column("returned_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "overdue_notified_at", sa.TIMESTAMP(timezone=True), nullable=True
        ),  # D-06
        sa.CheckConstraint(
            "status IN ('active','returned','overdue')", name="ck_loans_status"
        ),
    )
    op.create_index("ix_loans_due_date", "loans", ["due_date"])  # D-07

    # =========================================================================
    # D-10: Admin librarian seed from environment variables (AUTH-05)
    # Password is hashed with argon2 before INSERT — never stored plaintext.
    # T-01-03: Password sourced from ADMIN_PASSWORD env var (operator-controlled).
    # =========================================================================
    from pwdlib import PasswordHash  # imported here to avoid module-level dep at migration import

    password_hash = PasswordHash.recommended()
    admin_email = os.environ["ADMIN_EMAIL"]
    admin_password = os.environ["ADMIN_PASSWORD"]
    hashed = password_hash.hash(admin_password)

    op.execute(
        sa.text(
            "INSERT INTO users (email, hashed_password, full_name, role) "
            "VALUES (:email, :hashed_password, :full_name, 'admin_librarian')"
        ).bindparams(
            email=admin_email,
            hashed_password=hashed,
            full_name="System Admin",
        )
    )


def downgrade() -> None:
    # Drop in reverse FK dependency order
    op.drop_table("loans")
    op.drop_table("borrow_requests")
    op.drop_table("books")
    op.drop_table("refresh_token_blocklist")
    op.drop_table("users")
