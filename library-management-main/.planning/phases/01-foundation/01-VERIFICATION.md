---
phase: 01-foundation
verified: 2026-06-11T08:30:00Z
status: gaps_found
score: 6/7 must-haves verified
overrides_applied: 0
gaps:
  - truth: "A new student can register with email and password and immediately log in without admin intervention"
    status: failed
    reason: >
      POST /auth/register returns UserOut (id, email, full_name, role) — not TokenResponse.
      RegisterPage.tsx calls setAuth(data.access_token, data.user) after registration;
      data.access_token and data.user are both undefined on the UserOut payload.
      setAuth(undefined, undefined) stores undefined as accessToken in AuthContext and module-level
      axios ref. ProtectedRoute checks !accessToken (undefined is falsy) and redirects to /login.
      The student registers successfully server-side but is NOT automatically authenticated —
      they land on /dashboard and are immediately bounced back to /login.
      The ROADMAP success criterion "immediately log in" is not met.
    artifacts:
      - path: "backend/app/routers/auth.py"
        issue: "POST /auth/register returns response_model=UserOut (201), not TokenResponse — correct per REST conventions but mismatched with frontend expectation"
      - path: "frontend/src/pages/RegisterPage.tsx"
        issue: "Line 59: setAuth(data.access_token, data.user) — both undefined when response is UserOut. Should call /auth/login after registration, or backend should return TokenResponse on register."
    missing:
      - "RegisterPage.tsx must be fixed: after successful POST /auth/register, call POST /auth/login with the same credentials and use the TokenResponse to call setAuth — OR — the /auth/register endpoint must return TokenResponse (access_token + httpOnly cookie + user)."
      - "A secondary login call after registration is the minimal fix. Alternatively, change the register endpoint to return TokenResponse (sets cookie + returns token), matching the pattern of many auth APIs."
deferred:
  - truth: "rejection_note column on borrow_requests table (for BORROW-06 librarian rejection notes)"
    addressed_in: "Phase 3"
    evidence: "BORROW-06 requirement is Phase 3: 'Librarian can reject a request with an optional rejection note'. The Phase 1 migration does not include this column — it will be added in Phase 3."
---

# Phase 1: Foundation Verification Report

**Phase Goal:** Any user can register, log in, and be routed to a role-appropriate view — and the full database schema with all constraints is in place from day one.
**Verified:** 2026-06-11T08:30:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A new student can register and immediately log in without admin intervention | FAILED | `POST /auth/register` returns `UserOut` (no `access_token`). `RegisterPage.tsx:59` calls `setAuth(data.access_token, data.user)` where both are `undefined`. `ProtectedRoute` rejects `undefined` token — user bounced to `/login` after registration. |
| 2 | A logged-in user stays logged in across browser refreshes | VERIFIED | `App.tsx` bootstrap `useEffect` POSTs `/auth/refresh`; httpOnly cookie auto-sent; `setAuth` restores session; `Skeleton` shown during wait. |
| 3 | A user who logs out cannot access protected pages, and session is invalidated server-side | VERIFIED | `POST /auth/logout` calls `insert_into_blocklist`; subsequent `/auth/refresh` with same token returns 401. `ProtectedRoute` redirects to `/login` when `accessToken` is falsy. |
| 4 | The seeded admin librarian account can log in and create a new librarian account from the admin UI | VERIFIED | Alembic migration `001_initial_schema.py` seeds admin from `ADMIN_EMAIL`/`ADMIN_PASSWORD` env vars with argon2 hash. `CreateLibrarianPage.tsx` posts to `/admin/users`. Human checkpoint confirmed full loop. |
| 5 | Calling any librarian or admin endpoint as a student returns 403 Forbidden | VERIFIED | `require_role("admin_librarian")` dependency on `POST /admin/users` raises HTTP 403. Human checkpoint curl-bypass confirmed. Smoke test asserts 403. |

**Score:** 4/5 ROADMAP success criteria verified (Truth 1 fails). 6/7 plan must-haves verified (Truth 1 of plan 01-03 fails).

---

## Gaps Detail

### BLOCKER: RegisterPage post-registration auth state is broken (AUTH-01)

**Root cause:** The backend `POST /auth/register` returns `UserOut` (HTTP 201):
```
{ "id": 1, "email": "...", "full_name": "...", "role": "student" }
```

`RegisterPage.tsx` line 59 does:
```typescript
const { data } = await api.post("/auth/register", values);
setAuth(data.access_token, data.user);  // both are undefined
navigate("/dashboard", { replace: true });
```

`setAuth(undefined, undefined)` stores `undefined` as `accessToken`. TypeScript does not catch this because `api.post()` returns `AxiosResponse<any>` — no compile-time type mismatch. The `npm run build` succeeds.

When the user navigates to `/dashboard`, `ProtectedRoute` evaluates `!accessToken` as `true` (undefined is falsy) and redirects to `/login`. The student must log in manually after registering.

The ROADMAP success criterion "immediately log in" is not satisfied.

**Note:** The 01-03 human checkpoint (Task 3) was listed as "awaiting human checkpoint" at the time of the 01-03 SUMMARY, and the SUMMARY's self-check does not include a runtime test of the register→dashboard flow. The 01-04 human checkpoint covered only the admin flow (steps 1-5 of 01-04-PLAN.md), not student registration. This behavioral defect went undetected.

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/routers/auth.py` | Register, login, refresh, logout endpoints | VERIFIED | All 4 endpoints present and substantive. Returns correct status codes and token structures. |
| `backend/app/routers/admin.py` | POST /admin/users with require_role guard | VERIFIED | Depends on `require_role("admin_librarian")`, creates user with role='librarian'. |
| `backend/app/dependencies/auth.py` | `get_current_user` + `require_role` factory | VERIFIED | `algorithms=["HS256"]` always passed; raises HTTP 403 on role mismatch. |
| `backend/app/services/auth_service.py` | Token creation, password hashing, blocklist | VERIFIED | PyJWT HS256, pwdlib[argon2], DUMMY_HASH timing mitigation, SHA-256 blocklist. |
| `backend/alembic/versions/001_initial_schema.py` | Full 5-table schema + admin seed | VERIFIED | All 5 tables, CHECK constraints, D-07 indexes, GIN fulltext, admin seed from env vars. |
| `frontend/src/context/AuthContext.tsx` | In-memory access token, no localStorage | VERIFIED | Module-level `setAccessToken` synced with React state; no localStorage reference. |
| `frontend/src/lib/axios.ts` | withCredentials + Bearer interceptor + 401 refresh queue | VERIFIED | `withCredentials: true`; request interceptor injects Bearer; response interceptor queues 401s and calls `/auth/refresh`. |
| `frontend/src/App.tsx` | AUTH-03 bootstrap + route map | VERIFIED | `useEffect` POSTs `/auth/refresh` on mount; admin route wrapped in `ProtectedRoute allowedRoles={['admin_librarian']}`. |
| `frontend/src/components/ProtectedRoute.tsx` | Client UX gate with allowedRoles | VERIFIED | Checks `accessToken` (null → /login), checks `allowedRoles` (mismatch → /unauthorized). |
| `frontend/src/pages/LoginPage.tsx` | AUTH-02 login screen | VERIFIED | Posts to `/auth/login`; calls `setAuth(data.access_token, data.user)` — response is `TokenResponse`, so this is correct. |
| `frontend/src/pages/RegisterPage.tsx` | AUTH-01 register screen | STUB (partial) | Form posts to `/auth/register` correctly, but `setAuth(data.access_token, data.user)` on `UserOut` response leaves auth undefined. |
| `frontend/src/pages/DashboardPage.tsx` | Role-appropriate dashboard | VERIFIED | Role-gated nav links, `WelcomeContent` by role, Avatar dropdown with sign-out. |
| `frontend/src/pages/CreateLibrarianPage.tsx` | AUTH-06 admin create-librarian form | VERIFIED | TanStack Query mutation to `POST /admin/users`; toast on 201; 409/403 alerts; form reset. |
| `frontend/src/pages/UnauthorizedPage.tsx` | Access denied screen | VERIFIED | ShieldOff icon, "Access denied" heading, "Go to dashboard" button navigates to /dashboard. |
| `frontend/src/components/AdminNavLink.tsx` | Role-gated "Manage Users" link | VERIFIED | Renders only when `user.role === 'admin_librarian'`. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `App.tsx` | `/auth/refresh` on mount | `api.post("/auth/refresh")` in `useEffect` | WIRED | Bootstrap sets auth state before rendering routes. |
| `RegisterPage.tsx` | `POST /auth/register` | `api.post("/auth/register", values)` | WIRED | Request wired, but response handling broken — `data.access_token` is undefined on `UserOut`. |
| `LoginPage.tsx` | `POST /auth/login` | `api.post("/auth/login", values)` | WIRED | Correct — `setAuth(data.access_token, data.user)` on `TokenResponse`. |
| `App.tsx` | `ProtectedRoute allowedRoles={['admin_librarian']}` | `/admin/users/new` route | WIRED | Non-admins redirect to `/unauthorized`. |
| `CreateLibrarianPage.tsx` | `POST /admin/users` | `api.post("/admin/users", values)` via TanStack Query mutation | WIRED | Bearer token injected by axios interceptor. |
| `admin.py` | `require_role("admin_librarian")` | `Depends(require_role("admin_librarian"))` on route | WIRED | Backend returns 403 for non-admin tokens — confirmed by curl-bypass checkpoint and smoke test. |
| `auth.py /logout` | blocklist | `insert_into_blocklist(db, refresh_token)` | WIRED | Then `/auth/refresh` checks `is_token_blocklisted` before issuing new token. |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `DashboardPage.tsx` | `user` (from `useAuth()`) | `AuthContext` state — set by `setAuth` on login/refresh | Yes — from JWT decode at login or `/auth/refresh` response | FLOWING |
| `CreateLibrarianPage.tsx` | mutation result | `api.post("/admin/users")` → `POST /admin/users` → DB insert | Yes — real DB write, returns created user | FLOWING |
| `RegisterPage.tsx` | `data.access_token` | `api.post("/auth/register")` → `UserOut` | NO — `UserOut` has no `access_token` field | DISCONNECTED |

---

## Behavioral Spot-Checks

| Behavior | Check | Status |
|----------|-------|--------|
| `POST /auth/register` returns UserOut (no `access_token`) | Read `backend/app/routers/auth.py` line 43: `response_model=UserOut` | CONFIRMED |
| `RegisterPage.tsx` calls `setAuth(data.access_token, data.user)` | Read `frontend/src/pages/RegisterPage.tsx` line 59 | CONFIRMED |
| `ProtectedRoute` rejects undefined `accessToken` | `if (!accessToken) return <Navigate to="/login" replace />` — undefined is falsy | CONFIRMED — redirect fires |
| `POST /admin/users` returns 403 for student token | `require_role("admin_librarian")` dependency; confirmed in smoke test at line 124 | CONFIRMED |
| `POST /auth/logout` → blocklist → `/auth/refresh` rejected | Smoke test lines 102-110; `insert_into_blocklist` then `is_token_blocklisted` | CONFIRMED |
| httpOnly refresh cookie scoped to `/auth` path | `auth.py` line 113: `path="/auth"` | CONFIRMED |

---

## Requirements Coverage

| Requirement | Plan | Description | Status | Evidence |
|-------------|------|-------------|--------|----------|
| AUTH-01 | 01-02, 01-03 | Student can self-register with email and password | PARTIAL | Backend endpoint complete and correct. Frontend post-registration auth state broken — user not automatically logged in. |
| AUTH-02 | 01-02, 01-03 | Any user can log in with email and password | SATISFIED | `POST /auth/login` returns `TokenResponse`; `LoginPage.tsx` correctly calls `setAuth`. |
| AUTH-03 | 01-02, 01-03 | Session persists across page refreshes | SATISFIED | httpOnly cookie + `App.tsx` bootstrap `useEffect`. |
| AUTH-04 | 01-02 | Any user can log out; refresh token invalidated server-side | SATISFIED | `insert_into_blocklist` on logout; blocklist check on refresh. |
| AUTH-05 | 01-01 | Admin librarian seeded via Alembic from env vars | SATISFIED | `001_initial_schema.py` upgrade() seeds admin with argon2-hashed password. |
| AUTH-06 | 01-02, 01-04 | Admin librarian can create librarian accounts | SATISFIED | `POST /admin/users` with `require_role`; `CreateLibrarianPage.tsx` with mutation + toast. Human checkpoint confirmed. |
| AUTH-07 | 01-02, 01-04 | Backend enforces RBAC on protected endpoints | SATISFIED | `require_role` dependency raises HTTP 403; not frontend-only. Curl-bypass confirmed in human checkpoint. |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/pages/RegisterPage.tsx` | 59 | `setAuth(data.access_token, data.user)` where `data` is `UserOut` — both fields are `undefined` | BLOCKER | Student cannot log in automatically after registration; redirected to `/login` instead of `/dashboard`. |

No `TBD`, `FIXME`, or `XXX` markers found in any backend or frontend source files. The Tailwind `placeholder:text-muted-foreground` in `input.tsx` is a CSS class name, not a code stub.

---

## Human Verification Required

No additional human verification required. The blocking gap is programmatically verifiable (mismatched response schema vs. frontend expectation). All other behaviors were verified via code inspection and the human checkpoint in 01-04.

---

## Deferred Items

Items not yet met but explicitly addressed in later milestone phases.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | `rejection_note` column missing from `borrow_requests` table | Phase 3 | BORROW-06: "Librarian can reject a request with an optional rejection note" — Phase 3 requirement. Column not needed until Phase 3 borrow lifecycle endpoints are built. |

---

## Gaps Summary

**1 blocker found.** The phase goal "any user can register, log in, and be routed to a role-appropriate view" is not fully achieved.

The registration flow has a response-schema mismatch: `POST /auth/register` returns `UserOut` (id, email, full_name, role) but `RegisterPage.tsx` reads `data.access_token` and `data.user` from it. Both are `undefined`. The `setAuth(undefined, undefined)` call leaves the auth context with a falsy token. `ProtectedRoute` then redirects the newly registered student away from `/dashboard` to `/login`.

The student CAN register (server-side works), and they CAN then log in manually (LoginPage is correct). But the "immediately log in" part of ROADMAP success criterion 1 fails.

**Fix options:**
- Minimal: In `RegisterPage.tsx` `onSubmit`, after the successful register call, make a second `api.post("/auth/login", { email: values.email, password: values.password })` call and use that `TokenResponse` for `setAuth`.
- Cleaner: Change `POST /auth/register` to return `TokenResponse` (set httpOnly cookie + return `access_token` + `user`), matching the login response pattern.

All other 6/7 must-haves are verified. The auth API (AUTH-02 through AUTH-07), session persistence, logout/invalidation, admin seed, admin UI, RBAC, and route guarding are all correctly implemented and wired.

---

_Verified: 2026-06-11T08:30:00Z_
_Verifier: Claude (gsd-verifier)_
