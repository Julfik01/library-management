# backend/app/schemas/auth.py
# Pydantic v2 schemas for authentication request/response bodies.
# CLAUDE.md: Pydantic v2 required (model_config, EmailStr).

from pydantic import BaseModel, EmailStr, field_validator

from app.schemas.user import UserOut


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
