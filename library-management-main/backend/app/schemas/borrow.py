# backend/app/schemas/borrow.py
# Pydantic v2 schemas for borrow request and loan endpoints.

import datetime
from typing import Optional

from pydantic import BaseModel


class BorrowRequestCreate(BaseModel):
    book_id: int


class BorrowRequestOut(BaseModel):
    id: int
    student_id: int
    book_id: int
    status: str
    requested_at: datetime.datetime
    reviewed_at: Optional[datetime.datetime] = None
    reviewed_by: Optional[int] = None

    model_config = {"from_attributes": True}


class LoanOut(BaseModel):
    id: int
    borrow_request_id: int
    student_id: int
    book_id: int
    status: str
    loan_date: datetime.datetime
    due_date: datetime.datetime
    returned_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}
