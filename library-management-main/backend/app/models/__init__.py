# backend/app/models/__init__.py
# Re-exports all models and Base so a single import populates Base.metadata.
# CRITICAL for Alembic env.py: import this module before target_metadata assignment
# to ensure all tables are registered (Pitfall 2 — empty migration if models not imported).

from app.models.user import Base, User
from app.models.book import Book
from app.models.borrow_request import BorrowRequest
from app.models.loan import Loan
from app.models.refresh_token_blocklist import RefreshTokenBlocklist

__all__ = ["Base", "User", "Book", "BorrowRequest", "Loan", "RefreshTokenBlocklist"]
