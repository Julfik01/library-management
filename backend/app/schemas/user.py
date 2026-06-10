# backend/app/schemas/user.py
# Pydantic v2 schemas for user-related output and admin input.
# CLAUDE.md: Pydantic v2 (model_config from_attributes=True, EmailStr).

from pydantic import BaseModel, EmailStr, field_validator


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}  # Pydantic v2 ORM mode


class CreateLibrarianRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
