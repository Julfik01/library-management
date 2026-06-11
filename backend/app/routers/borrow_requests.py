from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.database import DbSession
from app.dependencies.auth import get_current_user, require_role
from app.schemas.borrow_request import BorrowRequestCreate, BorrowRequestOut
from app.services.borrow_service import create_borrow_request, approve_borrow_request, reject_borrow_request
from app.models.user import User
from app.models.borrow_request import BorrowRequest

router = APIRouter()


@router.post("", response_model=BorrowRequestOut, status_code=status.HTTP_201_CREATED)
async def post_borrow_request(
    data: BorrowRequestCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> BorrowRequestOut:
    """Student creates a borrow request for a book."""
    br = await create_borrow_request(db, current_user.id, data.book_id)
    return BorrowRequestOut.model_validate(br)


@router.get("", response_model=list[BorrowRequestOut])
async def list_borrow_requests(
    status: str | None = None,
    current_user: Annotated[User, Depends(require_role("librarian"))],
    db: DbSession,
) -> list[BorrowRequestOut]:
    """Librarian: list borrow requests (filter by status optionally)."""
    stmt = select(BorrowRequest)
    if status:
        stmt = stmt.where(BorrowRequest.status == status)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [BorrowRequestOut.model_validate(r) for r in rows]


@router.post("/{id}/approve")
async def approve(
    id: int,
    current_user: Annotated[User, Depends(require_role("librarian"))],
    db: DbSession,
):
    """Librarian approves a pending borrow request — returns loan_id on success."""
    loan_id = await approve_borrow_request(db, id, current_user.id)
    return {"loan_id": loan_id}


@router.post("/{id}/reject")
async def reject(
    id: int,
    current_user: Annotated[User, Depends(require_role("librarian"))],
    db: DbSession,
):
    await reject_borrow_request(db, id, current_user.id)
    return {"message": "rejected"}
