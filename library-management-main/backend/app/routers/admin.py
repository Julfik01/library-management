# backend/app/routers/admin.py
# Admin endpoints: librarian account creation.
#
# AUTH-06: POST /admin/users — admin_librarian creates librarian accounts
# AUTH-07: require_role("admin_librarian") enforced as FastAPI dependency (D-09, CM-7)
#
# CM-7: Backend RBAC is the authority — frontend role checks are UX convenience only.
#       This endpoint will return 403 for any non-admin_librarian token regardless
#       of what the frontend claims.

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.database import DbSession
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.user import CreateLibrarianRequest, UserOut
from app.services.auth_service import password_hash

router = APIRouter()


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
