# Research Summary - University Library Management System

**Synthesized:** 2026-06-10
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md
**Overall Confidence:** HIGH

---

## Recommended Stack

- **Backend:** Python 3.12 + FastAPI 0.115 + SQLAlchemy 2.0 async + asyncpg + Alembic. Use PyJWT 2.8 (not python-jose, CVEs) and pwdlib[argon2] (not passlib, unmaintained). SQLAlchemy async preferred over SQLModel.
- **Database:** PostgreSQL 16 with GIN full-text indexes on book title/author. No Elasticsearch needed. CHECK constraints and SELECT FOR UPDATE enforce DB integrity.
- **Frontend:** React 18 + Vite 5 + TypeScript 5. TanStack Query v5, shadcn/ui + Tailwind 3, React Hook Form + Zod, Axios with JWT interceptors.
- **Email/Scheduling:** fastapi-mail + BackgroundTasks for approval/rejection emails; APScheduler for nightly overdue detection. No Celery or Redis for v1.
- **Infrastructure:** Docker Compose with postgres:16-alpine, python:3.12-slim, node:20-alpine, mailhog/mailhog as dev SMTP sink, nginx:alpine in production.

---
## Table Stakes Features

- **Catalog search** with keyword matching on title, author, ISBN, category with available-copy badge on every result card.
- **Book detail page** with metadata, cover, availability, Request to Borrow button (disabled when 0 copies available).
- **Borrow request submission** by students with duplicate-prevention (one pending request per book per student).
- **Request status visibility** for students (pending / approved / rejected).
- **Active loans list** with due dates and explicit overdue visual indicator (not just email).
- **Librarian pending requests queue** with inline Approve / Reject actions.
- **Approve / reject workflow** atomically decrements/preserves available_copies and creates/skips a loan record.
- **Record return** atomically increments available_copies.
- **Overdue dashboard for librarian** sorted by most-days-overdue-first.
- **Catalog CRUD** for librarians (add, edit, delete books).
- **Email notifications** on approve, reject, and overdue (async via BackgroundTasks / APScheduler).
- **Role-based access** with role checked on the backend, not only the frontend.
- **Session persistence** since re-login on every visit is a hard adoption blocker.

---

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| System structure | Modular monolith | Shared DB transaction for approve+decrement is trivial in a monolith |
| RBAC enforcement | FastAPI dependency injection (require_role) | Co-located with endpoints, composable, testable |
| Copy tracking | Count fields (total_copies, available_copies) on books table | Per-copy rows not needed |
| Concurrency safety | SELECT FOR UPDATE on book row inside approval transaction | Prevents over-allocation |
| Auth token | JWT with role in payload; 60 min student / 8 hr librarian expiry | No DB round-trip per request |
| Email background | FastAPI BackgroundTasks for approval/rejection; APScheduler for overdue | No broker needed |
| Search | PostgreSQL GIN full-text on title + author | No Elasticsearch needed |
| Dev email | MailHog SMTP sink | Zero-config, no real email sent |
| DB integrity | CHECK constraints + UNIQUE on loans.borrow_request_id + ON DELETE RESTRICT | Database is the final authority |
| Loan state transitions | Enforced in service method reading current state before writing | Prevents double-decrement |
| Frontend state | TanStack Query with invalidateQueries after every mutation | Server is source of truth |
| Frontend routing guard | ProtectedRoute, LibrarianRoute, AdminLibrarianRoute components | Role from AuthContext |

---

## Critical Pitfalls to Avoid

1. **Concurrent borrow approval race (CP-1):** Two librarians approve the last copy simultaneously, driving available_copies negative. Prevention: SELECT FOR UPDATE inside every approval transaction + CHECK (available_copies >= 0) DB constraint.

2. **SQLAlchemy async session shared across requests (CP-2):** Module-level AsyncSession causes MissingGreenlet and cross-request data bleed. Prevention: per-request get_db() dependency using async_sessionmaker with expire_on_commit=False.

3. **JWT tokens with no expiry or server-side invalidation (CP-3):** Stolen tokens grant indefinite access. Prevention: short expiry (15-60 min), httpOnly refresh token cookie, refresh_token_blocklist table, is_active check on refresh.

4. **Alembic migration drift (CP-4):** Model changes without migrations cause silent dev/prod divergence. Prevention: Alembic owns the schema from day one; run alembic upgrade head in container entrypoint.

5. **Role enforcement only on the frontend (CM-7):** Students can call librarian endpoints via curl if no backend check. Prevention: every mutation endpoint must use require_role as a FastAPI dependency.

---

## Open Questions

| Question | Source | Notes |
|----------|--------|-------|
| JWT storage: in-memory vs httpOnly cookie vs localStorage | STACK.md, PITFALLS.md CP-3 | localStorage is XSS-vulnerable. In-memory simplest for v1. Decide before Phase 1 auth. |
| Refresh token vs single access token for v1 | STACK.md, ARCHITECTURE.md | ARCHITECTURE.md recommends no refresh token. PITFALLS.md recommends one. Decide explicitly. |
| Email provider for production | STACK.md | MailHog for dev settled. Production needs real SMTP or transactional service. Must be known before Phase 3. |
| APScheduler multi-instance risk | STACK.md | Multiple replicas fire overdue job multiple times. Single replica acceptable for v1 - document constraint. |
| Cover image strategy for v1 | FEATURES.md | URL field, omit covers, or auto-fetch via Open Library ISBN? Decide what a missing cover placeholder looks like. |
| admin_librarian bootstrap | ARCHITECTURE.md | First admin_librarian cannot self-register. Decide: DB migration seed, CLI command, or one-time endpoint. |
| Soft delete vs hard delete for books | ARCHITECTURE.md | ON DELETE RESTRICT prevents deleting books with active loans. Hard delete acceptable once resolved? |
| Loan period as hardcoded constant | FEATURES.md | PROJECT.md sets 14 days fixed. Confirm this is a code constant, not a settings toggle. |

---

## Build Order Recommendation

### Phase 1 - Foundation (Auth + Dev Environment + DB Schema)

Deliver: working login/register with role routing; all DB tables and constraints in place; dev environment operational.

- Docker Compose: PostgreSQL 16, FastAPI backend, React frontend (Vite), MailHog
- Alembic schema: users, books, borrow_requests, loans with all CHECK constraints, FK constraints, GIN indexes from day one
- Auth module: register, login, JWT with role in payload, require_role dependency
- Pydantic response schemas for all models (never return ORM objects directly)
- CORS configured via ALLOWED_ORIGINS environment variable
- Key pitfalls: CP-2 (session scope), CP-3 (token expiry), CP-4 (migration drift), CM-4 (hot reload), CM-7 (backend role check)

### Phase 2 - Core Catalog + Borrow Flow

Deliver: end-to-end flow from student searching a book to librarian approving and recording return.

- Book catalog CRUD (librarian) + full-text search with pagination
- Student catalog browse + book detail page with availability badge
- Borrow request submission with duplicate-prevention
- Librarian pending requests queue with inline Approve / Reject
- Approve: SELECT FOR UPDATE + atomic copy decrement + loan creation (due = now + 14 days)
- Reject: status update + notes field
- Record return: atomic copy increment
- Student active loans view with due date and overdue visual indicator
- Key pitfalls: CP-1 (concurrent approval race), CP-5 (loan state machine), CM-3 (stale React state), CM-5 (missing indexes)

### Phase 3 - Notifications + Overdue Detection

Deliver: fully async email notifications and automated overdue flagging with librarian dashboard.

- Email on approval and rejection via FastAPI BackgroundTasks + fastapi-mail
- APScheduler nightly overdue job: mark is_overdue, set overdue_notified_at, send email alert
- Student overdue indicator driven by is_overdue flag (not computed on read)
- Librarian overdue dashboard sorted by most-days-overdue-first
- Key pitfalls: CM-2 (blocking SMTP), MG-7 (overdue detection must run in scheduler not on read path)

### Phase 4 - Polish + Secondary Features (post-MVP)

Deliver: differentiating features that improve UX and reduce librarian workload.

- Pagination and sorting on all list views
- Advanced catalog filters (genre multi-select, availability toggle)
- Borrow history for students (all past loans)
- Librarian search across loans by student name or book title
- Admin librarian user management UI (create / deactivate librarian accounts)
- Cover image auto-fetch via Open Library ISBN API
- Catalog statistics dashboard (most borrowed titles, overdue rate)

---

## Research Flags

| Phase | Needs Deep Research? | Reason |
|-------|---------------------|--------|
| Phase 1 | No | Auth + Docker patterns are canonical and well-documented |
| Phase 2 | No | REST CRUD + PostgreSQL GIN search are standard patterns |
| Phase 3 | Possibly | APScheduler with FastAPI lifespan events has nuance; fastapi-mail 1.4.x async config should be verified |
| Phase 4 | Yes (ISBN API) | Open Library / Google Books API rate limits and reliability need validation |
