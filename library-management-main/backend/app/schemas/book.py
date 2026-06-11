# backend/app/schemas/book.py
# Pydantic v2 schemas for book catalog endpoints.
# CLAUDE.md: Pydantic v2 (model_config from_attributes=True, EmailStr).

from typing import Optional

from pydantic import BaseModel, field_validator


class BookOut(BaseModel):
    id: int
    isbn: str
    title: str
    author: str
    total_copies: int
    available_copies: int

    model_config = {"from_attributes": True}  # Pydantic v2 ORM mode


class BookCreate(BaseModel):
    isbn: str
    title: str
    author: str
    total_copies: int

    @field_validator("total_copies")
    @classmethod
    def total_copies_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("total_copies must be at least 1")
        return v

    @field_validator("isbn")
    @classmethod
    def isbn_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ISBN must not be empty")
        return v.strip()

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title must not be empty")
        return v.strip()

    @field_validator("author")
    @classmethod
    def author_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Author must not be empty")
        return v.strip()


class BookUpdate(BaseModel):
    isbn: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    total_copies: Optional[int] = None

    @field_validator("total_copies")
    @classmethod
    def total_copies_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("total_copies must be at least 1")
        return v


class BookSearchResponse(BaseModel):
    items: list[BookOut]
    total: int
    page: int
    page_size: int
    pages: int
