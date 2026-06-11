# Walking Skeleton — University Library Management System

**Phase:** 1
**Generated:** 2026-06-11

## Phase Goal (User Story)

**As a** university user (student or admin librarian), **I want to** register, log in, stay logged in across refreshes, and reach a role-appropriate view, **so that** I have authenticated, role-enforced access to the library system.

> Note: the ROADMAP `**Goal:**` line for Phase 1 is in prose form, not the canonical
> "As a / I want to / so that" user-story format. The three slots (actor, capability, outcome)
> are unambiguously derivable from the ROADMAP goal, the CONTEXT decisions, and the five
> success criteria, so this story was derived rather than blocking the plan. Consider running
> `/gsd mvp-phase 1` if you want the ROADMAP line rewritten to the canonical format.

## Capability Proven End-to-End

A new student can register, log in, refresh the page without losing their session, and see a role-appropriate dashboard served by the deployed Docker Compose stack; the seeded admin can create a librarian who can then log in — exercising frontend → API → DB read AND write, with backend-enforced RBAC.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI 0.115.x (Python 3.12, async) | Fixed constraint (CLAUDE.md); ASGI-native, auto OpenAPI |
| ORM / data layer | SQLAlchemy 2.0 async + asyncpg | Only async-capable ORM with Alembic support (D-research); per-request async_sessionmaker, never module-level session (CP-2) |
| Migrations | Alembic (async env.py template) | Single `001_initial_schema.py` holds the COMPLETE 5-phase schema (D-01, D-02); later phases never add tables |
| Database | PostgreSQL 16 | Fixed constraint; GIN full-text index for catalog search reserved from day one (D-07) |
| Auth | Custom email/password; PyJWT (HS256) access token + pwdlib[argon2] hashing | PyJWT over python-jose (CVEs); pwdlib over passlib (unmaintained) — CLAUDE.md |
| Session/token storage | In-memory access token (React Context) + httpOnly SameSite=Lax refresh cookie; server-side blocklist on logout | D-08 / D-04; never localStorage (XSS) |
| RBAC | FastAPI `require_role` dependency on every protected endpoint | D-09 / CM-7; backend is the authority, client routing is UX only |
| Admin bootstrap | Alembic migration seed from ADMIN_EMAIL / ADMIN_PASSWORD env vars | D-10; no one-time endpoint or CLI |
| Frontend | React 18 + TypeScript + Vite 5 | Fixed; CRA deprecated, Next.js overkill for a FastAPI-backed SPA |
| UI system | shadcn/ui (New York, Neutral) + Tailwind v3 | CLAUDE.md; Tailwind pinned to v3 BEFORE shadcn init (Pitfall 7) |
| Server state | TanStack Query v5 + Axios (interceptors) | CLAUDE.md; axios for JWT injection + 401 auto-refresh |
| Deployment target | Docker Compose dev stack (db + backend + frontend + mailhog) | Fixed; `docker compose up` is the documented full-stack run command |
| Directory layout | `backend/app/{models,schemas,services,routers,dependencies}` + `frontend/src/{context,lib,components,pages,hooks}` | RESEARCH.md Recommended Project Structure |

## Stack Touched in Phase 1

- [x] Project scaffold (FastAPI app, Vite/React app, build, lint, pytest + vitest-ready)
- [x] Routing — backend `/auth/*` + `/admin/*`; frontend React Router (/login, /register, /dashboard, /admin/users/new, /unauthorized)
- [x] Database — real read AND write: admin seed write (migration) + register/login reads/writes; full schema created
- [x] UI — interactive register/login forms wired to the live API; dashboard + create-librarian
- [x] Deployment — running on the Docker Compose dev stack via `docker compose up` (documented full-stack run)

## Out of Scope (Deferred to Later Slices)

- Book catalog CRUD, Open Library cover fetch, search/pagination (Phase 2 — tables exist but no endpoints/UI)
- Borrow request submission, approval/rejection, returns, copy-count accounting (Phase 3)
- Loan views, history, librarian loan search (Phase 4)
- Overdue detection (APScheduler), overdue emails, overdue dashboard (Phase 5)
- Rate limiting on login (brute-force) — accepted out of scope for v1
- Production email provider (MailHog is dev-only); dark mode; password reset; email verification

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton WITHOUT altering its architectural decisions or schema:

- Phase 2: Librarians manage books; students browse, search, and view book details with live availability.
- Phase 3: Students request books; librarians approve/reject and record returns with atomic copy accounting.
- Phase 4: Students track active loans and history; librarians search across all loans.
- Phase 5: Nightly overdue detection + one-time overdue emails + librarian overdue dashboard.
