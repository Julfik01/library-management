---
phase: 01-foundation
plan: 01
subsystem: database
tags: [fastapi, sqlalchemy, alembic, postgresql, docker, asyncpg, pydantic-settings]

# Dependency graph
requires: []
provides:
  - Docker Compose 4-service dev stack (db, backend, frontend, mailhog)
  - SQLAlchemy 2.0 async engine + async_sessionmaker + DbSession alias
  - DeclarativeBase + 4 ORM models (User, Book, BorrowRequest, Loan)
  - Single Alembic migration 001_initial_schema with complete 5-phase schema
  - 5 tables with all FK constraints, CHECK constraints, and D-07 indexes
  - GIN full-text index on books (title + author) for catalog search (CAT-05)
  - Admin librarian seeded from ADMIN_EMAIL + ADMIN_PASSWORD env vars (AUTH-05, D-10)
  - pytest infrastructure (pytest.ini + conftest.py + test_schema.py)
affects:
  - 01-02 (auth endpoints use get_db, User model, Base)
  - 01-03 (frontend scaffold wired to backend container)
  - 02-xx (Book model, catalog endpoints)
  - 03-xx (BorrowRequest + Loan models, borrow lifecycle)
  - 04-xx (Loan views, student history)
  - 05-xx (overdue_notified_at field, APScheduler job)

# Tech tracking
tech-stack:
  added:
    - fastapi==0.115.12
    - uvicorn[standard]==0.30.6
    - sqlalchemy==2.0.41 (async engine)
    - asyncpg==0.29.0
    - alembic==1.13.3
    - PyJWT==2.8.0 (not python-jose — CVEs)
    - pwdlib[argon2]==0.2.1 (not passlib — unmaintained)
    - pydantic[email]==2.11.5
    - pydantic-settings==2.9.1
    - python-multipart==0.0.9
    - python-dotenv==1.0.1
    - fastapi-mail==1.4.2
    - pytest==8.3.4 + pytest-asyncio==0.23.8 + httpx==0.27.2
    - postgres:16-alpine (Docker)
    - mailhog/mailhog (Docker)
  patterns:
    - SQLAlchemy 2.0 async: create_async_engine + async_sessionmaker + get_db dependency
    - DbSession = Annotated[AsyncSession, Depends(get_db)] alias for route signatures
    - Pydantic BaseSettings for all config/secrets (not os.environ directly in app code)
    - VARCHAR + CHECK constraints for status/role fields (not native PostgreSQL ENUM)
    - Alembic async env.py: async_engine_from_config + asyncio.run (not sync template)
    - All model imports before target_metadata = Base.metadata in env.py

key-files:
  created:
    - compose.yml
    - .env.example
    - .gitignore
    - backend/Dockerfile
    - backend/requirements.txt
    - backend/requirements-dev.txt
    - backend/app/__init__.py
    - backend/app/main.py
    - backend/app/config.py
    - backend/app/database.py
    - backend/app/models/__init__.py
    - backend/app/models/user.py
    - backend/app/models/book.py
    - backend/app/models/borrow_request.py
    - backend/app/models/loan.py
    - backend/alembic.ini
    - backend/alembic/env.py
    - backend/alembic/script.py.mako
    - backend/alembic/versions/001_initial_schema.py
    - backend/pytest.ini
    - backend/tests/__init__.py
    - backend/tests/conftest.py
    - backend/tests/test_schema.py
  modified: []

key-decisions:
  - "PyJWT 2.8.0 over python-jose (CVEs in python-jose — CLAUDE.md constraint)"
  - "pwdlib[argon2] 0.2.1 over passlib (passlib unmaintained since 2023 — CLAUDE.md constraint)"
  - "VARCHAR + CHECK constraints for role/status — not native PostgreSQL ENUM (D-05)"
  - "Alembic async template (async_engine_from_config) — sync template hangs with asyncpg (Pitfall 1)"
  - "All 4 model modules imported in env.py before target_metadata — prevents empty migration (Pitfall 2)"
  - "DB URL read from os.environ in env.py — never embedded in alembic.ini (T-01-01)"
  - "admin_librarian seeded via migration from ADMIN_EMAIL + ADMIN_PASSWORD env vars (D-10, AUTH-05)"
  - "CORS allow_origins=['http://localhost:5173'] — explicit list, never wildcard with credentials (CLAUDE.md)"
  - "backend depends_on db with condition: service_healthy — prevents Alembic race on cold start (Pitfall 6)"

patterns-established:
  - "Pattern 1: Per-request DB session via async_sessionmaker + async with in get_db() — no module-level AsyncSession (CP-2)"
  - "Pattern 2: DbSession = Annotated[AsyncSession, Depends(get_db)] alias for clean route handler signatures"
  - "Pattern 3: DeclarativeBase in models/user.py, all other models import Base from there"
  - "Pattern 4: models/__init__.py re-exports all models for single-import in Alembic env.py"
  - "Pattern 5: Alembic env.py uses async_engine_from_config + asyncio.run (async template only)"
  - "Pattern 6: Admin seed in upgrade() via op.execute(sa.text(...).bindparams(...))"

requirements-completed: [AUTH-05]

# Metrics
duration: 9min
completed: 2026-06-10
---

# Phase 1 Plan 01: Docker Compose + Async DB + Full 5-Phase Schema Summary

**PostgreSQL 16 dev stack, SQLAlchemy 2.0 async data layer, and complete 5-table Alembic migration with argon2-hashed admin seed — all schema correctness constraints active before any endpoint exists**

## Performance

- **Duration:** 9 min
- **Started:** 2026-06-10T21:27:40Z
- **Completed:** 2026-06-10T21:37:19Z
- **Tasks:** 3 (Task 3 was TDD with 2 commits: RED + GREEN)
- **Files created:** 23

## Accomplishments

- Docker Compose 4-service dev stack with pg_isready healthcheck gating backend startup (prevents Alembic DB race on cold container start)
- SQLAlchemy 2.0 async data layer: async engine, async_sessionmaker, per-request get_db dependency, DbSession alias — no module-level shared session (CP-2)
- Complete 5-table schema in a single Alembic migration (001_initial_schema.py): users, refresh_token_blocklist, books, borrow_requests, loans — all tables for all 5 phases from day one (D-01, D-02)
- All CHECK constraints active at DB layer: CP-1 (available_copies >= 0 and <= total_copies), D-05 (role/status VARCHAR CHECK), GIN full-text index on books (CAT-05 search readiness)
- Admin librarian seeded from ADMIN_EMAIL/ADMIN_PASSWORD env vars with argon2 hash (AUTH-05, D-10, T-01-03)
- TDD test scaffold: pytest with asyncio_mode=auto, function-scoped db_session fixture, 6 schema behavior tests

## Task Commits

Each task committed atomically:

1. **Task 1: Docker Compose dev stack + backend container scaffold** - `21f4303` (feat)
2. **Task 2: SQLAlchemy 2.0 async data layer + all 4 ORM models** - `713253c` (feat)
3. **Task 3: TDD RED — schema test scaffold** - `a78658c` (test)
4. **Task 3: TDD GREEN — Alembic async setup + 001_initial_schema migration** - `1c2390b` (feat)

## Files Created/Modified

- `compose.yml` - 4-service dev stack (db, backend, frontend, mailhog) with healthcheck gate
- `.env.example` - documents all required env vars (POSTGRES_*, SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, VITE_API_URL)
- `.gitignore` - excludes .env and generated files (T-01-01 secret disclosure mitigation)
- `backend/Dockerfile` - python:3.12-slim base (CLAUDE.md constraint), installs requirements.txt
- `backend/requirements.txt` - pinned deps: PyJWT 2.8.0, pwdlib[argon2] 0.2.1, SQLAlchemy 2.0.41, asyncpg 0.29.0, Alembic 1.13.3
- `backend/requirements-dev.txt` - pytest 8.3.4, pytest-asyncio 0.23.8, httpx 0.27.2, factory-boy 3.3.3
- `backend/app/config.py` - Pydantic BaseSettings (DATABASE_URL, SECRET_KEY, ENVIRONMENT, DEBUG, ADMIN_EMAIL, ADMIN_PASSWORD)
- `backend/app/main.py` - FastAPI app with explicit CORS origins (not wildcard), GET /health endpoint
- `backend/app/database.py` - async engine + async_sessionmaker + get_db + DbSession
- `backend/app/models/user.py` - Base (DeclarativeBase) + User model with role CHECK constraint
- `backend/app/models/book.py` - Book model with CP-1 available_copies CHECK constraints
- `backend/app/models/borrow_request.py` - BorrowRequest with D-05 VARCHAR CHECK status
- `backend/app/models/loan.py` - Loan with D-05 VARCHAR CHECK status + D-06 overdue_notified_at
- `backend/app/models/__init__.py` - re-exports all models + Base for single import in env.py
- `backend/alembic.ini` - Alembic config, DB URL from env (not hardcoded — T-01-01)
- `backend/alembic/env.py` - async template: async_engine_from_config + asyncio.run, all model imports
- `backend/alembic/script.py.mako` - migration file template
- `backend/alembic/versions/001_initial_schema.py` - complete 5-phase schema + D-07 indexes + D-10 admin seed
- `backend/pytest.ini` - asyncio_mode=auto, testpaths=tests
- `backend/tests/conftest.py` - function-scoped db_session (create_all/drop_all) + HTTP client fixture
- `backend/tests/test_schema.py` - 6 schema behavior tests (table existence, CHECK constraint enforcement)

## Decisions Made

- PyJWT over python-jose: python-jose has unresolved CVEs; CLAUDE.md mandates PyJWT
- pwdlib[argon2] over passlib: passlib unmaintained since 2023; FastAPI docs now recommend pwdlib
- VARCHAR CHECK over native ENUM for role/status: easier to extend without ALTER TYPE migrations (D-05)
- Alembic async template mandatory: sync template hangs with asyncpg (Pitfall 1 from RESEARCH.md)
- All 4 model imports before target_metadata in env.py: prevents empty migration (Pitfall 2 from RESEARCH.md)
- DB URL from os.environ in env.py, not alembic.ini: mitigates T-01-01 secret disclosure
- CORS allow_origins=['http://localhost:5173'] explicit list: browsers block wildcard + credentials (CLAUDE.md)
- service_healthy gate on backend depends_on: prevents Alembic race on container cold start (Pitfall 6)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added .gitignore to exclude .env**
- **Found during:** Task 1 (Docker Compose scaffold)
- **Issue:** The plan didn't explicitly list .gitignore but threat model T-01-01 requires .env be excluded from git. Without .gitignore, secrets could be accidentally committed.
- **Fix:** Created .gitignore excluding .env, Python caches, node_modules, and IDE files.
- **Files modified:** .gitignore
- **Verification:** .gitignore present and .env is listed
- **Committed in:** `21f4303` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical security file)
**Impact on plan:** Essential security measure. No scope creep.

## Issues Encountered

None — plan executed cleanly following PATTERNS.md and RESEARCH.md guidance.

## Known Stubs

None — all files are fully functional (no hardcoded empty values, no placeholder text, no unconnected components). The frontend service in compose.yml references `./frontend` which is created in plan 03; this is by design (the plan explicitly notes this).

## Threat Flags

No new threat surface beyond the plan's threat model. All T-01-xx mitigations applied:
- T-01-01: .env gitignored; alembic.ini reads URL from env only
- T-01-02: CP-1 CHECK constraints in migration
- T-01-03: Admin password argon2-hashed; from env var
- T-01-04: VARCHAR + CHECK on role/status (D-05)

## User Setup Required

None — no external service configuration required. Developers copy `.env.example` to `.env`, fill in values, and run `docker compose up`.

## Next Phase Readiness

- Plan 01-02 (auth endpoints) can build directly on: User model, get_db/DbSession, Base, config.py, main.py
- Plan 01-03 (frontend scaffold) creates `./frontend` directory to satisfy compose.yml frontend service
- All later phases can rely on the complete schema being in place from day one (no schema migrations needed in phases 2-5)
- GIN index on books is active from day one for phase 2 catalog search

## Self-Check: PASSED

All 24 files verified present on disk. All 4 task commits verified in git log:
- `21f4303` feat(01-01): Task 1 — Docker Compose dev stack + backend scaffold
- `713253c` feat(01-01): Task 2 — SQLAlchemy async data layer + 4 ORM models
- `a78658c` test(01-01): Task 3 TDD RED — schema tests
- `1c2390b` feat(01-01): Task 3 TDD GREEN — Alembic migration + admin seed

---
*Phase: 01-foundation*
*Completed: 2026-06-10*
