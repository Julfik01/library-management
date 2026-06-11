# backend/app/routers/admin.py
# Admin endpoints: librarian account creation and book catalog management.
#
# AUTH-06: POST /admin/users — admin_librarian creates librarian accounts
# AUTH-07: require_role("admin_librarian") enforced as FastAPI dependency (D-09, CM-7)
#
# ADM-01: POST /admin/books — add a book to the catalog
# ADM-02: PUT /admin/books/{id} — update a book record
# ADM-03: DELETE /admin/books/{id} — remove a book from the catalog
#
# CM-7: Backend RBAC is the authority — frontend role checks are UX convenience only.
#       These endpoints return 403 for any non-admin_librarian token regardless
#       of what the frontend claims.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import DbSession
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.book import BookCreate, BookOut, BookUpdate
from app.schemas.user import CreateLibrarianRequest, UserOut
from app.services.auth_service import password_hash
from app.services.book_service import create_book, delete_book, get_book, update_book

router = APIRouter()


# ---------------------------------------------------------------------------
# User management (librarian creation)
# ---------------------------------------------------------------------------

@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_librarian(
    data: CreateLibrarianRequest,
    current_user: Annotated[User, Depends(require_role("admin_librarian"))],
    db: DbSession,
) -> UserOut:
    """
    AUTH-06: Create a new librarian account.

    Access: admin_librarian only (AUTH-07, D-09, CM-7).
    Returns 403 if called by a non-admin user — enforced by require_role dependency.
    Returns 409 if email already registered.
    Returns 201 Created with UserOut on success.

    The new user is created with role='librarian'.
    """
    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Hash password with pwdlib[argon2]
    hashed = password_hash.hash(data.password)

    new_librarian = User(
        email=data.email,
        hashed_password=hashed,
        full_name=data.full_name,
        role="librarian",
    )
    db.add(new_librarian)
    await db.commit()
    await db.refresh(new_librarian)

    return UserOut.model_validate(new_librarian)


# ---------------------------------------------------------------------------
# Book catalog management
# ---------------------------------------------------------------------------

@router.post("/books", response_model=BookOut, status_code=status.HTTP_201_CREATED)
async def admin_create_book(
    data: BookCreate,
    current_user: Annotated[User, Depends(require_role("admin_librarian", "librarian"))],
    db: DbSession,
) -> BookOut:
    """
    ADM-01: Add a new book to the catalog.

    Access: admin_librarian and librarian.
    Returns 201 Created with the new Book on success.
    Returns 409 if ISBN already exists.

    available_copies is set equal to total_copies on creation.
    """
    try:
        book = await create_book(db, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A book with this ISBN already exists",
        )
    return BookOut.model_validate(book)


@router.put("/books/{book_id}", response_model=BookOut)
async def admin_update_book(
    book_id: int,
    data: BookUpdate,
    current_user: Annotated[User, Depends(require_role("admin_librarian", "librarian"))],
    db: DbSession,
) -> BookOut:
    """
    ADM-02: Update a book record.

    Access: admin_librarian and librarian.
    Returns 404 if book not found.
    Returns 409 if the new ISBN conflicts with an existing book.

    If total_copies changes, available_copies is adjusted proportionally (CP-1).
    """
    book = await get_book(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )
    try:
        updated = await update_book(db, book, data)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A book with this ISBN already exists",
        )
    return BookOut.model_validate(updated)


@router.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_book(
    book_id: int,
    current_user: Annotated[User, Depends(require_role("admin_librarian"))],
    db: DbSession,
) -> None:
    """
    ADM-03: Remove a book from the catalog.

    Access: admin_librarian only (destructive operation).
    Returns 404 if book not found.
    Returns 204 No Content on success.
    """
    book = await get_book(db, book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )
    await delete_book(db, book)
