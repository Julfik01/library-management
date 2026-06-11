---
phase: 01-foundation
plan: 04
subsystem: frontend
tags: [react, shadcn, rbac, admin, tanstack-query, react-hook-form, zod, route-guard]

# Dependency graph
requires:
  - 01-03 (Vite+React18 scaffold, AuthContext, ProtectedRoute, App.tsx route map, axios api instance, DashboardPage TopNav)
  - 01-02 (POST /admin/users contract: admin_librarian-only, 201/409/403 responses; POST /auth/login for seeded admin)
provides:
  - CreateLibrarianPage.tsx: admin-only Create Librarian screen (AUTH-06) — POST /admin/users mutation with Sonner toast, 409/403 Alert errors, form reset
  - AdminNavLink.tsx: role-gated "Manage Users" nav link (admin_librarian only) in DashboardPage TopNav
  - UnauthorizedPage.tsx: ShieldOff icon + "Access denied" + "Go to dashboard" (AUTH-07 client UX)
  - App.tsx: /admin/users/new wrapped in ProtectedRoute allowedRoles=['admin_librarian']; /unauthorized → UnauthorizedPage wired
  - End-to-end AUTH-06 loop verified: seeded admin → creates librarian → new librarian logs in
  - AUTH-07 backend RBAC verified: student curl-bypass of /admin/users returns HTTP 403
affects:
  - Phase 2 and beyond (all future phases build on the auth+RBAC system finalized here)
  - Phase 2 (Book Catalog) can start — Foundation phase complete

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Admin-only route guard: ProtectedRoute allowedRoles={['admin_librarian']} — non-admins auto-redirect to /unauthorized
    - Defense-in-depth: client ProtectedRoute is UX; backend require_role('admin_librarian') is the authority (CM-7, D-09)
    - TanStack Query mutation pattern for admin mutations: useMutation → POST /admin/users via api axios instance
    - Conditional nav rendering: AdminNavLink renders only when user.role === 'admin_librarian' (state from AuthContext)

key-files:
  created:
    - frontend/src/pages/CreateLibrarianPage.tsx (AUTH-06 — admin create-librarian form, POST /admin/users)
    - frontend/src/components/AdminNavLink.tsx (role-gated "Manage Users" nav link for admin_librarian)
  modified:
    - frontend/src/App.tsx (/admin/users/new route added with ProtectedRoute allowedRoles; /unauthorized wired)
    - frontend/src/pages/DashboardPage.tsx (Manage Users href fixed to /admin/users/new; Link component used)

key-decisions:
  - "ProtectedRoute allowedRoles pattern: non-matching roles redirect to /unauthorized, not /login — correct UX per UI-SPEC"
  - "AdminNavLink is UX-only; AUTH-07 defense-in-depth proven by curl-bypass 403 check in human checkpoint"
  - "DashboardPage Manage Users href corrected from /admin/users to /admin/users/new (Rule 1 bug fix inline)"

patterns-established:
  - "allowedRoles guard: ProtectedRoute wraps admin routes with allowedRoles={['admin_librarian']} — redirect to /unauthorized on role mismatch"
  - "Admin mutation: useMutation(POST /admin/users) → toast on 201 → form.reset(); 409 → inline Alert; 403 → inline Alert"

requirements-completed: [AUTH-06, AUTH-07]

# Metrics
duration: ~15min (task 1: ~12min; checkpoint approval: async)
completed: 2026-06-11
---

# Phase 1 Plan 04: Admin RBAC Screens + Phase 1 Completion Summary

**Create Librarian screen (AUTH-06) gated to admin_librarian with TanStack Query mutation, Unauthorized screen (AUTH-07), AdminNavLink, and defense-in-depth RBAC verified end-to-end via UI and curl-bypass 403**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-06-11T05:35:40Z
- **Completed:** 2026-06-11T05:49:36Z
- **Tasks executed:** 2 (Task 1: auto; Task 2: human-verify checkpoint — approved)
- **Files created:** 2
- **Files modified:** 2

## Accomplishments

### Task 1: Create Librarian + Unauthorized screens, admin nav link, route guarding

- `CreateLibrarianPage.tsx` built per UI-SPEC Screen 4: shadcn Card + Form (react-hook-form + zod: full_name, email, password min-8), TanStack Query mutation to POST /admin/users via `api` axios instance
  - On 201: Sonner toast "Librarian account created.", form.reset(), user stays on page
  - On 409: inline Alert "An account with this email already exists."
  - On 403: inline Alert "You don't have permission to perform this action."
  - "← Back to dashboard" link; CTA "Create account" / "Creating account..." loading state
- `AdminNavLink.tsx`: renders "Manage Users" link (→ /admin/users/new) only when `user.role === 'admin_librarian'`; integrated into DashboardPage TopNav
- `App.tsx`: `/admin/users/new` route wrapped in `ProtectedRoute allowedRoles={['admin_librarian']}`; `/unauthorized` route wired to UnauthorizedPage (replacing plan-03 placeholder)
- `DashboardPage.tsx`: Manage Users href corrected from `/admin/users` → `/admin/users/new`; `<a>` replaced with React Router `<Link>` (Rule 1 inline fix)
- `npm run build` clean — no TypeScript errors

### Task 2: Human Checkpoint — All 5 Verification Steps Passed

1. Seeded admin login: "Admin Dashboard" shown, "Manage Users" nav link visible — confirmed
2. Create librarian form: success toast shown, form resets — confirmed
3. New librarian login (AUTH-06 full loop): "Librarian Dashboard" shown — confirmed
4. Client guard: librarian navigating to /admin/users/new → /unauthorized "Access denied" — confirmed
5. Backend RBAC curl bypass (AUTH-07): student access token POST /admin/users → HTTP 403 — confirmed

All five Phase 1 success criteria from the ROADMAP are demonstrably TRUE.

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Create Librarian + Unauthorized screens, admin nav link, route guarding | c98c252 | frontend/src/pages/CreateLibrarianPage.tsx, frontend/src/components/AdminNavLink.tsx, frontend/src/App.tsx, frontend/src/pages/DashboardPage.tsx |
| 2 | Human-verify checkpoint | — | Approved by user (all 5 steps passed) |

## Files Created/Modified

- `frontend/src/pages/CreateLibrarianPage.tsx` — AUTH-06 admin create-librarian form with TanStack Query mutation, toast, 409/403 error handling
- `frontend/src/components/AdminNavLink.tsx` — role-gated "Manage Users" nav link (admin_librarian only)
- `frontend/src/App.tsx` — /admin/users/new route with ProtectedRoute allowedRoles; /unauthorized wired
- `frontend/src/pages/DashboardPage.tsx` — Manage Users href fix + Link component

## Decisions Made

- **ProtectedRoute allowedRoles redirect target:** Non-matching roles go to /unauthorized (not /login) — correct UX distinction between "not authenticated" and "not authorized"
- **AdminNavLink as UX-only:** Renders conditionally on client role state; AUTH-07 (backend enforcement) proven independently via curl-bypass step in checkpoint
- **Defense-in-depth documented:** T-04-01 mitigation verified — client guard (UX) + backend require_role (authority) are two separate layers

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed DashboardPage Manage Users href and replaced `<a>` with `<Link>`**
- **Found during:** Task 1 — AdminNavLink integration into DashboardPage TopNav
- **Issue:** DashboardPage.tsx had `<a href="/admin/users">Manage Users</a>` — wrong path (should be `/admin/users/new`) and used a bare `<a>` instead of React Router `<Link>` (causes full page reload, losing in-memory access token)
- **Fix:** Updated href to `/admin/users/new` and replaced `<a>` with `<Link to="/admin/users/new">` from react-router-dom
- **Files modified:** frontend/src/pages/DashboardPage.tsx
- **Verification:** npm run build clean; navigation to /admin/users/new confirmed working in human checkpoint
- **Committed in:** c98c252 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — Bug)
**Impact on plan:** Fix required for correct in-memory token preservation during admin navigation. No scope creep.

## Threat Surface Scan

All threat mitigations from plan's threat model applied:
- T-04-01: Backend require_role('admin_librarian') on POST /admin/users verified via curl-bypass → HTTP 403 (AUTH-07 confirmed)
- T-04-02: AdminNavLink and ProtectedRoute documented as UX-only; authorization decided server-side — CM-7 pattern maintained
- T-04-03: 409 "already exists" accepted for admin-only authenticated endpoint — admins are trusted operators
- T-04-SC: No new packages added; all packages from plan 03's audited set

No new threat surface beyond the plan's threat model.

## Known Stubs

None — CreateLibrarianPage posts to live POST /admin/users (from plan 01-02). All data flows wired to real backend. No hardcoded data or placeholder text.

## Phase 1 Completion

All five Foundation phase success criteria are now demonstrably TRUE:

1. A new student can register with email and password and immediately log in without admin intervention. (AUTH-01/AUTH-02 — plan 01-03)
2. A logged-in user stays logged in across browser refreshes without re-entering credentials. (AUTH-03 — httpOnly refresh cookie + in-memory token — plan 01-03)
3. A user who logs out cannot access protected pages until they log in again, and their session is invalidated server-side. (AUTH-04 — refresh_token_blocklist — plan 01-02)
4. The seeded admin librarian account can log in and create a new librarian account from the admin UI. (AUTH-05/AUTH-06 — plans 01-01/01-02/01-04)
5. Calling any librarian or admin endpoint as a student returns 403 Forbidden. (AUTH-07 — backend require_role — plans 01-02/01-04)

## Next Phase Readiness

- Phase 1 (Foundation) is **COMPLETE** — all AUTH-01 through AUTH-07 requirements delivered and verified
- Phase 2 (Book Catalog) can begin: full auth stack (register/login/refresh/logout/RBAC) operational; frontend scaffold ready
- Admin librarian account is seeded, can create librarian accounts, and all role-based route guards are in place
- No blockers for Phase 2

## Self-Check

**Files verified present on disk:**
- frontend/src/pages/CreateLibrarianPage.tsx: checked via git show c98c252 — FOUND
- frontend/src/components/AdminNavLink.tsx: checked via git show c98c252 — FOUND
- frontend/src/App.tsx (modified): checked via git show c98c252 — FOUND
- frontend/src/pages/DashboardPage.tsx (modified): checked via git show c98c252 — FOUND

**Task commit verified in git log:**
- `c98c252` feat(01-04): Create Librarian + Unauthorized screens, admin nav link, route guarding — FOUND

**Human checkpoint:** Approved by user — all 5 verification steps confirmed passing.

## Self-Check: PASSED

---
*Phase: 01-foundation*
*Completed: 2026-06-11*
