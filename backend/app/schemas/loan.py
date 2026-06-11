# backend/app/schemas/loan.py
# Read models for Phase 4 loan views and librarian search.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class LoanListItem(BaseModel):
    id: int
    book_title: str
    student_name: str
    loan_date: datetime
    due_date: datetime
    returned_at: datetime | None
    status: Literal["active", "returned", "overdue"]
    is_overdue: bool
    outcome: str

    model_config = {"from_attributes": True}


class PaginatedLoansResponse(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: list[LoanListItem]
