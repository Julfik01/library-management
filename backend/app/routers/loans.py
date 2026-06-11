# backend/app/routers/loans.py
# Read-only loan endpoints for Phase 4.

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.database import DbSession
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.schemas.loan import PaginatedLoansResponse
from app.services.loan_service import DEFAULT_PAGE_SIZE, list_student_loans, search_loans

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("/me", response_model=PaginatedLoansResponse)
async def get_my_loans(
    status: Literal["active", "history"] = Query("active"),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: DbSession = None,
) -> PaginatedLoansResponse:
    return await list_student_loans(
        db=db,
        student_id=current_user.id,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/search", response_model=PaginatedLoansResponse)
async def loan_search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1),
    current_user: Annotated[User, Depends(require_role("librarian", "admin_librarian"))] = None,
    db: DbSession = None,
) -> PaginatedLoansResponse:
    del current_user
    return await search_loans(db=db, q=q, page=page, page_size=page_size)
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
