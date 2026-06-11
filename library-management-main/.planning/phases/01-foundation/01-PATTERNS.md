# Phase 1: Foundation - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 22 (new files — greenfield project)
**Analogs found:** 0 / 22 — codebase is a blank slate (only CLAUDE.md exists)

> **Greenfield note:** No analog files exist in the repository. All patterns below are sourced directly from RESEARCH.md code examples and official documentation references. The planner MUST use these patterns as the authoritative source of truth for all implementation tasks.

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `backend/app/main.py` | config | request-response | none | no analog |
| `backend/app/config.py` | config | — | none | no analog |
| `backend/app/database.py` | utility | request-response | none | no analog |
| `backend/app/models/user.py` | model | CRUD | none | no analog |
| `backend/app/models/book.py` | model | CRUD | none | no analog |
| `backend/app/models/borrow_request.py` | model | CRUD | none | no analog |
| `backend/app/models/loan.py` | model | CRUD | none | no analog |
| `backend/app/schemas/auth.py` | utility | request-response | none | no analog |
| `backend/app/schemas/user.py` | utility | request-response | none | no analog |
| `backend/app/routers/auth.py` | controller | request-response | none | no analog |
| `backend/app/routers/admin.py` | controller | request-response | none | no analog |
| `backend/app/services/auth_service.py` | service | request-response | none | no analog |
| `backend/app/dependencies/auth.py` | middleware | request-response | none | no analog |
| `backend/alembic/env.py` | config | batch | none | no analog |
| `backend/alembic/versions/001_initial_schema.py` | migration | batch | none | no analog |
| `backend/tests/conftest.py` | test | request-response | none | no analog |
| `backend/tests/test_auth.py` | test | request-response | none | no analog |
| `backend/tests/test_admin.py` | test | request-response | none | no analog |
| `frontend/src/context/AuthContext.tsx` | provider | event-driven | none | no analog |
| `frontend/src/lib/axios.ts` | utility | request-response | none | no analog |
| `frontend/src/components/ProtectedRoute.tsx` | component | request-response | none | no analog |
| `compose.yml` | config | — | none | no analog |

---

## Pattern Assignments

### `backend/app/database.py` (utility, request-response)

**Source:** RESEARCH.md — Pattern 1: SQLAlchemy 2.0 Async Session Dependency

**Full pattern:**
```python
# backend/app/database.py

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator, Annotated
from fastapi import Depends
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,  # "postgresql+asyncpg://user:pass@host:5432/db"
    echo=settings.DEBUG,
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

DbSession = Annotated[AsyncSession, Depends(get_db)]
```

**Critical constraint:** Never create a module-level shared `AsyncSession`. Always use `async_sessionmaker` with `async with` context manager per request. Sharing sessions across requests causes state corruption (RESEARCH.md Pitfall: module-level AsyncSession).

---

### `backend/app/config.py` (config)

**Source:** RESEARCH.md Standard Stack + CLAUDE.md constraints

**Pattern:**
```python
# backend/app/config.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    class Config:
        env_file = ".env"

settings = Settings()
```

---

### `backend/app/main.py` (config, request-response)

**Source:** RESEARCH.md Pitfall 4 (CORS) + CLAUDE.md constraint

**CORS pattern — critical:**
```python
# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, admin

app = FastAPI()

# CRITICAL: Never use allow_origins=["*"] with allow_credentials=True.
# Browsers block credentialed requests to wildcard origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # explicit origin list only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
```

---

### `backend/app/models/user.py` (model, CRUD)

**Source:** RESEARCH.md Code Examples — Complete SQLAlchemy Model Skeleton

**Full pattern:**
```python
# backend/app/models/user.py
# SQLAlchemy 2.0 Mapped types pattern

from sqlalchemy import String, CheckConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    # D-03: full_name required for Phase 4 loan search by student name
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # D-discretion: VARCHAR CHECK (not native ENUM) per CONTEXT.md
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student")
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    __table_args__ = (
        CheckConstraint("role IN ('student','librarian','admin_librarian')", name="ck_users_role"),
    )
```

**Password column name:** Use `hashed_password` (FastAPI docs convention per CONTEXT.md discretion).

---

### `backend/app/models/book.py` (model, CRUD)

**Source:** RESEARCH.md D-07 indexes + CONTEXT.md specifics (available_copies constraints)

**Pattern:**
```python
# backend/app/models/book.py

from sqlalchemy import String, Integer, CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.user import Base

class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    isbn: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    total_copies: Mapped[int] = mapped_column(Integer, nullable=False)
    # CONTEXT.md specifics: CP-1 correctness constraints
    available_copies: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("available_copies >= 0", name="ck_books_available_nonnegative"),
        CheckConstraint("available_copies <= total_copies", name="ck_books_available_lte_total"),
        # D-07: GIN full-text index for catalog search (CAT-05)
        # Note: GIN index created in Alembic migration, not via SQLAlchemy model
    )
```

---

### `backend/app/models/borrow_request.py` (model, CRUD)

**Source:** RESEARCH.md D-05 (VARCHAR CHECK for status)

**Pattern:**
```python
# backend/app/models/borrow_request.py

from sqlalchemy import String, Integer, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime
from app.models.user import Base

class BorrowRequest(Base):
    __tablename__ = "borrow_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    # D-05: VARCHAR CHECK instead of PostgreSQL ENUM (easier to extend)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    requested_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('pending','approved','rejected')", name="ck_borrow_requests_status"),
    )
```

---

### `backend/app/models/loan.py` (model, CRUD)

**Source:** RESEARCH.md D-06 (overdue_notified_at) + D-05 (VARCHAR CHECK)

**Pattern:**
```python
# backend/app/models/loan.py

from sqlalchemy import String, Integer, ForeignKey, CheckConstraint, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
import datetime
from app.models.user import Base

class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    borrow_request_id: Mapped[int] = mapped_column(ForeignKey("borrow_requests.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), nullable=False)
    # D-05: VARCHAR CHECK for status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    loan_date: Mapped[datetime.datetime] = mapped_column(nullable=False)
    # Fixed 14-day borrow period (CLAUDE.md constraint)
    due_date: Mapped[datetime.datetime] = mapped_column(nullable=False)
    returned_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    # D-06: NULL = not notified; timestamp = overdue email sent (idempotent)
    overdue_notified_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('active','returned','overdue')", name="ck_loans_status"),
    )
```

---

### `backend/app/services/auth_service.py` (service, request-response)

**Source:** RESEARCH.md — Pattern 2: JWT Token Pair (Access + Refresh)

**Full pattern:**
```python
# backend/app/services/auth_service.py

import jwt
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
ALGORITHM = "HS256"

def create_access_token(user_id: int, role: str, secret: str) -> str:
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)

def create_refresh_token(user_id: int, secret: str) -> str:
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)
```

**Critical:** Use `PyJWT` only — NOT `python-jose` (has unresolved CVEs). Always specify `algorithms=["HS256"]` in `jwt.decode()` — never `algorithms=None` (JWT algorithm confusion attack).

---

### `backend/app/dependencies/auth.py` (middleware, request-response)

**Source:** RESEARCH.md — Pattern 3: FastAPI require_role Dependency

**Full pattern:**
```python
# backend/app/dependencies/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
from typing import Annotated
from app.database import DbSession
from app.models.user import User
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload["sub"])
        role = payload["role"]
    except (InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(*roles: str):
    """Factory that returns a dependency enforcing role membership."""
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
```

**Apply to:** Every protected endpoint in `routers/auth.py` and `routers/admin.py`. This dependency is the backend authority — frontend routing is UX-only (CM-7).

---

### `backend/app/routers/auth.py` (controller, request-response)

**Source:** RESEARCH.md — Pattern 2 login endpoint + pitfall 3 (logout blocklist) + pitfall 5 (withCredentials)

**Login endpoint pattern:**
```python
# backend/app/routers/auth.py

from fastapi import APIRouter, Response, HTTPException, Cookie
from app.database import DbSession
from app.services.auth_service import create_access_token, create_refresh_token, password_hash
from app.schemas.auth import RegisterRequest, LoginRequest
from app.config import settings

router = APIRouter()

@router.post("/login")
async def login(form_data: LoginRequest, response: Response, db: DbSession):
    user = await authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.id, user.role, settings.SECRET_KEY)
    refresh_token = create_refresh_token(user.id, settings.SECRET_KEY)

    await store_refresh_token(db, user.id, refresh_token)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 7 days
        path="/auth/refresh",  # scope cookie to refresh endpoint only
    )

    return {"access_token": access_token, "token_type": "bearer", "user": UserOut.model_validate(user)}

@router.post("/logout")
async def logout(response: Response, db: DbSession, refresh_token: str = Cookie(None)):
    # D-04: server-side invalidation required (pitfall 3)
    if refresh_token:
        await insert_into_blocklist(db, refresh_token)
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}
```

**Timing-attack protection for email lookup:**
```python
# RESEARCH.md Security Domain — timing attack mitigation
DUMMY_HASH = password_hash.hash("dummy")

async def authenticate_user(db, email: str, password: str):
    user = await get_user_by_email(db, email)
    if not user:
        # Verify against dummy hash to prevent timing oracle on email existence
        password_hash.verify(password, DUMMY_HASH)
        return None
    if not password_hash.verify(password, user.hashed_password):
        return None
    return user
```

---

### `backend/app/routers/admin.py` (controller, request-response)

**Source:** RESEARCH.md — Pattern 3 require_role usage example

**Pattern:**
```python
# backend/app/routers/admin.py

from fastapi import APIRouter, Depends
from typing import Annotated
from app.dependencies.auth import require_role
from app.database import DbSession
from app.schemas.user import CreateLibrarianRequest, UserOut
from app.models.user import User

router = APIRouter()

@router.post("/users", response_model=UserOut)
async def create_librarian(
    data: CreateLibrarianRequest,
    current_user: Annotated[User, Depends(require_role("admin_librarian"))],
    db: DbSession,
):
    # AUTH-06: Admin librarian creates librarian accounts
    ...
```

---

### `backend/alembic/env.py` (config, batch)

**Source:** RESEARCH.md — Pattern 4: Alembic Async env.py

**Full pattern — critical (pitfall 1 + pitfall 2):**
```python
# backend/alembic/env.py
# CRITICAL: Use async template — default sync env.py hangs with asyncpg

import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from alembic import context

# CRITICAL: Import ALL models or Base.metadata will be empty → empty migration (pitfall 2)
from app.models.user import User, Base
from app.models.book import Book
from app.models.borrow_request import BorrowRequest
from app.models.loan import Loan

config = context.config
target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Required for migration context
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())

run_migrations_online()
```

**Initialize with:** `alembic init -t async alembic` (not default `alembic init alembic`).

---

### `backend/alembic/versions/001_initial_schema.py` (migration, batch)

**Source:** RESEARCH.md — Pattern 6: Complete Schema Migration structure + D-01 through D-10

**Table creation order (FK dependency order):**
```python
# backend/alembic/versions/001_initial_schema.py
# D-02: Single migration, all 5 phases tables

import os
from alembic import op
import sqlalchemy as sa
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()

def upgrade():
    # 1. users (no FKs)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),  # FastAPI docs convention
        sa.Column("full_name", sa.String(255), nullable=False),  # D-03
        sa.Column("role", sa.String(20), nullable=False, server_default="student"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("role IN ('student','librarian','admin_librarian')", name="ck_users_role"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)  # D-07

    # 2. refresh_token_blocklist (no FKs) — D-04
    op.create_table(
        "refresh_token_blocklist",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # 3. books (no FKs)
    op.create_table(
        "books",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("isbn", sa.String(20), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("total_copies", sa.Integer, nullable=False),
        sa.Column("available_copies", sa.Integer, nullable=False),  # CP-1
        sa.CheckConstraint("available_copies >= 0", name="ck_books_available_nonnegative"),
        sa.CheckConstraint("available_copies <= total_copies", name="ck_books_available_lte_total"),
    )
    op.create_index("ix_books_isbn", "books", ["isbn"], unique=True)  # D-07
    # D-07: GIN full-text index for catalog search (CAT-05)
    op.execute("CREATE INDEX ix_books_fulltext ON books USING gin(to_tsvector('english', title || ' ' || author))")

    # 4. borrow_requests (FK -> users, FK -> books)
    op.create_table(
        "borrow_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("book_id", sa.Integer, sa.ForeignKey("books.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),  # D-05
        sa.Column("requested_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.CheckConstraint("status IN ('pending','approved','rejected')", name="ck_borrow_requests_status"),
    )
    op.create_index("ix_borrow_requests_status", "borrow_requests", ["status"])  # D-07

    # 5. loans (FK -> borrow_requests, FK -> users, FK -> books)
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("borrow_request_id", sa.Integer, sa.ForeignKey("borrow_requests.id"), nullable=False),
        sa.Column("student_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("book_id", sa.Integer, sa.ForeignKey("books.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),  # D-05
        sa.Column("loan_date", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("due_date", sa.TIMESTAMP(timezone=True), nullable=False),  # 14 days fixed
        sa.Column("returned_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("overdue_notified_at", sa.TIMESTAMP(timezone=True), nullable=True),  # D-06
        sa.CheckConstraint("status IN ('active','returned','overdue')", name="ck_loans_status"),
    )
    op.create_index("ix_loans_due_date", "loans", ["due_date"])  # D-07

    # D-10: Admin librarian seed from environment variables
    op.execute(
        sa.text(
            "INSERT INTO users (email, hashed_password, full_name, role) "
            "VALUES (:email, :hash, :name, 'admin_librarian')"
        ),
        {
            "email": os.environ["ADMIN_EMAIL"],
            "hash": password_hash.hash(os.environ["ADMIN_PASSWORD"]),
            "name": "System Admin",
        }
    )

def downgrade():
    op.drop_table("loans")
    op.drop_table("borrow_requests")
    op.drop_table("books")
    op.drop_table("refresh_token_blocklist")
    op.drop_table("users")
```

---

### `frontend/src/context/AuthContext.tsx` (provider, event-driven)

**Source:** RESEARCH.md — Pattern 5: React AuthContext + Axios Interceptor

**Full pattern:**
```typescript
// frontend/src/context/AuthContext.tsx
// D-08: in-memory access token (not localStorage — XSS risk)
// D-discretion: React Context preferred over module-level variable for testability

import React, { createContext, useContext, useState, useCallback } from "react";

interface AuthState {
  accessToken: string | null;
  user: { id: number; role: string; email: string; full_name: string } | null;
}

interface AuthContextType extends AuthState {
  setAuth: (token: string, user: AuthState["user"]) => void;
  clearAuth: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuthState] = useState<AuthState>({ accessToken: null, user: null });

  const setAuth = useCallback((token: string, user: AuthState["user"]) => {
    setAuthState({ accessToken: token, user });
  }, []);

  const clearAuth = useCallback(() => {
    setAuthState({ accessToken: null, user: null });
  }, []);

  return (
    <AuthContext.Provider value={{ ...auth, setAuth, clearAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
};
```

---

### `frontend/src/lib/axios.ts` (utility, request-response)

**Source:** RESEARCH.md — Pattern 5: Axios instance with interceptors

**Full pattern — critical (pitfall 4 + pitfall 5):**
```typescript
// frontend/src/lib/axios.ts
// CRITICAL: withCredentials: true — sends httpOnly refresh cookie
// CRITICAL: Do NOT use allow_origins=["*"] on backend when withCredentials is set

import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  withCredentials: true,  // CRITICAL: sends httpOnly refresh cookie
});

// Module-level ref avoids stale closure in interceptors
// (AuthContext setAuth also calls setAccessToken to keep in sync)
let accessToken: string | null = null;
export const setAccessToken = (t: string | null) => { accessToken = t; };

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers["Authorization"] = `Bearer ${accessToken}`;
  }
  return config;
});

let isRefreshing = false;
let failedQueue: Array<{ resolve: (v: string) => void; reject: (e: unknown) => void }> = [];

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        }).then((token) => {
          originalRequest.headers["Authorization"] = `Bearer ${token}`;
          return api(originalRequest);
        });
      }
      isRefreshing = true;
      try {
        // CRITICAL: use same api instance (withCredentials) for refresh (pitfall 5)
        const { data } = await api.post("/auth/refresh");
        setAccessToken(data.access_token);
        failedQueue.forEach(({ resolve }) => resolve(data.access_token));
        failedQueue = [];
        return api(originalRequest);
      } catch (e) {
        failedQueue.forEach(({ reject }) => reject(e));
        failedQueue = [];
        setAccessToken(null);
        window.location.href = "/login";
        return Promise.reject(e);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);
```

---

### `frontend/src/components/ProtectedRoute.tsx` (component, request-response)

**Source:** RESEARCH.md Code Examples — ProtectedRoute component

**Full pattern:**
```typescript
// frontend/src/components/ProtectedRoute.tsx
// UX convenience only — backend require_role is the authority (CM-7)

import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

interface ProtectedRouteProps {
  allowedRoles?: string[];
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { accessToken, user } = useAuth();

  if (!accessToken) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <Outlet />;
}
```

---

### `backend/tests/conftest.py` (test)

**Source:** RESEARCH.md Validation Architecture — Wave 0 gaps + pytest-asyncio pattern

**Pattern:**
```python
# backend/tests/conftest.py

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.database import get_db
from app.models.user import Base

TEST_DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test_db"

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
```

**pytest.ini required:**
```ini
# backend/pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

---

### `compose.yml` (config)

**Source:** RESEARCH.md Code Examples — Docker Compose healthcheck pattern

**Full pattern — critical (pitfall 6):**
```yaml
# compose.yml
# CRITICAL: depends_on with service_healthy prevents Alembic race condition (pitfall 6)

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    depends_on:
      db:
        condition: service_healthy  # CRITICAL: waits for DB ready, not just container start
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      SECRET_KEY: ${SECRET_KEY}
      ADMIN_EMAIL: ${ADMIN_EMAIL}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
      ENVIRONMENT: development
    ports:
      - "8000:8000"
    command: >
      sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
    environment:
      VITE_API_URL: http://localhost:8000

  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025"   # SMTP
      - "8025:8025"   # Web UI

volumes:
  postgres_data:
```

---

## Shared Patterns

### Authentication Dependency
**Source:** RESEARCH.md Pattern 3 (`backend/app/dependencies/auth.py`)
**Apply to:** ALL controller endpoints except `/auth/register` and `/auth/login`

```python
from app.dependencies.auth import require_role, get_current_user
from typing import Annotated

# For role-specific endpoints:
current_user: Annotated[User, Depends(require_role("admin_librarian"))]

# For any authenticated user:
current_user: Annotated[User, Depends(get_current_user)]
```

### Error Handling
**Source:** RESEARCH.md Pattern 3 + FastAPI HTTPException pattern
**Apply to:** All router handlers

```python
from fastapi import HTTPException, status

# 401 — authentication failure
raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

# 403 — authorization failure (role mismatch — handled inside require_role)
raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")

# 409 — conflict (duplicate email on register)
raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
```

### Pydantic v2 Schema Pattern
**Source:** RESEARCH.md Standard Stack (Pydantic v2 required by FastAPI 0.100+)
**Apply to:** All schema files in `backend/app/schemas/`

```python
from pydantic import BaseModel, EmailStr

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}  # Pydantic v2 ORM mode
```

### Async Route Handler Pattern
**Source:** RESEARCH.md Pattern 1 — async def + DbSession
**Apply to:** All route handlers that touch the database

```python
# Every DB-touching route handler must be async def
# Every DB operation must use await
@router.post("/register")
async def register(data: RegisterRequest, db: DbSession) -> UserOut:
    result = await db.execute(select(User).where(User.email == data.email))
    ...
    await db.commit()
```

---

## No Analog Found

All 22 files have no existing analog — this is a greenfield project. The patterns above from RESEARCH.md are the authoritative source for all implementations.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| All 22 files listed in classification | various | various | Blank slate — only CLAUDE.md exists in repo |

---

## Critical Anti-Patterns (DO NOT implement)

These are explicitly called out in RESEARCH.md and CLAUDE.md:

| Anti-Pattern | Why Forbidden | Correct Alternative |
|--------------|---------------|---------------------|
| `python-jose` for JWT | Unresolved CVEs | `PyJWT` only |
| `passlib` for password hashing | Unmaintained since 2023 | `pwdlib[argon2]` |
| `JWT in localStorage` | XSS-vulnerable | React Context (access) + httpOnly cookie (refresh) |
| `allow_origins=["*"]` with credentials | Browser blocks credentialed requests | Explicit origin list |
| `Session` (sync) in `async def` routes | Blocks event loop | `AsyncSession` with `await` |
| Module-level shared `AsyncSession` | State corruption across requests | `async_sessionmaker` per request |
| `alembic init alembic` (sync template) | Hangs with asyncpg | `alembic init -t async alembic` |
| Missing model imports in `env.py` | Empty migration generated | Import all models before `target_metadata` |
| PostgreSQL ENUM for status fields | Requires ALTER TYPE to extend | VARCHAR + CHECK constraints (D-05) |
| Frontend-only role check | Backend never enforced | `require_role` dependency on every protected endpoint |

---

## Metadata

**Analog search scope:** Entire repository (`//wsl.localhost/Ubuntu/home/laode/projects/library-management/`)
**Files scanned:** 1 (only CLAUDE.md exists)
**Greenfield:** Yes — Phase 1 establishes all foundational patterns
**Pattern sources:** RESEARCH.md (primary), CLAUDE.md (constraints), CONTEXT.md (decisions D-01 through D-10)
**Pattern extraction date:** 2026-06-11
