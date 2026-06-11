# backend/app/routers/books.py
# Book catalog endpoints.
#
# CAT-01: GET /books — search catalog (authenticated, all roles)
# CAT-02: GET /books/{id} — get a single book detail
#
# Search uses ILIKE on title/author/ISBN (case-insensitive, paginated).
# CAT-05: target < 500ms on local env.

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import DbSession
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.book import BookOut, BookSearchResponse
from app.services.book_service import get_book, search_books

router = APIRouter()


@router.get("", response_model=BookSearchResponse)
async def list_books(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    q: Optional[str] = Query(None, description="Search by title, author, or ISBN"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> BookSearchResponse:
    """
    CAT-01: Search the book catalog.

    Query parameters:
      - q: optional search string (matches title, author, ISBN — case-insensitive)
      - page: page number (default 1)
      - page_size: items per page (default 20, max 100)

    Returns paginated BookSearchResponse with items, total, page, page_size, pages.
    All authenticated roles can access this endpoint.
    """
    result = await search_books(db, q=q, page=page, page_size=page_size)
    return BookSearchResponse(**result)


@router.get("/{book_id}", response_model=BookOut)
async def get_book_detail(
    book_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> BookOut:
    """
    CAT-02: Get a single book's details by ID.
    Returns 404 if book not found.
    All authenticated roles can access this endpoint.
    """
    book = await get_book(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )
    return BookOut.model_validate(book)
