# backend/app/routers/borrow.py
# Borrow/Return workflow endpoints.
#
# BR-01: POST /borrow — student submits a borrow request
# BR-02: POST /borrow/{id}/approve — librarian/admin approves request → creates Loan
# BR-03: POST /borrow/{id}/reject — librarian/admin rejects request
# BR-04: GET /borrow — list borrow requests (filtered by role)
# BR-05: POST /loans/{id}/return — librarian/admin records return
# BR-06: GET /loans — list loans (filtered by role)
#
# CM-7: Backend RBAC is the authority — students cannot approve their own requests.
# CP-1: Availability checks in service layer + DB-level CHECK constraints.

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import DbSession
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.schemas.borrow import BorrowRequestCreate, BorrowRequestOut, LoanOut
from app.services import borrow_service

router = APIRouter()


@router.post("", response_model=BorrowRequestOut, status_code=status.HTTP_201_CREATED)
async def create_borrow_request(
    data: BorrowRequestCreate,
    current_user: Annotated[User, Depends(require_role("student"))],
    db: DbSession,
) -> BorrowRequestOut:
    """
    BR-01: Student submits a borrow request.

    Access: student only.
    Returns 201 Created with the new BorrowRequest.
    Returns 400 if book not found, no copies available, or duplicate pending request.
    """
    try:
        borrow_request = await borrow_service.create_borrow_request(
            db, current_user.id, data.book_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return BorrowRequestOut.model_validate(borrow_request)


@router.get("", response_model=list[BorrowRequestOut])
async def list_borrow_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    status_filter: Optional[str] = Query(None, alias="status"),
) -> list[BorrowRequestOut]:
    """
    BR-04: List borrow requests.

    Access:
      - students: see only their own requests
      - librarians/admin_librarians: see all requests

    Optional query param ?status=pending|approved|rejected to filter.
    """
    student_id = current_user.id if current_user.role == "student" else None
    requests = await borrow_service.get_borrow_requests(
        db, student_id=student_id, status=status_filter
    )
    return [BorrowRequestOut.model_validate(r) for r in requests]


@router.post("/{request_id}/approve", response_model=LoanOut)
async def approve_borrow_request(
    request_id: int,
    current_user: Annotated[User, Depends(require_role("librarian", "admin_librarian"))],
    db: DbSession,
) -> LoanOut:
    """
    BR-02: Librarian approves a pending borrow request → creates a Loan.

    Access: librarian and admin_librarian only.
    Returns the created Loan.
    Returns 400 if request not found, not pending, or no copies available.
    """
    try:
        loan = await borrow_service.approve_borrow_request(
            db, request_id, current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return LoanOut.model_validate(loan)


@router.post("/{request_id}/reject", response_model=BorrowRequestOut)
async def reject_borrow_request(
    request_id: int,
    current_user: Annotated[User, Depends(require_role("librarian", "admin_librarian"))],
    db: DbSession,
) -> BorrowRequestOut:
    """
    BR-03: Librarian rejects a pending borrow request.

    Access: librarian and admin_librarian only.
    Returns the updated BorrowRequest with status='rejected'.
    Returns 400 if request not found or not pending.
    """
    try:
        borrow_request = await borrow_service.reject_borrow_request(
            db, request_id, current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return BorrowRequestOut.model_validate(borrow_request)
