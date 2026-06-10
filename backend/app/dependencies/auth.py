# backend/app/dependencies/auth.py
# FastAPI dependencies for authentication and role-based access control.
#
# PATTERNS.md Pattern 3: require_role dependency factory.
# CLAUDE.md: Backend-enforced RBAC — frontend routing is UX-only (CM-7).
# T-02-01: jwt.decode always uses algorithms=["HS256"] — never None.
# D-09: Every protected endpoint uses require_role — not just frontend check.

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError

from app.config import settings
from app.database import DbSession
from app.models.user import User

# OAuth2PasswordBearer extracts the Bearer token from the Authorization header.
# tokenUrl="/auth/login" is used by OpenAPI docs — does NOT need to match the actual endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    """
    Decode the JWT access token and load the corresponding User from DB.

    Security:
      - algorithms=["HS256"] explicitly specified — algorithm confusion defense (T-02-01)
      - Validates token type == "access" — prevents refresh tokens being accepted as access tokens
      - Returns 401 for any decode failure, missing claim, or missing user

    Used as a dependency by all authenticated endpoints.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # CRITICAL: always pass algorithms=["HS256"] — never algorithms=None (T-02-01)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id_str: str = payload.get("sub")
        role: str = payload.get("role")
        token_type: str = payload.get("type")

        if user_id_str is None or role is None:
            raise credentials_exception
        # Prevent refresh tokens from being used as access tokens
        if token_type != "access":
            raise credentials_exception

        user_id = int(user_id_str)
    except (InvalidTokenError, KeyError, ValueError):
        raise credentials_exception

    user = await db.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user


def require_role(*roles: str):
    """
    Dependency factory that enforces role membership.

    Usage:
        @router.post("/admin/users")
        async def create_librarian(
            current_user: Annotated[User, Depends(require_role("admin_librarian"))],
            ...
        ):

    Returns the current User if their role is in `roles`.
    Raises HTTP 403 if the role does not match (AUTH-07, D-09, CM-7).

    This is the backend authority — frontend routing is UX convenience only.
    """
    async def check_role(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {roles}",
            )
        return current_user
    return check_role
