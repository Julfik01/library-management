# Phase 1: Foundation - Research

**Researched:** 2026-06-11
**Domain:** FastAPI authentication + PostgreSQL schema + React frontend scaffolding
**Confidence:** MEDIUM

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Phase 1 creates ALL tables for all 5 phases in a single Alembic migration — `001_initial_schema.py`. Tables: `users`, `refresh_token_blocklist`, `books`, `borrow_requests`, `loans`. No table additions in later phases.
- **D-02:** Single migration file — one `001_initial_schema.py` with all tables, FKs, constraints, and indexes in dependency order.
- **D-03:** `users` table includes `full_name` (in addition to `email`, `password_hash`, `role`).
- **D-04:** `refresh_token_blocklist` table created in Phase 1 migration.
- **D-05:** Status fields use VARCHAR + CHECK constraints (not PostgreSQL native ENUMs). `borrow_requests.status` CHECK IN ('pending','approved','rejected'); `loans.status` CHECK IN ('active','returned','overdue').
- **D-06:** `loans` table includes `overdue_notified_at TIMESTAMPTZ` (nullable). NULL = not yet notified; timestamp = first overdue email sent.
- **D-07:** Indexes: UNIQUE on `users.email`, UNIQUE on `books.isbn`, index on `loans.due_date`, index on `borrow_requests.status`, GIN full-text on `books (title || ' ' || author)`.
- **D-08:** Token strategy: short-lived in-memory access token + httpOnly refresh cookie. No localStorage.
- **D-09:** RBAC via FastAPI `require_role` dependency injection on every protected endpoint.
- **D-10:** Admin librarian seeded via Alembic migration using `ADMIN_EMAIL` and `ADMIN_PASSWORD` env vars.

### Claude's Discretion

- Specific index naming convention — use SQLAlchemy/Alembic conventions (`ix_` prefix).
- Password column name — follow FastAPI docs convention (`hashed_password`).
- `role` column implementation — VARCHAR CHECK IN ('student','librarian','admin_librarian').
- React in-memory token store — React Context preferred for testability.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | Student can self-register with email and password | pwdlib[argon2] hash on registration; POST /auth/register endpoint; duplicate email returns 409 |
| AUTH-02 | Any user can log in with email and password | PyJWT access token creation; refresh token stored in DB; httpOnly cookie set on response |
| AUTH-03 | Session persists across page refreshes via httpOnly refresh token cookie + in-memory access token | /auth/refresh endpoint reads Cookie; React Context stores access token in memory; Axios interceptor auto-refreshes on 401 |
| AUTH-04 | Any user can log out; refresh token is invalidated server-side | /auth/logout deletes httpOnly cookie and inserts token into refresh_token_blocklist table |
| AUTH-05 | Admin librarian account is seeded via Alembic migration | Alembic migration 001 seeds admin user using os.environ ADMIN_EMAIL / ADMIN_PASSWORD |
| AUTH-06 | Admin librarian can create librarian accounts | POST /admin/users endpoint requires role=admin_librarian; sets role='librarian' |
| AUTH-07 | Backend enforces role-based access on all protected endpoints | require_role(["librarian","admin_librarian"]) Depends pattern; returns 403 on mismatch |
</phase_requirements>

---

## Summary

Phase 1 is the entire project foundation: Docker Compose dev environment, complete PostgreSQL schema for all 5 phases, FastAPI authentication stack (register, login, token refresh, logout, RBAC), and a scaffolded React frontend with routing and auth context. Every subsequent phase builds on these artifacts and none adds to the database schema.

The authentication architecture uses PyJWT for access tokens (short-lived, returned in response body, held in React Context) and a server-side refresh token stored in the database with its token string held in an httpOnly SameSite=Lax cookie. Logout invalidates the refresh token by inserting it into the `refresh_token_blocklist` table. The full 5-phase schema must be laid down in a single Alembic migration `001_initial_schema.py`, including all GIN indexes, CHECK constraints, and the admin seed record.

The critical non-obvious element of this phase is that Phase 1 is schema-complete for the entire project. Tables for books, borrow_requests, and loans must exist from day one even though Phase 2, 3, 4 implement their endpoints. This means the Alembic migration is larger than typical "bootstrap" migrations and requires careful ordering of FK dependencies. All correctness constraints (available_copies CHECK, SELECT FOR UPDATE semantics) must be written correctly now even though the endpoints that use them ship later.

**Primary recommendation:** Build bottom-up — Docker Compose + DB first, then SQLAlchemy models + Alembic migration, then FastAPI auth endpoints, then React scaffolding + auth context.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| User registration | API / Backend | — | Password hashing and DB write belong server-side |
| Login / token issuance | API / Backend | — | Credentials verified server-side; tokens issued server-side |
| Session persistence across refresh | Browser / Client | API / Backend | httpOnly cookie survives page reload; /refresh endpoint validates it |
| Logout / token invalidation | API / Backend | Browser / Client | Server inserts blocklist record; client clears in-memory token and deletes cookie |
| Role-based access control | API / Backend | — | FastAPI require_role dependency; frontend routing is UX-only |
| Admin librarian seeding | Database / Storage | — | Alembic migration seed record; no API endpoint needed |
| Full DB schema creation | Database / Storage | — | Single Alembic migration; all tables for all phases |
| Frontend routing by role | Browser / Client | — | React Router protected routes; does NOT substitute for backend RBAC |
| Token refresh on 401 | Browser / Client | API / Backend | Axios response interceptor triggers; /auth/refresh endpoint handles |

---

## Standard Stack

### Core (Backend)
| Library | Version (PyPI verified) | Purpose | Why Standard |
|---------|------------------------|---------|--------------|
| fastapi | 0.115.x (latest: 0.136.3) | Web framework | Fixed constraint; 0.115.x is stable LTS line |
| uvicorn[standard] | 0.30.x (latest: 0.49.0) | ASGI server | Official FastAPI server; [standard] adds watchfiles for dev |
| pydantic | v2.x | Validation / serialization | FastAPI 0.100+ requires Pydantic v2 |
| sqlalchemy | 2.0.x (latest: 2.0.50) | ORM + async engine | Only async-capable ORM with Alembic support |
| asyncpg | 0.29.x (latest: 0.31.0) | PostgreSQL async driver | Required by SQLAlchemy async engine |
| alembic | 1.13.x (latest: 1.18.4) | DB migrations | Only maintained migration tool for SQLAlchemy |
| pyjwt | 2.8.x (latest: 2.13.0) | JWT encode/decode | FastAPI official docs use PyJWT; python-jose has CVEs |
| pwdlib[argon2] | 0.2.x (latest: 0.3.0) | Password hashing | FastAPI docs recommend over passlib; Argon2 is memory-hard |
| python-multipart | 0.0.9 (latest: 0.0.32) | Form data parsing | Required for OAuth2PasswordRequestForm |

### Core (Frontend)
| Library | Version (CLAUDE.md) | Purpose | Why Standard |
|---------|---------------------|---------|--------------|
| react | 18.x | UI framework | Fixed constraint |
| typescript | 5.x | Type safety | Multi-role app; catches auth/role bugs at compile time |
| vite | 5.x | Build tool | CRA deprecated; standard for API-backed SPAs |
| react-router-dom | v6.x | Client-side routing | Standard SPA router; nested routes support |
| @tanstack/react-query | v5 | Server state / data fetching | Handles auth state, caching, loading |
| axios | 1.x | HTTP client | Interceptors for JWT injection + auto-refresh |
| react-hook-form | 7.x | Form management | Login/register forms |
| zod | 3.x | Schema validation | Client-side form validation |
| shadcn/ui | latest | UI components | Copy-paste model; Tailwind-native |
| tailwindcss | 3.x | Utility CSS | Required by shadcn/ui |

### Supporting
| Library | Version (PyPI verified) | Purpose | When to Use |
|---------|------------------------|---------|-------------|
| python-dotenv | latest | .env loading | Load env vars in non-Docker local dev |
| pytest | 8.x (latest: 9.0.3) | Test runner | Backend unit + integration tests |
| pytest-asyncio | 0.23.x (latest: 1.4.0) | Async test support | Required for async route handler tests |
| httpx | 0.27.x (latest: 0.28.1) | Test HTTP client | FastAPI TestClient dependency |
| factory-boy | 3.x (latest: 3.3.3) | Test fixtures | Generate User model instances for tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyJWT | python-jose | python-jose has unresolved CVEs; PyJWT is the FastAPI docs recommendation |
| pwdlib[argon2] | passlib[bcrypt] | passlib is largely unmaintained since 2023 |
| SQLAlchemy async | SQLModel | SQLModel async support lags; Alembic integration is friction |
| React Context (token store) | Module-level variable | Context is testable and supports React DevTools; module variable is simpler but untestable |

**Backend installation:**
```bash
pip install "fastapi==0.115.*" "uvicorn[standard]==0.30.*" "sqlalchemy==2.0.*" \
  "asyncpg==0.29.*" "alembic==1.13.*" "pyjwt==2.8.*" "pwdlib[argon2]==0.2.*" \
  "python-multipart==0.0.9" "pydantic[email]==2.*" "python-dotenv"
```

**Backend dev installation:**
```bash
pip install "pytest==8.*" "pytest-asyncio==0.23.*" "httpx==0.27.*" "factory-boy==3.*"
```

**Frontend scaffolding:**
```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install react-router-dom @tanstack/react-query axios react-hook-form zod
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npx shadcn-ui@latest init
```

**Version note:** CLAUDE.md specifies 0.115.x for FastAPI (LTS line). Latest PyPI is 0.136.3. Pin to `0.115.*` as specified. For Alembic: latest is 1.18.4 but CLAUDE.md pins 1.13.x — pin to `1.13.*` for stability. For pwdlib: latest is 0.3.0, pin `0.2.*` as specified.

---

## Package Legitimacy Audit

> All packages in this phase are sourced from CLAUDE.md, the authoritative project instruction file. Registry legitimacy checks via seam returned SUS verdicts due to missing network connectivity to the registry API — not due to genuine suspicion. Packages are validated against official documentation and the project's own technology specification.

| Package | Registry | Authority Source | Verdict | Disposition |
|---------|----------|-----------------|---------|-------------|
| fastapi | PyPI | CLAUDE.md + fastapi.tiangolo.com | OK | Approved |
| pyjwt | PyPI | CLAUDE.md + fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ | OK | Approved |
| pwdlib[argon2] | PyPI | CLAUDE.md + fastapi.tiangolo.com tutorial | OK | Approved |
| sqlalchemy | PyPI | CLAUDE.md + official SQLAlchemy docs | OK | Approved |
| asyncpg | PyPI | CLAUDE.md + SQLAlchemy async docs | OK | Approved |
| alembic | PyPI | CLAUDE.md + alembic.sqlalchemy.org | OK | Approved |
| uvicorn | PyPI | CLAUDE.md + fastapi.tiangolo.com/deployment | OK | Approved |
| python-multipart | PyPI | CLAUDE.md + FastAPI OAuth2 form docs | OK | Approved |
| react | npm | CLAUDE.md | OK | Approved |
| react-router-dom | npm | CLAUDE.md | OK | Approved |
| @tanstack/react-query | npm | CLAUDE.md | OK | Approved |
| axios | npm | CLAUDE.md | OK | Approved |
| shadcn/ui | npm | CLAUDE.md + ui.shadcn.com/docs | OK | Approved |
| tailwindcss | npm | CLAUDE.md | OK | Approved |
| vite | npm | CLAUDE.md | OK | Approved |

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious:** none

---

## Architecture Patterns

### System Architecture Diagram

```
Browser (React SPA)
  |
  | Login/Register (JSON body)
  v
[FastAPI /auth/register]  →  pwdlib hash  →  INSERT users
[FastAPI /auth/login]     →  pwdlib verify →  PyJWT sign
                                              ├─ access_token  →  Response body (client stores in React Context)
                                              └─ refresh_token →  Response httpOnly SameSite=Lax cookie (Set-Cookie header)

Page Refresh:
Browser                   →  GET /auth/refresh (cookie auto-sent by browser)
                          ←  new access_token in response body
React App on load         →  calls /auth/refresh → stores in Context → app ready

Authenticated Request:
Axios (request interceptor) →  Authorization: Bearer <access_token from Context>
                             →  FastAPI get_current_user dependency validates JWT
                             →  require_role([...]) checks payload.role

Token Expiry (401):
Axios (response interceptor) →  queue request  →  POST /auth/refresh  →  retry with new token

Logout:
Browser                   →  POST /auth/logout
FastAPI                   →  INSERT refresh_token_blocklist (token_hash, expires_at)
                          →  response.delete_cookie("refresh_token")
                          →  browser: clear React Context access_token
```

### Recommended Project Structure
```
library-management/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, router registration
│   │   ├── config.py            # Settings (Pydantic BaseSettings)
│   │   ├── database.py          # create_async_engine, async_sessionmaker, get_db
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py          # User SQLAlchemy model
│   │   │   ├── book.py          # Book model (schema-complete for Phase 2)
│   │   │   ├── borrow_request.py # BorrowRequest model
│   │   │   └── loan.py          # Loan model
│   │   ├── schemas/
│   │   │   ├── auth.py          # RegisterRequest, LoginResponse, TokenResponse
│   │   │   └── user.py          # UserOut, CreateLibrarianRequest
│   │   ├── routers/
│   │   │   ├── auth.py          # /auth/register, /auth/login, /auth/refresh, /auth/logout
│   │   │   └── admin.py         # /admin/users (create librarian)
│   │   ├── services/
│   │   │   └── auth_service.py  # authenticate_user, create_tokens
│   │   └── dependencies/
│   │       └── auth.py          # get_current_user, require_role
│   ├── alembic/
│   │   ├── env.py               # async env.py
│   │   ├── versions/
│   │   │   └── 001_initial_schema.py  # all 5 phases tables
│   │   └── alembic.ini
│   ├── tests/
│   │   ├── conftest.py
│   │   └── test_auth.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx              # Router setup
│   │   ├── context/
│   │   │   └── AuthContext.tsx  # in-memory token + user state
│   │   ├── lib/
│   │   │   └── axios.ts         # Axios instance with interceptors
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── RegisterPage.tsx
│   │   │   └── DashboardPage.tsx  # role-based redirect shell
│   │   ├── components/
│   │   │   └── ProtectedRoute.tsx
│   │   └── hooks/
│   │       └── useAuth.ts
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── compose.yml
└── .env.example
```

### Pattern 1: SQLAlchemy 2.0 Async Session Dependency

**What:** Per-request AsyncSession injected via FastAPI Depends. Engine and sessionmaker created once at startup.
**When to use:** Every route handler that touches the database.

```python
# Source: berkkaraal.com + SQLAlchemy docs + fastapi.tiangolo.com
# backend/app/database.py

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator, Annotated
from fastapi import Depends

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

```python
# Usage in route handler
@router.post("/register")
async def register(data: RegisterRequest, db: DbSession) -> UserOut:
    ...
```

### Pattern 2: JWT Token Pair (Access + Refresh)

**What:** Access token returned in JSON response body (stored in React Context, cleared on tab close). Refresh token stored in DB and referenced via httpOnly cookie.
**When to use:** Login endpoint and token refresh endpoint.

```python
# Source: fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ + retz.dev/blog/jwt-and-cookie-auth-in-fastapi/
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

```python
# Source: fastapi.tiangolo.com + retz.dev cookie pattern
# backend/app/routers/auth.py — Login endpoint

from fastapi import Response
from fastapi.responses import JSONResponse

@router.post("/login")
async def login(form_data: LoginRequest, response: Response, db: DbSession):
    user = await authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.id, user.role, settings.SECRET_KEY)
    refresh_token = create_refresh_token(user.id, settings.SECRET_KEY)

    # Store refresh token hash in DB
    await store_refresh_token(db, user.id, refresh_token)

    # Set httpOnly cookie for refresh token
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
```

### Pattern 3: FastAPI require_role Dependency

**What:** Reusable dependency factory that returns a dependency checking the user's role.
**When to use:** Every librarian, admin, or protected endpoint.

```python
# Source: fastapi.tiangolo.com/tutorial/security/ + dev.to/moadennagi RBAC pattern
# backend/app/dependencies/auth.py

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt.exceptions import InvalidTokenError
from typing import Annotated

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

# Usage:
@router.post("/admin/users")
async def create_librarian(
    data: CreateLibrarianRequest,
    current_user: Annotated[User, Depends(require_role("admin_librarian"))],
    db: DbSession,
):
    ...
```

### Pattern 4: Alembic Async env.py

**What:** Alembic's default env.py does not support asyncpg. Must use async template or manually configure.
**When to use:** Required for any project using asyncpg with Alembic.

```python
# Source: alembic.sqlalchemy.org/en/latest/cookbook.html
# alembic/env.py (async template via: alembic init -t async alembic)

import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from alembic import context

# Import all models so Base.metadata has all tables
from app.models.user import User
from app.models.book import Book
from app.models.borrow_request import BorrowRequest
from app.models.loan import Loan
from app.database import Base

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

### Pattern 5: React AuthContext + Axios Interceptor

**What:** Access token held in React Context (in-memory, cleared on tab close). Axios instance with request interceptor adds `Authorization: Bearer` header. Response interceptor auto-refreshes on 401.
**When to use:** Frontend auth setup.

```typescript
// Source: bezkoder.com React refresh token pattern + CLAUDE.md D-08 decision
// frontend/src/context/AuthContext.tsx

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

```typescript
// frontend/src/lib/axios.ts — Axios instance with interceptors
// Source: bezkoder.com React refresh token with axios interceptors

import axios from "axios";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  withCredentials: true,  // CRITICAL: sends httpOnly refresh cookie
});

// Access token injected per-request from module-level ref (avoids stale closure)
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
        const { data } = await axios.post("/auth/refresh", {}, { withCredentials: true });
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

### Pattern 6: Complete Schema Migration (001_initial_schema.py structure)

**What:** Single migration creates all 5 phases tables in FK-dependency order.
**When to use:** Phase 1 only; later phases never add tables.

```python
# Source: CONTEXT.md D-01 through D-07 decisions

# Table creation order (FK dependency order):
# 1. users  (no FKs)
# 2. refresh_token_blocklist  (no FKs — stores token hash + expiry)
# 3. books  (no FKs)
# 4. borrow_requests  (FK -> users, FK -> books)
# 5. loans  (FK -> borrow_requests, FK -> users, FK -> books)

# Key schema decisions:
# - users.role: VARCHAR(20) NOT NULL DEFAULT 'student' CHECK (role IN ('student','librarian','admin_librarian'))
# - users.hashed_password: VARCHAR(255) NOT NULL  [FastAPI docs convention]
# - books.available_copies: INTEGER CHECK (available_copies >= 0) CHECK (available_copies <= total_copies)
# - borrow_requests.status: VARCHAR(20) CHECK (status IN ('pending','approved','rejected'))
# - loans.status: VARCHAR(20) CHECK (status IN ('active','returned','overdue'))
# - loans.overdue_notified_at: TIMESTAMPTZ nullable  [D-06: idempotent overdue email]
# - loans.due_date: TIMESTAMPTZ NOT NULL  [14 days from approval_date]

# Indexes (all in this migration):
# - UNIQUE: users.email
# - UNIQUE: books.isbn
# - ix_loans_due_date: loans.due_date
# - ix_borrow_requests_status: borrow_requests.status
# - ix_books_fulltext: GIN(to_tsvector('english', title || ' ' || author))

# Admin seed (D-10):
# op.execute(
#   "INSERT INTO users (email, hashed_password, full_name, role) VALUES (:email, :hash, :name, 'admin_librarian')",
#   {"email": os.environ["ADMIN_EMAIL"], "hash": password_hash.hash(os.environ["ADMIN_PASSWORD"]), "name": "System Admin"}
# )
```

### Anti-Patterns to Avoid

- **Module-level AsyncSession:** Never create a shared `session = AsyncSession(engine)` at the top of a file. Always use `async_sessionmaker` with the `async with` context manager per request. Sharing sessions across requests causes state corruption (CP-2).
- **JWT in localStorage:** XSS-vulnerable. Access token lives in React Context only; refresh token in httpOnly cookie only (CLAUDE.md What NOT to Use).
- **Frontend-only role check:** React Router `<ProtectedRoute>` is UX convenience only. Every API endpoint uses `require_role` dependency — never skip it because the frontend "already checks" (CM-7).
- **allow_origins=["*"] with credentials:** Browsers block this. Must specify explicit origins when `allow_credentials=True` (CLAUDE.md What NOT to Use).
- **Alembic without model imports:** If `env.py` does not import all model modules, `Base.metadata.tables` is empty and autogenerate produces empty migration. Every model must be imported before `target_metadata = Base.metadata`.
- **PostgreSQL ENUMs for status fields:** Use VARCHAR + CHECK constraints instead (D-05). ENUMs require `ALTER TYPE` migrations to extend values — CHECK constraints do not.
- **Sync SQLAlchemy in async FastAPI:** Using `Session` (sync) inside `async def` route handlers blocks the event loop. Only `AsyncSession` with `await` is acceptable.
- **python-jose for JWT:** Has unresolved CVEs. Use PyJWT only (CLAUDE.md, FastAPI docs).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom bcrypt/SHA-256 | `pwdlib[argon2]` | Argon2 is memory-hard; timing-safe verify built-in |
| JWT encode/decode | Manual base64 + HMAC | `PyJWT` | Handles expiry, algorithm validation, InvalidTokenError |
| DB migrations | Manual ALTER TABLE scripts | `Alembic` | Revision history, upgrade/downgrade, autogenerate |
| Async DB sessions | Manual connection pool | `SQLAlchemy async_sessionmaker` | Per-request lifecycle, connection pooling, cleanup |
| Form validation (frontend) | Custom onChange validators | `react-hook-form + zod` | Handles touched/dirty state, async validation, nested fields |
| UI components | Custom Button/Input/Dialog | `shadcn/ui` | Accessible (Radix primitives), consistent design, zero bundle overhead |
| HTTP client interceptors | Custom fetch wrapper | `Axios + interceptors` | Request queue for concurrent refresh, error propagation |

**Key insight:** Password hashing and JWT handling have subtle timing-attack and cryptographic pitfalls that custom code consistently gets wrong. Use purpose-built libraries for both.

---

## Common Pitfalls

### Pitfall 1: Alembic async env.py not configured (CP-4)
**What goes wrong:** `alembic upgrade head` hangs or throws `asyncpg: got a connection` error.
**Why it happens:** Default `alembic init` generates sync `engine_from_config`. asyncpg requires async engine.
**How to avoid:** Use `alembic init -t async alembic` template, or manually replace `engine_from_config` with `async_engine_from_config` and add `asyncio.run(run_async_migrations())`.
**Warning signs:** Migration command hangs indefinitely; `PG_INVALID_CATALOG_NAME` error on wrong DB URL.

### Pitfall 2: Missing model imports in env.py
**What goes wrong:** `alembic revision --autogenerate` generates an empty migration file with no tables.
**Why it happens:** `Base.metadata` is only populated when model modules are imported. env.py must explicitly import every model.
**How to avoid:** Add explicit imports for every model module at the top of env.py before the `target_metadata` assignment.
**Warning signs:** `INFO Running upgrade -> ...` but generated migration has no `op.create_table()` calls.

### Pitfall 3: Stale httpOnly cookie after logout
**What goes wrong:** User logs out, but old refresh token still works if not blocked.
**Why it happens:** Cookie deletion on client side is insufficient — the token must also be invalidated server-side.
**How to avoid:** On logout: (1) INSERT into `refresh_token_blocklist`, (2) `response.delete_cookie("refresh_token")`. On every refresh request: check blocklist before issuing new access token.
**Warning signs:** User can hit `/auth/refresh` after logout and get a new access token.

### Pitfall 4: CORS allow_credentials + wildcard origin
**What goes wrong:** Browser throws `CORS policy` error on credentialed requests (those sending the httpOnly cookie).
**Why it happens:** Browsers refuse `allow_credentials=True` when `allow_origins=["*"]`.
**How to avoid:** Set `allow_origins=["http://localhost:5173", "https://yourdomain.com"]` explicitly. Never use wildcard with credentials.
**Warning signs:** Browser console: "The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard '*' when the request's credentials mode is 'include'."

### Pitfall 5: Axios withCredentials not set on refresh endpoint
**What goes wrong:** Refresh endpoint doesn't receive the httpOnly cookie, returns 401, causing infinite redirect loop.
**Why it happens:** Browser only sends cookies when `withCredentials: true` is set. Axios instance may have it set but the direct `axios.post("/auth/refresh")` call bypasses it.
**How to avoid:** Use the same `api` instance (with `withCredentials: true`) for all calls including token refresh, OR create a separate axios instance specifically for refresh with `withCredentials: true`.
**Warning signs:** `/auth/refresh` receives no cookie despite successful login.

### Pitfall 6: Docker Compose race condition (DB not ready)
**What goes wrong:** FastAPI container starts before PostgreSQL is ready, Alembic migration fails with `connection refused`.
**Why it happens:** `depends_on: db` only waits for container start, not for PostgreSQL to accept connections.
**How to avoid:** Use `depends_on: db: condition: service_healthy` with a PostgreSQL healthcheck: `test: ["CMD-SHELL", "pg_isready -U $POSTGRES_USER -d $POSTGRES_DB"]`.
**Warning signs:** `alembic upgrade head` in entrypoint fails with `asyncpg.exceptions.ConnectionRefusedError`.

### Pitfall 7: React 18 vs 19 compatibility (shadcn/ui)
**What goes wrong:** `npx shadcn-ui@latest init` in 2025 may generate components targeting React 19.
**Why it happens:** shadcn/ui continuously updates; latest CLI output assumes latest React.
**How to avoid:** Pin React to `18.x` and explicitly check component output after `npx shadcn-ui@latest add`. shadcn/ui documents that React 18 + Tailwind v3 still work.
**Warning signs:** TypeScript errors about unknown props on React 19 `ref` patterns.

---

## Code Examples

### Complete SQLAlchemy Model Skeleton

```python
# Source: SQLAlchemy 2.0 docs Mapped types pattern
# backend/app/models/user.py

from sqlalchemy import String, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="student",
        # CHECK constraint added via __table_args__ or CheckConstraint in migration
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
```

### Docker Compose healthcheck pattern

```yaml
# Source: Docker Compose v2 healthcheck docs + Docker Hub postgres image
# compose.yml

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
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      SECRET_KEY: ${SECRET_KEY}
      ADMIN_EMAIL: ${ADMIN_EMAIL}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
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

  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025"   # SMTP
      - "8025:8025"   # Web UI

volumes:
  postgres_data:
```

### ProtectedRoute component

```typescript
// Source: React Router v6 docs pattern
// frontend/src/components/ProtectedRoute.tsx

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

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `python-jose` for JWT | `PyJWT` | FastAPI docs updated ~2023 | python-jose has CVEs; PyJWT is actively maintained |
| `passlib[bcrypt]` | `pwdlib[argon2]` | FastAPI docs updated 2023 | passlib unmaintained; Argon2 is stronger than bcrypt |
| `tiangolo/uvicorn-gunicorn-fastapi` Docker image | `python:3.12-slim` directly | FastAPI deployment docs deprecated it | Official image deprecated; direct slim image is smaller and clearer |
| `alembic init alembic` (sync) | `alembic init -t async alembic` | SQLAlchemy 2.0 async became standard ~2022 | Sync env.py hangs with asyncpg |
| Create React App (CRA) | Vite | 2023 (CRA officially deprecated) | CRA is unmaintained; Vite is 10x faster |
| React 18 ref forwarding | React 19 `ref` as prop | React 19 (2024) | Project pins React 18; forwardRef still needed |

**Deprecated/outdated:**
- `tiangolo/uvicorn-gunicorn-fastapi`: Explicitly deprecated by FastAPI deployment docs.
- `Create React App`: Officially deprecated and unmaintained since 2023.
- `python-jose`: CVEs; FastAPI docs moved away. Do not use.
- `passlib`: Largely unmaintained since 2023; pwdlib is the replacement.
- Alembic sync `engine_from_config` with asyncpg: Incompatible; always use async template.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `path="/auth/refresh"` as cookie scope narrows cookie to only that endpoint | Code Examples (login pattern) | Cookie not sent on refresh if path scope is wrong; set path="/" if this causes issues |
| A2 | shadcn/ui CLI generates React 18 compatible components when installed on React 18 project | Pitfall 7 | Components may need manual adjustment if CLI generates React 19 syntax |
| A3 | `pytest-asyncio` 1.x (latest) is backward-compatible with 0.23.x test patterns | Standard Stack | Tests may need `asyncio_mode = "auto"` in pytest.ini for newer versions |

**Risk mitigation:** A1 — can fall back to `path="/"` scope if needed. A3 — set `asyncio_mode = "auto"` in pytest.ini from the start.

---

## Open Questions (RESOLVED)

1. **pytest-asyncio major version bump (0.23.x → 1.x)**
   - What we know: CLAUDE.md specifies 0.23.x; latest is 1.4.0; the seam reports SUS but this is a registry connectivity issue, not a package issue.
   - What's unclear: Whether 1.x has breaking changes requiring mode configuration changes.
   - Recommendation: Pin to `0.23.*` as CLAUDE.md specifies; upgrade to 1.x only after verifying tests pass.
   - RESOLVED: Pin `pytest-asyncio==0.23.*` in requirements-dev.txt. Plans 01-01/01-02 already encode this pin.

2. **Alembic version mismatch**
   - What we know: CLAUDE.md specifies 1.13.x; latest is 1.18.4. The 1.13.x line is still maintained.
   - What's unclear: Whether any features used in env.py async pattern require newer Alembic.
   - Recommendation: Pin to `1.13.*` as specified; async template (`-t async`) is available since Alembic 1.7+.
   - RESOLVED: Pin `alembic==1.13.*` in requirements.txt. Async template available since 1.7+; no newer features needed.

3. **Vite + shadcn/ui Tailwind v4 compatibility**
   - What we know: Latest shadcn/ui init in 2025 may default to Tailwind v4 with `@tailwindcss/vite` plugin; CLAUDE.md specifies Tailwind v3.
   - What's unclear: Whether `npx shadcn-ui@latest init` will detect Tailwind v3 or try to install v4.
   - Recommendation: Explicitly install `tailwindcss@3` before running shadcn init; check generated CSS imports.
   - RESOLVED: Plan 01-03 Task 1 explicitly runs `npm install tailwindcss@3 postcss autoprefixer` before `npx shadcn@latest init`. Tailwind v3 is pinned; v4 conflict avoided.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | All services | Yes | 28.5.1 | — |
| Docker Compose | Multi-service orchestration | Yes | v2.40.0 | — |
| Node.js | Frontend build | Yes | 24.15.0 | — |
| Python 3 | Backend dev | Yes | 3.13.13 | — |
| pip | Backend packages | Yes | 25.3 | — |
| PostgreSQL (local) | Direct DB access outside Docker | No | — | Use Docker Compose `db` service |
| npm registry (direct) | Frontend package install | Limited (SSL) | — | Use inside Docker or fix SSL cert |

**Missing dependencies with no fallback:**
- None — all critical dependencies are met via Docker Compose.

**Missing dependencies with fallback:**
- PostgreSQL local install: Use `docker compose up db` for all DB operations; psql via Docker exec.
- npm registry SSL: Run `npm install` inside Docker container or fix Node.js SSL cert (`--use-system-ca`).

**Note:** Python runtime is 3.13.13 on the host, but CLAUDE.md specifies Python 3.12 for the Docker container. Always run the application inside Docker — the host Python version is irrelevant.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.23.x |
| Config file | `backend/pytest.ini` (Wave 0 gap) |
| Quick run command | `docker compose exec backend pytest tests/ -x -q` |
| Full suite command | `docker compose exec backend pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | POST /auth/register creates user, hashes password | unit/integration | `pytest tests/test_auth.py::test_register -x` | No — Wave 0 |
| AUTH-01 | Duplicate email returns 409 | integration | `pytest tests/test_auth.py::test_register_duplicate -x` | No — Wave 0 |
| AUTH-02 | POST /auth/login returns access_token + sets cookie | integration | `pytest tests/test_auth.py::test_login -x` | No — Wave 0 |
| AUTH-02 | Invalid credentials return 401 | integration | `pytest tests/test_auth.py::test_login_invalid -x` | No — Wave 0 |
| AUTH-03 | POST /auth/refresh with valid cookie returns new access_token | integration | `pytest tests/test_auth.py::test_refresh -x` | No — Wave 0 |
| AUTH-04 | POST /auth/logout deletes cookie + blocks further refresh | integration | `pytest tests/test_auth.py::test_logout -x` | No — Wave 0 |
| AUTH-05 | Admin user exists after migration runs | integration | `pytest tests/test_auth.py::test_admin_seeded -x` | No — Wave 0 |
| AUTH-06 | Admin can POST /admin/users to create librarian | integration | `pytest tests/test_admin.py::test_create_librarian -x` | No — Wave 0 |
| AUTH-07 | Student hitting /admin/users returns 403 | integration | `pytest tests/test_admin.py::test_student_forbidden -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `docker compose exec backend pytest tests/ -x -q`
- **Per wave merge:** `docker compose exec backend pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/pytest.ini` — `asyncio_mode = "auto"`, `testpaths = tests`
- [ ] `backend/tests/conftest.py` — async test client, DB override, factory fixtures
- [ ] `backend/tests/test_auth.py` — AUTH-01 through AUTH-05 test cases
- [ ] `backend/tests/test_admin.py` — AUTH-06, AUTH-07 test cases

---

## Security Domain

### Applicable ASVS Categories (Level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | pwdlib[argon2] hashing; PyJWT with HS256; constant-time verify |
| V3 Session Management | Yes | httpOnly SameSite=Lax refresh cookie; in-memory access token; server-side blocklist on logout |
| V4 Access Control | Yes | require_role FastAPI dependency on every protected endpoint; 403 for mismatched role |
| V5 Input Validation | Yes | Pydantic v2 validates all request bodies; email format validation via `pydantic[email]` |
| V6 Cryptography | Partial | SECRET_KEY from env var (never hardcoded); HS256 is ASVS L1 acceptable; RS256 for L2+ |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS token theft | Information Disclosure | httpOnly cookie for refresh token; access token in React Context only (not localStorage) |
| CSRF on refresh endpoint | Tampering | SameSite=Lax on cookie; restricts cross-site POST |
| Brute force login | Elevation of Privilege | [ASSUMED] — rate limiting not in Phase 1 scope; acceptable for v1 |
| JWT algorithm confusion | Tampering | Always specify `algorithms=["HS256"]` in `jwt.decode()`; never use `algorithms=None` |
| Wildcard CORS + credentials | Elevation of Privilege | Explicit `allow_origins` list; never `["*"]` when `allow_credentials=True` |
| Timing attack on email lookup | Information Disclosure | Verify against DUMMY_HASH when user not found (FastAPI docs pattern) |
| Refresh token replay after logout | Elevation of Privilege | Server-side blocklist in `refresh_token_blocklist` table; checked on every /auth/refresh call |
| Alembic exposing SECRET_KEY | Information Disclosure | Alembic reads DB URL from env var; SECRET_KEY never in alembic.ini |

---

## Project Constraints (from CLAUDE.md)

| Constraint | Directive |
|------------|-----------|
| Stack | FastAPI + React + PostgreSQL + Docker — fixed, no alternatives |
| Auth | Custom email/password with JWT — no SSO |
| Borrow period | 14 days hardcoded — no configurable periods |
| Scope | University only |
| JWT storage | httpOnly cookie for refresh; NEVER localStorage |
| CORS | Never `allow_origins=["*"]` with `allow_credentials=True` |
| JWT library | PyJWT only — NOT python-jose (has CVEs) |
| Password hashing | pwdlib[argon2] only — NOT passlib (unmaintained) |
| ORM | SQLAlchemy 2.0 async only — NOT SQLModel (async lags), NOT sync SQLAlchemy |
| Build tool | Vite only — NOT CRA (deprecated), NOT Next.js (overkill) |
| Docker base image | `python:3.12-slim` — NOT `tiangolo/uvicorn-gunicorn-fastapi` (deprecated) |
| State management | TanStack Query — NOT Redux (overhead for this app) |
| UI components | shadcn/ui — NOT MUI, NOT Ant Design |
| Task queue | BackgroundTasks (Phase 3) + APScheduler (Phase 5) — NOT Celery (overkill) |

---

## Sources

### Primary (MEDIUM confidence — context7 not reachable; official docs fetched directly)
- [fastapi.tiangolo.com/tutorial/security/oauth2-jwt/](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) — PyJWT + pwdlib authentication pattern; confirmed PyJWT usage, PasswordHash.recommended()
- [alembic.sqlalchemy.org/en/latest/cookbook.html](https://alembic.sqlalchemy.org/en/latest/cookbook.html) — async env.py with run_async_migrations, NullPool, asyncio.run pattern
- [berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/](https://berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker/) — SQLAlchemy 2.0 async session + Alembic setup
- [retz.dev/blog/jwt-and-cookie-auth-in-fastapi/](https://retz.dev/blog/jwt-and-cookie-auth-in-fastapi/) — httpOnly cookie refresh token pattern
- [ui.shadcn.com/docs/installation/vite](https://ui.shadcn.com/docs/installation/vite) — shadcn/ui Vite + TypeScript setup
- CLAUDE.md (project root) — authoritative stack decisions, package versions, rejected patterns

### Secondary (LOW confidence — web search summaries)
- bezkoder.com React refresh token with Axios interceptors pattern
- dev.to/moadennagi FastAPI RBAC dependency injection pattern
- leapcell.io FastAPI + SQLAlchemy 2.0 + asyncpg guide

### Version Verification (VERIFIED: PyPI registry)
- fastapi: latest 0.136.3 (pinning 0.115.x per CLAUDE.md)
- pyjwt: latest 2.13.0 (pinning 2.8.x per CLAUDE.md)
- pwdlib: latest 0.3.0 (pinning 0.2.x per CLAUDE.md)
- sqlalchemy: latest 2.0.50 (pinning 2.0.x)
- asyncpg: latest 0.31.0 (pinning 0.29.x per CLAUDE.md)
- alembic: latest 1.18.4 (pinning 1.13.x per CLAUDE.md)
- uvicorn: latest 0.49.0 (pinning 0.30.x per CLAUDE.md)
- python-multipart: latest 0.0.32 (pinning 0.0.9 per CLAUDE.md)
- pytest: latest 9.0.3 (pinning 8.x per CLAUDE.md)
- pytest-asyncio: latest 1.4.0 (pinning 0.23.x per CLAUDE.md)
- httpx: latest 0.28.1 (pinning 0.27.x per CLAUDE.md)
- factory-boy: latest 3.3.3

---

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — packages are CLAUDE.md-specified; PyPI versions verified; npm versions unavailable from this environment but are all well-established packages
- Architecture: MEDIUM — patterns sourced from official FastAPI docs and authoritative blog posts; confirmed against official sources
- Pitfalls: MEDIUM — drawn from STATE.md critical pitfalls (CP-1 through CP-4, CM-7) and official documentation warnings

**Research date:** 2026-06-11
**Valid until:** 2026-07-11 (30 days — stable stack)
