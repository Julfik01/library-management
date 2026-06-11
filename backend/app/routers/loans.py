from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.database import DbSession
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.models.loan import Loan
from app.schemas.loan import LoanOut
from app.services.loan_service import return_loan, list_loans

router = APIRouter()


@router.get("", response_model=list[LoanOut])
async def get_loans(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    status: str | None = None,
) -> list[LoanOut]:
    """List loans. Students see their own loans; librarians see all."""
    loans = await list_loans(db, current_user, status)
    return [LoanOut.model_validate(l) for l in loans]


@router.post("/{id}/return")
async def post_return(
    id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
):
    await return_loan(db, id, current_user)
    return {"message": "returned"}
