# backend/app/routers/loans.py
# Loan endpoints.
#
# BR-05: POST /loans/{id}/return — librarian records a book return
# BR-06: GET /loans — list loans (filtered by role)
#
# CM-7: Backend RBAC is the authority.
# CP-1: Returning a loan increments available_copies (service layer enforces).

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import DbSession
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.schemas.borrow import LoanOut
from app.services import borrow_service

router = APIRouter()


@router.get("", response_model=list[LoanOut])
async def list_loans(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    status_filter: Optional[str] = Query(None, alias="status"),
) -> list[LoanOut]:
    """
    BR-06: List loans.

    Access:
      - students: see only their own loans
      - librarians/admin_librarians: see all loans

    Optional query param ?status=active|returned|overdue to filter.
    """
    student_id = current_user.id if current_user.role == "student" else None
    loans = await borrow_service.get_loans(db, student_id=student_id, status=status_filter)
    return [LoanOut.model_validate(loan) for loan in loans]


@router.post("/{loan_id}/return", response_model=LoanOut)
async def return_loan(
    loan_id: int,
    current_user: Annotated[User, Depends(require_role("librarian", "admin_librarian"))],
    db: DbSession,
) -> LoanOut:
    """
    BR-05: Librarian records a book return.

    Access: librarian and admin_librarian only.
    Returns the updated Loan with status='returned' and returned_at timestamp.
    Returns 400 if loan not found or already returned.
    """
    try:
        loan = await borrow_service.return_loan(db, loan_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return LoanOut.model_validate(loan)
