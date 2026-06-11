from pydantic import BaseModel
from datetime import datetime


class BorrowRequestCreate(BaseModel):
    book_id: int


class BorrowRequestOut(BaseModel):
    id: int
    student_id: int
    book_id: int
    status: str
    requested_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: int | None = None

    model_config = {"from_attributes": True}
