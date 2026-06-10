# backend/app/routers/auth.py
# Authentication endpoints: register, login, refresh, logout.
#
# AUTH-01: POST /auth/register — student self-registration
# AUTH-02: POST /auth/login — returns access_token + sets httpOnly refresh cookie
# AUTH-03: POST /auth/refresh — exchanges refresh cookie for new access_token
# AUTH-04: POST /auth/logout — blocklists refresh token, deletes cookie
#
# D-08: Access token in response body only; refresh token in httpOnly SameSite=Lax cookie.
# D-04: Logout MUST insert into refresh_token_blocklist — cookie deletion alone is insufficient.
# T-02-02: Access token never stored server-side (held in React Context only).
# T-02-03: Refresh cookie set SameSite=Lax (CSRF protection on /auth/refresh).
# Pitfall 3: Stale cookie after logout — always blocklist server-side before cookie deletion.
# Pitfall 4: CORS — wildcard origin forbidden with credentials (handled in main.py).

from typing import Optional

import jwt
from fastapi import APIRouter, Cookie, HTTPException, Response, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select

from app.config import settings
from app.database import DbSession
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.auth_service import (
    ALGORITHM,
    REFRESH_TOKEN_EXPIRE_DAYS,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    insert_into_blocklist,
    is_token_blocklisted,
    password_hash,
    store_refresh_token,
)

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: DbSession) -> UserOut:
    """
    AUTH-01: Student self-registration.

    Creates a user with role='student', hashes password with argon2.
    Returns 409 if email already registered.
    Returns 201 Created with UserOut on success.
    """
    # Check for duplicate email
    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Hash password with pwdlib[argon2] (CLAUDE.md constraint — NOT passlib)
    hashed = password_hash.hash(data.password)

    new_user = User(
        email=data.email,
        hashed_password=hashed,
        full_name=data.full_name,
        role="student",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return UserOut.model_validate(new_user)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, response: Response, db: DbSession) -> TokenResponse:
    """
    AUTH-02: Login with email and password.

    Returns:
      - access_token in response body (client holds in React Context — D-08)
      - refresh_token in httpOnly SameSite=Lax cookie (browser auto-sends on /auth requests)

    Cookie attributes:
      - httponly=True  — XSS protection (T-02-02)
      - samesite="lax" — CSRF protection on /auth/refresh (T-02-03)
      - secure=True    — in production only
      - path="/auth"   — scopes cookie to /auth/refresh and /auth/logout
    """
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token = create_access_token(user.id, user.role, settings.SECRET_KEY)
    refresh_token = create_refresh_token(user.id, settings.SECRET_KEY)

    # Store token (no-op in current blocklist-only design, but keeps API stable)
    await store_refresh_token(db, user.id, refresh_token)

    # Set httpOnly cookie — refresh token NEVER in response body (D-08)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=60 * 60 * 24 * REFRESH_TOKEN_EXPIRE_DAYS,
        path="/auth",  # scopes cookie to /auth/* — both /auth/refresh and /auth/logout
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserOut.model_validate(user),
    )


@router.post("/refresh")
async def refresh(
    db: DbSession,
    refresh_token: Optional[str] = Cookie(None),
) -> dict:
    """
    AUTH-03: Exchange a valid refresh cookie for a new access_token.

    Validates:
      1. Cookie present (401 if missing)
      2. Not in blocklist — D-04 (401 if blocklisted, prevents post-logout replay T-02-04)
      3. JWT signature and expiry valid (401 if invalid)
      4. Token type == "refresh" (prevents access tokens being reused here)
      5. User still exists (401 if not)

    Returns new access_token in response body only.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    # D-04: Check blocklist BEFORE any decode — prevents replay after logout (T-02-04)
    if await is_token_blocklisted(db, refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    # Validate JWT signature and expiry
    try:
        # CRITICAL: algorithms=["HS256"] — never None (T-02-01)
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
        token_type = payload.get("type")
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Validate token type
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Verify user still exists
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Issue new access token
    new_access_token = create_access_token(user.id, user.role, settings.SECRET_KEY)
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
    response: Response,
    db: DbSession,
    refresh_token: Optional[str] = Cookie(None),
) -> dict:
    """
    AUTH-04: Server-side logout.

    Steps (Pitfall 3 — BOTH steps required for correct invalidation):
      1. INSERT refresh token hash into blocklist — prevents replay (D-04, T-02-04)
      2. Delete the httpOnly cookie from the browser

    If no cookie is present (already logged out or cookie expired), we still
    return success and clear any stale cookie.
    """
    if refresh_token:
        # D-04: Server-side invalidation — cookie deletion alone is insufficient (Pitfall 3)
        await insert_into_blocklist(db, refresh_token)

    # Delete the httpOnly cookie — must match the path set on login
    response.delete_cookie(key="refresh_token", path="/auth")

    return {"message": "Logged out successfully"}
