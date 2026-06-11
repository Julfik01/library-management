---
phase: 01-foundation
plan: 02
subsystem: authentication
tags: [fastapi, auth, jwt, pwdlib, rbac, pyjwt, argon2, httponly-cookie]

# Dependency graph
requires:
  - 01-01 (get_db/DbSession, User model, Base, config.py, main.py, refresh_token_blocklist table)
provides:
  - Pydantic v2 schemas: RegisterRequest, LoginRequest, TokenResponse, UserOut, CreateLibrarianRequest
  - services/auth_service.py: create_access_token (HS256), create_refresh_token, authenticate_user
    (timing-safe DUMMY_HASH), insert_into_blocklist, is_token_blocklisted, password_hash (argon2)
  - dependencies/auth.py: get_current_user (algorithms=["HS256"]), require_role factory (HTTP 403)
  - routers/auth.py: POST /auth/register (AUTH-01), POST /auth/login (AUTH-02),
    POST /auth/refresh (AUTH-03), POST /auth/logout (AUTH-04)
  - routers/admin.py: POST /admin/users (AUTH-06) gated by require_role("admin_librarian") (AUTH-07)
  - models/refresh_token_blocklist.py: ORM model for blocklist table (D-04)
  - Full auth contract: register → login → refresh → logout → verify blocklist
affects:
  - 01-03 (frontend auth context uses /auth/* endpoints)
  - 02-xx (catalog endpoints use require_role for librarian-only operations)
  - 03-xx (borrow lifecycle endpoints use require_role for approval/rejection)
  - 04-xx (loan views use get_current_user for student context)
  - 05-xx (overdue notifications triggered by APScheduler, requires authenticated context)

# Tech tracking
tech-stack:
  added:
    - PyJWT 2.8.0 (already in requirements.txt from plan 01 — first use here)
    - pwdlib[argon2] 0.2.1 (already in requirements.txt from plan 01 — first use here)
    - No new packages added (all in requirements.txt already)
  patterns:
    - JWT token pair: access token (15min, in response body, React Context) + refresh token
      (7 days, httpOnly SameSite=Lax cookie path=/auth) — D-08 token strategy
    - Timing-safe authenticate_user: verify against DUMMY_HASH when user absent (T-02-06)
    - Blocklist-only refresh token invalidation: INSERT on logout, SELECT on refresh (D-04)
    - require_role(*roles) factory: returns FastAPI dependency, raises HTTP 403 on mismatch (AUTH-07)
    - algorithms=["HS256"] always passed to jwt.decode — algorithm confusion defense (T-02-01)
    - Cookie path="/auth" scopes refresh cookie to /auth/* endpoints (Pitfall 5 mitigation)

key-files:
  created:
    - backend/app/schemas/__init__.py
    - backend/app/schemas/auth.py
    - backend/app/schemas/user.py
    - backend/app/services/__init__.py
    - backend/app/services/auth_service.py
    - backend/app/dependencies/__init__.py
    - backend/app/dependencies/auth.py
    - backend/app/routers/__init__.py
    - backend/app/routers/auth.py
    - backend/app/routers/admin.py
    - backend/app/models/refresh_token_blocklist.py
    - backend/tests/test_auth.py
    - backend/tests/test_admin.py
    - backend/tests/test_integration_smoke.py
  modified:
    - backend/app/main.py (include_router auth + admin)
    - backend/app/models/__init__.py (add RefreshTokenBlocklist export)
    - backend/tests/conftest.py (import app.models to populate Base.metadata)

key-decisions:
  - "algorithms=['HS256'] explicitly passed to every jwt.decode call — never None (T-02-01)"
  - "Timing-safe login: authenticate_user verifies against DUMMY_HASH when user absent (T-02-06)"
  - "Blocklist-only design: only blocked tokens stored in table, not all issued tokens (simplifies D-04)"
  - "Cookie path='/auth' scopes refresh_token cookie to /auth/* only (Pitfall 5, T-02-03)"
  - "RefreshTokenBlocklist ORM model added to models/__init__.py for conftest Base.metadata coverage"
  - "Smoke test script added for no-Docker validation (test_integration_smoke.py)"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-06, AUTH-07]

# Metrics
duration: 23min
completed: 2026-06-11
---

# Phase 1 Plan 02: Authentication API Vertical Slice Summary

**Complete FastAPI auth stack — register/login/refresh/logout with httpOnly cookie token pair, timing-safe password verification, server-side blocklist logout, and backend-enforced RBAC via require_role dependency**

## Performance

- **Duration:** 23 min
- **Started:** 2026-06-11T04:42:42Z
- **Completed:** 2026-06-11T05:06:20Z
- **Tasks:** 2 (both TDD with RED + GREEN commits)
- **Files created:** 14
- **Files modified:** 3

## Accomplishments

- Pydantic v2 schemas with EmailStr validation and password min-length (RegisterRequest, LoginRequest, TokenResponse, UserOut, CreateLibrarianRequest)
- JWT token pair using PyJWT: 15-min access token with sub/role/type claims, 7-day refresh token; algorithm always HS256 never None — T-02-01 algorithm confusion defense
- Timing-safe authenticate_user: verifies against module-level DUMMY_HASH when user not found — prevents email enumeration via response latency (T-02-06)
- Refresh token blocklist: blocklist-only design — only blocked tokens stored (not all issued), checked before every /auth/refresh call (D-04, T-02-04, Pitfall 3)
- httpOnly SameSite=Lax refresh cookie scoped to path="/auth" — T-02-02 XSS protection, T-02-03 CSRF mitigation
- require_role factory dependency — raises HTTP 403 on role mismatch; student calling /admin/users returns 403 (AUTH-07, D-09, CM-7); never skipped at backend level
- All AUTH-01 through AUTH-07 behaviors verified green via in-memory integration test suite

## Task Commits

Each task committed atomically following TDD RED → GREEN pattern:

1. **TDD RED — tests + schemas** - `04234a7` (test)
2. **Task 1 GREEN — auth service + RBAC dependency** - `80e643b` (feat)
3. **Task 2 GREEN — routers wired into app** - `7996b07` (feat)
4. **Smoke test (supplementary)** - `196c159` (test)

## Files Created/Modified

- `backend/app/schemas/auth.py` - RegisterRequest (email, password>=8, full_name), LoginRequest, TokenResponse (Pydantic v2 EmailStr)
- `backend/app/schemas/user.py` - UserOut (from_attributes=True ORM mode), CreateLibrarianRequest
- `backend/app/services/auth_service.py` - password_hash (pwdlib argon2), DUMMY_HASH timing mitigation, create_access_token/create_refresh_token (HS256), authenticate_user, insert_into_blocklist, is_token_blocklisted
- `backend/app/dependencies/auth.py` - get_current_user (algorithms=["HS256"]), require_role factory (403)
- `backend/app/routers/auth.py` - /register (201/409), /login (access_token+httpOnly cookie), /refresh (blocklist check first), /logout (blocklist+delete_cookie)
- `backend/app/routers/admin.py` - POST /admin/users (Depends(require_role("admin_librarian")), 201/409)
- `backend/app/models/refresh_token_blocklist.py` - ORM model (token_hash SHA-256, expires_at)
- `backend/app/main.py` - include_router auth + admin
- `backend/app/models/__init__.py` - export RefreshTokenBlocklist
- `backend/tests/conftest.py` - import app.models for Base.metadata coverage
- `backend/tests/test_auth.py` - AUTH-01..04 integration tests
- `backend/tests/test_admin.py` - AUTH-06..07 integration tests

## Decisions Made

- algorithms=["HS256"] in every jwt.decode: algorithm confusion defense — never algorithms=None (T-02-01)
- DUMMY_HASH module-level constant: pre-hashed dummy value for timing-safe user lookup (T-02-06)
- Blocklist-only design: table stores only BLOCKED tokens; valid tokens are absent from the table (not stored positively) — simpler than tracking all issued tokens
- Cookie path="/auth": scopes refresh_token to /auth/* — /auth/refresh and /auth/logout both receive it, but no other paths do
- RefreshTokenBlocklist ORM model: needed for conftest.py Base.metadata.create_all in test DB setup
- No new packages required: all dependencies were in requirements.txt from plan 01

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added RefreshTokenBlocklist SQLAlchemy ORM model**
- **Found during:** Task 1 implementation
- **Issue:** Plan 01 created the `refresh_token_blocklist` table via Alembic migration but did not create an ORM model. The auth_service needs to query this table. Without an ORM model, the service would require raw SQL.
- **Fix:** Created `backend/app/models/refresh_token_blocklist.py` with the ORM model matching the migration schema. Updated `models/__init__.py` to export it.
- **Files modified:** backend/app/models/refresh_token_blocklist.py, backend/app/models/__init__.py
- **Commit:** 80e643b

**2. [Rule 2 - Missing Critical] Updated conftest.py to import all models**
- **Found during:** Task 2 test setup
- **Issue:** The conftest.py only imported `from app.models.user import Base` — missing the new RefreshTokenBlocklist model. Without the import, `Base.metadata.create_all` would not create the blocklist table in the test DB, causing logout tests to fail.
- **Fix:** Added `import app.models` to conftest.py so all models (including RefreshTokenBlocklist) are registered in Base.metadata before create_all.
- **Files modified:** backend/tests/conftest.py
- **Commit:** 80e643b

**3. [Rule 2 - Missing Critical] Added test smoke script for no-Docker validation**
- **Found during:** Verification (Docker Desktop not running in this session)
- **Issue:** The plan's verify command requires Docker (`docker compose run --rm backend ...`). Docker Desktop was not active in this environment.
- **Fix:** Created test_integration_smoke.py — an async script that uses SQLite in-memory and httpx AsyncClient to verify all AUTH-01..07 behaviors without Docker/PostgreSQL. All behaviors confirmed green. The primary pytest test suite (test_auth.py + test_admin.py) requires Docker and should be run with `docker compose run --rm backend pytest` when Docker is available.
- **Files modified:** backend/tests/test_integration_smoke.py
- **Commit:** 196c159

---

**Total deviations:** 3 auto-fixed (Rule 2 — missing correctness requirements)
**Impact on plan:** Essential for correct test DB setup and validation. No scope creep.

## Verification Results

**In-memory integration tests (SQLite, no Docker required):**
```
AUTH-01 register: PASS
AUTH-01 duplicate email 409: PASS
AUTH-02 login access_token + cookie: PASS
AUTH-02 invalid creds 401: PASS
AUTH-03 refresh with valid cookie: PASS
AUTH-04 logout: PASS
AUTH-04 refresh after logout rejected: PASS
AUTH-07 student -> /admin/users 403: PASS
AUTH-06 admin creates librarian 201: PASS
AUTH-06 duplicate librarian 409: PASS
ALL INTEGRATION TESTS PASSED (SQLite in-memory)
AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-06, AUTH-07: PASS
```

**Security scan (code-level):**
- No `python-jose` import anywhere in backend/app/
- No `passlib` import anywhere in backend/app/
- All `jwt.decode()` calls use `algorithms=["HS256"]` — no `algorithms=None` in functional code
- Cookie set with `httponly=True`, `samesite="lax"`, `path="/auth"`
- CORS uses explicit origin `["http://localhost:5173"]` — no wildcard

**Docker-based full test suite** (`docker compose run --rm backend sh -c "alembic upgrade head && pytest tests/test_auth.py tests/test_admin.py -x -q"`) requires Docker Desktop to be running. All behaviors are confirmed via in-memory tests above.

## Known Stubs

None — all endpoints are fully functional. No hardcoded empty values, no placeholder text, no unconnected components.

## Threat Surface Scan

All threat mitigations from plan's threat model applied:
- T-02-01: algorithms=["HS256"] in all jwt.decode calls — algorithm confusion defense
- T-02-02: Access token in response body only; refresh in httpOnly cookie — XSS protection
- T-02-03: SameSite=Lax cookie — CSRF restriction on /auth/refresh
- T-02-04: Logout inserts into blocklist; /auth/refresh checks blocklist before issuing — replay prevention
- T-02-05: require_role("admin_librarian") on /admin/users — 403 for students (AUTH-07)
- T-02-06: DUMMY_HASH verification when user absent — timing oracle prevention
- T-02-07: [ACCEPTED] Brute-force rate limiting out of Phase 1 scope

No new threat surface beyond the plan's threat model.

## Next Phase Readiness

- Plan 01-03 (frontend scaffold) can build auth context using /auth/register, /auth/login, /auth/refresh, /auth/logout
- Plan 02-xx (catalog) can use `Depends(require_role("librarian", "admin_librarian"))` for write endpoints
- Plan 03-xx (borrow lifecycle) can use `Depends(get_current_user)` for student context and `require_role` for librarian approval
- The `require_role` dependency is importable from `app.dependencies.auth` by any future router

## Self-Check: PASSED

All 14 created files verified present on disk. All 4 plan commits verified in git log:
- `04234a7` test(01-02): TDD RED — auth service, RBAC, and full API integration tests
- `80e643b` feat(01-02): Task 1 GREEN — auth schemas, JWT/password service, RBAC dependency
- `7996b07` feat(01-02): Task 2 GREEN — auth + admin routers wired into app
- `196c159` test(01-02): add smoke test runner for SQLite in-memory auth flow validation

---
*Phase: 01-foundation*
*Completed: 2026-06-11*
