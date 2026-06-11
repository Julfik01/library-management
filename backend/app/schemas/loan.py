from pydantic import BaseModel
from datetime import datetime


class LoanOut(BaseModel):
    id: int
    borrow_request_id: int
    student_id: int
    book_id: int
    status: str
    loan_date: datetime
    due_date: datetime
    returned_at: datetime | None = None

    model_config = {"from_attributes": True}


class LoanListQuery(BaseModel):
    status: str | None = None
