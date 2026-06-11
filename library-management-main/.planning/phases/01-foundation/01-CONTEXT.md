# Phase 1: Foundation - Context

**Gathered:** 2026-06-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 1 delivers: authenticated access with role enforcement, plus the **complete database schema for all 5 phases** laid down from day one.

By the end of Phase 1:
- A student can register, log in, stay logged in across page refreshes, and log out (session invalidated server-side).
- An admin librarian can log in and create new librarian accounts.
- Every backend endpoint enforces role-based access (student / librarian / admin-librarian) — not just frontend routing.
- The full PostgreSQL schema (all tables, constraints, indexes) is in place and managed by Alembic.

Later phases (2–5) add data, endpoints, and UI — they do NOT modify the schema.

</domain>

<decisions>
## Implementation Decisions

### Database Schema

- **D-01:** Phase 1 creates ALL tables for all 5 phases in a single Alembic migration — `001_initial_schema.py`. This covers: `users`, `refresh_token_blocklist`, `books`, `borrow_requests`, `loans`. No table additions in later phases.
- **D-02:** Single migration file — one `001_initial_schema.py` with all tables, FKs, constraints, and indexes in dependency order. Not split per domain.
- **D-03:** `users` table includes `full_name` (in addition to `email`, `password_hash`, `role`). This is required for Phase 4's "search loans by student name" feature; capturing it at registration is the correct place.
- **D-04:** `refresh_token_blocklist` table created in Phase 1 migration. AUTH-04 requires server-side token invalidation on logout; the table must exist before any auth endpoint goes live.
- **D-05:** Status fields use **VARCHAR + CHECK constraints** (not PostgreSQL native ENUMs). `borrow_requests.status` CHECK IN ('pending','approved','rejected'); `loans.status` CHECK IN ('active','returned','overdue'). Easier to extend without ALTER TYPE migrations.
- **D-06:** `loans` table includes `overdue_notified_at TIMESTAMPTZ` (nullable). NULL = not yet notified; timestamp = first overdue email sent. APScheduler job: mark loans overdue WHERE `overdue_notified_at IS NULL` → send email → set timestamp. Satisfies OVERDUE-02 "exactly one email" requirement idempotently.
- **D-07:** Essential indexes created in Phase 1 migration:
  - `UNIQUE` on `users.email`
  - `UNIQUE` on `books.isbn`
  - Index on `loans.due_date` (for nightly overdue job)
  - Index on `borrow_requests.status` (for pending queue query)
  - GIN full-text index on `books` (`to_tsvector('english', title || ' ' || author)`) for catalog search (CAT-05)
  
  Speculative tuning indexes are deferred to when queries prove slow.

### Authentication (Carried Forward from Prior Context)

- **D-08:** Token strategy: short-lived in-memory access token + httpOnly refresh cookie. No localStorage (XSS risk). Refresh token survival across page reloads is via the httpOnly cookie only.
- **D-09:** RBAC enforcement via FastAPI `require_role` dependency injection on every protected endpoint. Frontend routing is for UX only — backend is the authority.
- **D-10:** Admin librarian seeded via Alembic migration using credentials from environment variables (`ADMIN_EMAIL`, `ADMIN_PASSWORD`). No one-time endpoint or CLI command.

### Claude's Discretion

- Specific index naming convention (e.g., `ix_loans_due_date` vs. `loans_due_date_idx`) — use SQLAlchemy/Alembic conventions.
- Password column name (`password_hash` vs `hashed_password`) — follow FastAPI docs convention.
- Exact `role` column implementation (VARCHAR CHECK IN ('student','librarian','admin_librarian') vs. separate roles table) — use VARCHAR CHECK for simplicity at this scale.
- React in-memory token store implementation detail (React Context vs. module-level variable) — either is acceptable; Context is preferred for testability.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements & Roadmap
- `.planning/ROADMAP.md` — Phase 1 goal, requirements (AUTH-01–AUTH-07), and success criteria
- `.planning/REQUIREMENTS.md` — Full requirement specifications for AUTH-01 through AUTH-07
- `.planning/PROJECT.md` — Stack decisions, constraints, and what NOT to use (especially auth section)

### Architecture Decisions & Pitfalls
- `.planning/STATE.md` — Key decisions already logged (token strategy, RBAC pattern, concurrency pitfalls CP-1 through CP-4, CM-7); MUST read before planning auth and schema
- `CLAUDE.md` (project root) — Tech stack versions, rationale for PyJWT over python-jose, pwdlib[argon2] over passlib, rejected patterns (JWT in localStorage, allow_origins=["*"])

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — codebase is a blank slate. Phase 1 establishes all foundational patterns.

### Established Patterns
- None yet — Phase 1 defines the patterns that all later phases follow.

### Integration Points
- Phases 2–5 build on Phase 1's `users` table (FK for created_by, student ownership of loans).
- Phase 1's `require_role` dependency is imported by every protected endpoint in Phases 2–5.
- Phase 1's Alembic `001_initial_schema.py` is the single source of truth for schema — later phases never add migrations for tables.
- Phase 1's Docker Compose dev environment (FastAPI + React + PostgreSQL + MailHog) is the dev stack for all subsequent phases.

</code_context>

<specifics>
## Specific Ideas

- The roadmap explicitly states "full database schema with all constraints is in place from day one" — this is a hard requirement, not a preference. All tables must exist after Phase 1.
- MailHog as dev SMTP sink (from STATE.md) — zero real emails sent during development; capture all outbound email for inspection.
- `available_copies` column on `books` table with `CHECK (available_copies >= 0)` and `CHECK (available_copies <= total_copies)` constraints — critical correctness requirement from STATE.md CP-1.
- `SELECT FOR UPDATE` pattern for concurrent approval transactions (Phase 3 concern, but the schema constraints that enforce it must be present from Phase 1).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Foundation*
*Context gathered: 2026-06-10*
