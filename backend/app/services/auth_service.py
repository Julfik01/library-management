# backend/app/services/auth_service.py
# JWT token creation, password hashing, user authentication, and refresh token blocklist.
#
# CLAUDE.md constraints enforced:
#   - PyJWT only (NOT python-jose — has CVEs)
#   - pwdlib[argon2] only (NOT passlib — unmaintained)
#   - jwt.decode always uses algorithms=["HS256"] — algorithm confusion defense (T-02-01)
#   - authenticate_user verifies against DUMMY_HASH when user absent — timing oracle defense (T-02-06)
#   - refresh token blocklist via SHA-256 hash (D-04, AUTH-04)
#
# Blocklist design:
#   - Table contains ONLY invalidated tokens.
#   - Token NOT in table → valid.
#   - Token IN table → blocked (logout) → reject at /auth/refresh.

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pwdlib import PasswordHash

from app.models.user import User

# ---------------------------------------------------------------------------
# Password hashing — pwdlib[argon2] (CLAUDE.md constraint)
# ---------------------------------------------------------------------------
password_hash = PasswordHash.recommended()

# Timing-attack mitigation: pre-compute a dummy hash to verify against when
# a user is not found — prevents leaking email existence via response time.
# (RESEARCH.md Security Domain, T-02-06)
DUMMY_HASH = password_hash.hash("dummy_password_for_timing_attack_prevention")

# ---------------------------------------------------------------------------
# Token constants
# ---------------------------------------------------------------------------
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# Token creation — PyJWT (CLAUDE.md constraint; python-jose is forbidden)
# ---------------------------------------------------------------------------

def create_access_token(user_id: int, role: str, secret: str) -> str:
    """
    Create a short-lived JWT access token.

    Payload includes:
      - sub: str(user_id)  — JWT standard claim
      - role: str          — for RBAC enforcement in require_role
      - type: "access"     — prevents refresh tokens being used as access tokens
      - exp: 15 minutes    — short-lived; held in React Context only (D-08)

    Security: always uses ALGORITHM="HS256" — never None (T-02-01 algorithm confusion).
    """
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_refresh_token(user_id: int, secret: str) -> str:
    """
    Create a long-lived JWT refresh token.

    Payload includes:
      - sub: str(user_id)
      - type: "refresh"    — prevents access tokens being used for refresh
      - exp: 7 days        — stored in httpOnly SameSite=Lax cookie (D-08)
    """
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Refresh token storage helpers
# ---------------------------------------------------------------------------

async def store_refresh_token(db: AsyncSession, user_id: int, token: str) -> None:
    """
    Store the refresh token hash in the blocklist table as an issued (valid) record.

    We store a hash (not the raw token) in the DB.
    On logout, the row for this hash is left in place and the token is then
    inserted (it's already there) or we insert a new record with is_active=False.

    Actually — since our blocklist only stores BLOCKED tokens, store_refresh_token
    is a no-op in the current design. The token is valid until it appears in the
    blocklist. This is the simplest correct approach.

    Note: kept as an async function for API compatibility with routers.
    """
    # No-op: blocklist-only design means we only write on logout.
    # The token is implicitly valid until blocklisted.
    pass


async def is_token_blocklisted(db: AsyncSession, token: str) -> bool:
    """
    Return True if the token hash is in the blocklist (D-04, T-02-04).
    Always check this before issuing a new access token on /auth/refresh.
    """
    from app.models.refresh_token_blocklist import RefreshTokenBlocklist

    token_hash = _hash_token(token)
    result = await db.execute(
        select(RefreshTokenBlocklist).where(
            RefreshTokenBlocklist.token_hash == token_hash
        )
    )
    return result.scalar_one_or_none() is not None


async def insert_into_blocklist(db: AsyncSession, token: str) -> None:
    """
    Invalidate a refresh token by inserting its SHA-256 hash into the blocklist.
    Called by /auth/logout (D-04, AUTH-04, Pitfall 3).

    If the hash already exists (duplicate logout call), we silently ignore the
    IntegrityError — idempotent operation.
    """
    from app.models.refresh_token_blocklist import RefreshTokenBlocklist
    from sqlalchemy.exc import IntegrityError

    token_hash = _hash_token(token)

    # Check if already blocklisted (idempotent)
    existing = await db.execute(
        select(RefreshTokenBlocklist).where(
            RefreshTokenBlocklist.token_hash == token_hash
        )
    )
    if existing.scalar_one_or_none() is not None:
        return  # Already blocklisted — no-op

    # Parse expiry from token for record-keeping (best effort)
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=[ALGORITHM],
        )
        exp_ts = payload.get("exp", None)
        expires_at = (
            datetime.fromtimestamp(exp_ts, tz=timezone.utc)
            if exp_ts
            else datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        )
    except Exception:
        expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    entry = RefreshTokenBlocklist(
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(entry)
    await db.commit()


# ---------------------------------------------------------------------------
# User authentication
# ---------------------------------------------------------------------------

async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> Optional[User]:
    """
    Verify email + password. Returns the User on success, None on failure.

    Timing-attack mitigation (T-02-06, RESEARCH.md Security Domain):
      If the email does not exist, we still verify the supplied password against
      DUMMY_HASH before returning None. This ensures the response time is the
      same regardless of whether the email exists — an attacker cannot
      enumerate valid emails by measuring response latency.
    """
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Constant-time dummy verify — prevents timing oracle on email existence
        password_hash.verify(password, DUMMY_HASH)
        return None

    if not password_hash.verify(password, user.hashed_password):
        return None

    return user


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hash_token(token: str) -> str:
    """SHA-256 hex digest of the token string — used as the DB key."""
    return hashlib.sha256(token.encode()).hexdigest()
