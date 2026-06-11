---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 02
current_plan: 1
status: Phase 01 Complete — Ready for Phase 02
last_updated: "2026-06-11T05:49:36Z"
progress:
  total_phases: 5
  completed_phases: 1
  total_plans: 4
  completed_plans: 4
  percent: 20
---

# State: University Library Management System

**Last updated:** 2026-06-11
**Session:** Plan 01-04 complete — Phase 1 Foundation fully delivered

---

## Project Reference

**Core value:** A student can find a book, request to borrow it, and track when it's due — and a librarian can process that request and manage the full borrow lifecycle end-to-end.

**Stack:** FastAPI (Python 3.12) + React 18 (TypeScript) + PostgreSQL 16 + Docker Compose

**Roles:** Student (self-register), Librarian (created by admin), Admin Librarian (seeded via migration)

---

## Current Position

Phase: 01 (foundation) — COMPLETE
Phase: 02 (book-catalog) — NEXT
**Milestone:** v1 — MVP
**Current phase:** 02
**Current plan:** 1
**Phase status:** Phase 01 complete; Phase 02 not started

```
Progress: [##        ] 20%
Phases complete: 1/5
```

---

## Phase Summary

| Phase | Name | Requirements | Status |
|-------|------|--------------|--------|
| 1 | Foundation | AUTH-01 – AUTH-07 (7) | Complete |
| 2 | Book Catalog | CAT-01 – CAT-08 (8) | Not started |
| 3 | Borrow Lifecycle | BORROW-01 – BORROW-07, LOAN-01 (8) | Not started |
| 4 | Loan Views & History | LOAN-02 – LOAN-05 (4) | Not started |
| 5 | Notifications & Overdue Detection | OVERDUE-01 – OVERDUE-04 (4) | Not started |

---

## Accumulated Context

### Key Decisions Logged

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Auth token strategy | httpOnly refresh token cookie + in-memory access token | Avoids localStorage XSS risk; session survives page refresh |
| RBAC enforcement | FastAPI dependency injection (require_role) | Backend-enforced, not frontend-only; prevents curl bypass |
| Copy tracking | Count fields (total_copies, available_copies) on books table | Per-copy rows not needed for single-location library |
| Concurrency safety | SELECT FOR UPDATE inside approval transaction + CHECK (available_copies >= 0) | Prevents negative copy count under concurrent approvals |
| Email background | BackgroundTasks for approval/rejection; APScheduler for overdue | No broker (Celery/Redis) needed for v1 |
| Search | PostgreSQL GIN full-text index on title + author | No Elasticsearch needed |
| Dev SMTP | MailHog | Zero-config; no real email sent during development |
| Admin librarian bootstrap | Alembic migration seed (credentials from env vars) | No one-time endpoint or CLI command needed |
| Loan period | 14 days hardcoded constant | Fixed per PROJECT.md; no settings toggle in v1 |
| Book delete safety | ON DELETE RESTRICT / blocked if active loans exist | Database is the final authority; prevents orphaned loan records |

### Critical Pitfalls to Avoid

- **CP-1 Concurrent approval race:** Use SELECT FOR UPDATE + CHECK constraint — two simultaneous approvals must not drive available_copies negative.
- **CP-2 Async session scope:** Per-request get_db() dependency using async_sessionmaker — never a module-level AsyncSession.
- **CP-3 JWT invalidation:** Short access token expiry (15-60 min), httpOnly refresh cookie, refresh_token_blocklist table.
- **CP-4 Alembic drift:** Run alembic upgrade head in container entrypoint; Alembic owns the schema from day one.
- **CM-7 Frontend-only role check:** Every mutation endpoint uses require_role FastAPI dependency.

### Open Questions (to resolve before implementation)

| Question | Must Resolve By |
|----------|----------------|
| Production email provider (MailHog is dev only) | Before Phase 5 |
| APScheduler multi-instance risk (overdue job fires multiple times if replicated) | Before Phase 5; single replica acceptable for v1 — document constraint |
| Cover image placeholder for books where Open Library has no cover | Before Phase 2 |

### Decisions Pending (from research open questions)

| Question | Status |
|----------|--------|
| JWT: in-memory vs httpOnly cookie vs localStorage | Resolved: in-memory access token + httpOnly refresh cookie (AUTH-03) |
| Refresh token vs single access token | Resolved: httpOnly refresh token + short-lived in-memory access token |
| Soft delete vs hard delete for books | Resolved: hard delete blocked by ON DELETE RESTRICT (CAT-04) |
| Loan period as hardcoded constant | Resolved: yes, code constant per PROJECT.md |

---

## Blockers

None.

---

## Session Continuity

**Next action:** Begin Phase 2 — Book Catalog (CAT-01 through CAT-08). Phase 1 Foundation is fully complete.

**Context for next session:**

- Phase 1 complete: all 4 plans (01-01 through 01-04) executed and verified
- Full auth stack operational: register, login, refresh, logout, RBAC (AUTH-01 through AUTH-07)
- Frontend scaffold complete: Vite+React18+TS+Tailwind3+shadcn, AuthContext, axios interceptors, routing, Login/Register/Dashboard/CreateLibrarian/Unauthorized screens
- Backend: FastAPI + SQLAlchemy async + asyncpg + Alembic migration with full 5-phase schema + seeded admin
- Docker Compose: all services operational (FastAPI, PostgreSQL, frontend, MailHog)
- Phase 2 goal: Librarians manage books; students browse and find them (CAT-01 through CAT-08)

---
*State initialized: 2026-06-10*

## Performance Metrics

| Phase | Plan | Duration | Notes |
|-------|------|----------|-------|
| Phase 01-foundation P01 | 9min | 3 tasks | 23 files |
| Phase 01-foundation P02 | 23min | 2 tasks | 14 files |
| Phase 01-foundation P03 | 13min | 2 tasks (task 3 awaiting checkpoint) | 32 files |
| Phase 01-foundation P04 | 15min | 2 tasks (task 2 = human checkpoint) | 4 files |

## Decisions

- [Phase 01-foundation]: Single Alembic migration 001_initial_schema creates complete 5-phase schema (D-01, D-02)
- [Phase 01-foundation]: Alembic async template (async_engine_from_config) mandatory for asyncpg — sync template hangs
- [Phase 01-foundation]: VARCHAR+CHECK constraints for role/status (not native ENUM) — easier to extend without ALTER TYPE
- [Phase 01-foundation]: DB URL read from os.environ in alembic env.py — never embedded in alembic.ini (T-01-01)
- [Phase 01-foundation]: algorithms=["HS256"] in all jwt.decode calls (T-02-01 algorithm confusion defense)
- [Phase 01-foundation]: Blocklist-only refresh token design: only blocked tokens in table — simpler D-04 implementation
- [Phase 01-foundation]: Cookie path=/auth scopes refresh_token cookie to /auth/* endpoints only (Pitfall 5)
- [Phase 01-foundation]: DUMMY_HASH timing-safe authenticate_user prevents email enumeration via response latency (T-02-06)
- [Phase 01-foundation]: shadcn@2 (not @latest): shadcn v4 requires Tailwind v4; Tailwind v3 pins require shadcn v2
- [Phase 01-foundation]: In-memory access token in React Context + module-level setter for axios interceptors (D-08, T-03-01)
- [Phase 01-foundation]: AUTH-03 bootstrap: App.tsx useEffect POSTs /auth/refresh before rendering routes
- [Phase 01-foundation]: ProtectedRoute allowedRoles redirect target is /unauthorized (not /login) — "not authorized" vs "not authenticated" UX distinction
- [Phase 01-foundation]: AdminNavLink is UX-only; AUTH-07 backend require_role('admin_librarian') is the authority (CM-7, D-09)
