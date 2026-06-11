# backend/app/services/book_service.py
# Business logic for book catalog: search with title/author/ISBN filters and pagination.
# CP-1: Never manipulate available_copies without an availability check first.
# D-07: Search uses ILIKE for case-insensitive matching (GIN index created in migration).

import math
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.schemas.book import BookCreate, BookUpdate


async def search_books(
    db: AsyncSession,
    q: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """
    Search books by title, author, or ISBN using ILIKE (case-insensitive).
    Returns paginated results with total count.

    Accepts:
      - q: optional query string (matches title, author, ISBN via OR)
      - page: 1-indexed page number
      - page_size: items per page (capped at 100)

    CAT-05: Search hit rate < 500ms on local env — ILIKE is sufficient for
    university scale; GIN index is added in the migration for production.
    """
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size

    # Build filter — OR across title/author/ISBN if query provided
    stmt = select(Book)
    count_stmt = select(func.count()).select_from(Book)

    if q and q.strip():
        pattern = f"%{q.strip()}%"
        search_filter = or_(
            Book.title.ilike(pattern),
            Book.author.ilike(pattern),
            Book.isbn.ilike(pattern),
        )
        stmt = stmt.where(search_filter)
        count_stmt = count_stmt.where(search_filter)

    # Total count for pagination metadata
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Paginated results
    stmt = stmt.offset(offset).limit(page_size).order_by(Book.id)
    result = await db.execute(stmt)
    books = result.scalars().all()

    return {
        "items": books,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total > 0 else 1,
    }


async def get_book(db: AsyncSession, book_id: int) -> Optional[Book]:
    """Get a single book by ID, or None if not found."""
    return await db.get(Book, book_id)


async def create_book(db: AsyncSession, data: BookCreate) -> Book:
    """
    Create a new book. available_copies starts equal to total_copies.
    Returns the created Book ORM instance.
    Raises IntegrityError if ISBN already exists (unique constraint).
    """
    book = Book(
        isbn=data.isbn,
        title=data.title,
        author=data.author,
        total_copies=data.total_copies,
        available_copies=data.total_copies,  # All copies available on creation
    )
    db.add(book)
    await db.commit()
    await db.refresh(book)
    return book


async def update_book(db: AsyncSession, book: Book, data: BookUpdate) -> Book:
    """
    Update a book record. Adjusts available_copies proportionally if total_copies changes.
    CP-1: Ensures available_copies never goes negative or exceeds total_copies.
    """
    if data.isbn is not None:
        book.isbn = data.isbn
    if data.title is not None:
        book.title = data.title
    if data.author is not None:
        book.author = data.author
    if data.total_copies is not None:
        old_total = book.total_copies
        new_total = data.total_copies
        borrowed = old_total - book.available_copies
        # CP-1: available = new_total - borrowed, clamped to [0, new_total]
        new_available = max(0, min(new_total, new_total - borrowed))
        book.total_copies = new_total
        book.available_copies = new_available

    await db.commit()
    await db.refresh(book)
    return book


async def delete_book(db: AsyncSession, book: Book) -> None:
    """
    Delete a book record.
    Caller should check for active loans before deletion.
    """
    await db.delete(book)
    await db.commit()
