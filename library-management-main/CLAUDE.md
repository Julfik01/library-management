<!-- GSD:project-start source:PROJECT.md -->

## Project

**University Library Management System**

A web-based library management system for a university. Students can search the book catalog, submit borrow requests, and track their borrowed items and due dates. Librarians can manage the catalog, approve or reject borrow requests, record returns, and monitor overdue items through a dashboard.

**Core Value:** A student can find a book, request to borrow it, and track when it's due — and a librarian can process that request and manage the full borrow lifecycle end-to-end.

### Constraints

- **Tech Stack**: FastAPI + React + PostgreSQL + Docker — decided, no alternatives considered
- **Auth**: Custom email/password with JWT — no SSO integration for v1
- **Borrow Period**: Fixed 14 days — no configurable loan periods in v1
- **Scope**: University context — no public or multi-institution access

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Recommended Stack (with versions)

### Backend — FastAPI Layer

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| Python | 3.12 | Runtime | LTS-stable, full `asyncio` support, widespread Docker image availability |
| FastAPI | 0.115.x | Web framework | Fixed constraint; ASGI-native, auto-generates OpenAPI docs |
| Uvicorn | 0.30.x | ASGI server | Standard FastAPI server; use `uvicorn[standard]` for watchfiles/websocket support |
| Pydantic | v2.x | Validation/serialization | FastAPI 0.100+ requires Pydantic v2; significantly faster than v1 |
| SQLAlchemy | 2.0.x | ORM | Industry standard; v2 has stable async support via `AsyncSession`; more control than SQLModel for complex queries |
| asyncpg | 0.29.x | Async PostgreSQL driver | Required by SQLAlchemy async engine; fastest Python PostgreSQL driver |
| Alembic | 1.13.x | Database migrations | Standard SQLAlchemy migration tool; handles schema versioning across environments |
| PyJWT | 2.8.x | JWT encode/decode | Officially recommended by FastAPI docs (replaced python-jose recommendation); actively maintained |
| pwdlib[argon2] | 0.2.x | Password hashing | FastAPI docs now recommend this over passlib; Argon2 is the modern preferred hashing algorithm |
| python-multipart | 0.0.9 | Form data parsing | Required for OAuth2 password form and file uploads |
| fastapi-mail | 1.4.x | Email sending | Async-native email library built specifically for FastAPI; wraps aiosmtplib |

### Database Layer

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| PostgreSQL | 16 | Primary database | Fixed constraint; stable LTS version with excellent async driver support |
| asyncpg | 0.29.x | Driver | Fastest async PostgreSQL driver; used by SQLAlchemy async engine |
| Redis | 7.x | Background task queue (optional) | Only needed if email sending moves to ARQ; not required for BackgroundTasks approach |

### Frontend — React Layer

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| Node.js | 20 LTS | Runtime | LTS stable for Docker build environments |
| React | 18.x | UI framework | Fixed constraint; concurrent features, stable ecosystem |
| Vite | 5.x | Build tool / dev server | Fastest DX for React SPAs; CRA is deprecated; Next.js is overkill for a backend-API-driven SPA |
| TypeScript | 5.x | Type safety | Strongly recommended for a multi-role app; catches auth/role bugs at compile time |
| TanStack Query (React Query) | v5 | Server state / data fetching | Best-in-class for async CRUD data from a REST API; handles caching, loading states, refetching |
| React Router | v6.x | Client-side routing | Standard SPA router; v6 is stable with nested routes and loader support |
| React Hook Form | 7.x | Form management | Minimal re-renders; integrates cleanly with Zod validation |
| Zod | 3.x | Schema validation | Pairs with React Hook Form; can share schemas between frontend and Pydantic models conceptually |
| shadcn/ui | latest (2025) | UI component library | Copy-paste component model (no versioned lock-in); built on Radix UI + Tailwind; excellent DX |
| Tailwind CSS | 3.x | Utility CSS | Required by shadcn/ui; fast to build admin dashboards |
| Axios | 1.x | HTTP client | Alternative: TanStack Query with fetch; Axios preferred for interceptors (JWT token injection) |

### Infrastructure & Dev

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| Docker | 24.x | Containerization | Fixed constraint |
| Docker Compose | v2.x | Multi-service orchestration | Backend + Frontend + PostgreSQL + optional Redis in single `compose.yml` |
| python:3.12-slim | — | Backend Docker image | Official slim image; smaller than full; avoids deprecated `tiangolo/uvicorn-gunicorn-fastapi` |
| node:20-alpine | — | Frontend build image | Alpine-based for smaller production images |
| nginx:alpine | — | Frontend static server | Serves the React build in production; handles SPA routing with `try_files` |

### Testing

| Technology | Version | Purpose | Rationale |
|------------|---------|---------|-----------|
| pytest | 8.x | Backend test runner | Standard Python; FastAPI officially recommends it |
| pytest-asyncio | 0.23.x | Async test support | Required for testing async route handlers and DB operations |
| httpx | 0.27.x | HTTP test client | FastAPI's `TestClient` is built on httpx; also used for async integration tests |
| factory-boy | 3.x | Test fixtures | Clean way to generate model instances for tests |
| Vitest | 1.x | Frontend test runner | Vite-native; Jest-compatible API; much faster than Jest for Vite projects |
| React Testing Library | 14.x | Component testing | Standard React component testing; queries by accessibility role |

## Key Choices & Rationale

### ORM: SQLAlchemy 2.0 (async) over SQLModel

### Async vs Sync in FastAPI Routes

- The database layer uses `AsyncSession` with `asyncpg` (async-native)
- Email sending via `fastapi-mail` is async
- `async def` handlers run directly on the event loop without thread pool overhead

### JWT: PyJWT over python-jose

### Password Hashing: pwdlib[argon2] over passlib

### Email: FastAPI BackgroundTasks + fastapi-mail over Celery

- **APScheduler** (add to the FastAPI process) — simplest, no Redis needed, sufficient for this scale
- **Celery + Redis** — correct for high scale, overkill for a university library
- **ARQ + Redis** — async-native, lighter than Celery, but adds Redis dependency

### React Build Tool: Vite over CRA / Next.js

- **Create React App (CRA) is officially deprecated** as of 2023. It is unmaintained.
- **Next.js** is the React team's primary 2025 recommendation, but it is a full-stack SSR framework. This project already has a FastAPI backend — adding Next.js would duplicate routing, introduce SSR complexity, and provide no benefit for what is essentially a data-fetching SPA.
- **Vite** is the correct tool: it is a pure build tool / dev server for SPAs. Sub-second HMR, official React plugin, TypeScript first-class, standard in 2025 for API-backed SPAs.

### Frontend State: TanStack Query over Redux / Zustand

### UI Library: shadcn/ui over MUI / Ant Design

| Criterion | shadcn/ui | MUI | Ant Design |
|-----------|-----------|-----|------------|
| Bundle size | Minimal (copy-paste, tree-shaken) | Large (theme system) | Large |
| Customization | Full (you own the code) | Moderate (sx prop) | Limited |
| Admin dashboard suitability | Excellent | Excellent | Excellent |
| Tailwind integration | Native | Friction | Friction |
| Learning curve | Low | Medium | Medium |
| Design aesthetic | Clean, modern | Material Design | Ant/Chinese enterprise |

## What NOT to Use & Why

| Rejected Choice | Category | Why Rejected |
|-----------------|----------|-------------|
| `python-jose` | JWT | Has unresolved CVEs; FastAPI docs moved away from it; less actively maintained than PyJWT |
| `passlib[bcrypt]` | Password hashing | Largely unmaintained since 2023; replaced by `pwdlib` in FastAPI's own docs |
| `SQLModel` for async | ORM | Async support lags SQLAlchemy 2.0; creates friction with Alembic; dual-purpose model creates schema divergence issues at scale |
| `Tortoise ORM` | ORM | Django-influenced async ORM; smaller ecosystem; Alembic does not support it (uses Aerich instead); no benefit over SQLAlchemy |
| `Create React App (CRA)` | Build tool | Officially deprecated and unmaintained since 2023 |
| `Next.js` | Frontend framework | SSR framework overkill for a FastAPI-backed SPA; introduces duplicate routing concerns |
| `Redux Toolkit` | State management | No complex client state in this app; TanStack Query handles server state; Redux is pure overhead |
| `MUI (Material UI)` | UI components | Heavier bundle; Material Design aesthetic is dated; requires fighting the theme system to match custom designs; Tailwind integration is friction |
| `Ant Design` | UI components | Enterprise-Chinese aesthetic; heavy; poor Tailwind compatibility |
| `Celery` | Task queue | Requires Redis + Celery workers in Docker Compose; overkill for 2 email trigger points in a university-scale app; APScheduler covers the need in-process |
| `tiangolo/uvicorn-gunicorn-fastapi` | Docker image | Explicitly deprecated by FastAPI's own deployment docs; use `python:3.12-slim` directly |
| `Sync SQLAlchemy` | DB pattern | Blocks the ASGI event loop inside async route handlers; negates FastAPI's async benefits |
| `JWT in localStorage` | Auth storage | XSS-vulnerable; use `httpOnly` cookie or in-memory + short-lived access token pattern instead |
| `allow_origins=["*"]` with credentials | CORS | Browsers block this combination; must specify explicit origins when `allow_credentials=True` |

## Project Structure (Backend)

## Docker Compose Structure (Dev)

# compose.yml (dev)

## Installation Summary

### Backend (requirements.txt)

### Backend Dev Dependencies

### Frontend (package.json key deps)

## Confidence Levels

| Area | Confidence | Reasoning |
|------|------------|-----------|
| FastAPI project structure | HIGH | Verified against official FastAPI docs; feature-router pattern is canonical |
| SQLAlchemy 2.0 async | HIGH | Stable since 2022; asyncpg combination is well-established in production; official docs cover it |
| PyJWT + pwdlib recommendation | HIGH | Directly confirmed by current FastAPI docs (official tutorial uses PyJWT and pwdlib) |
| Alembic for migrations | HIGH | The only maintained migration tool for SQLAlchemy; universally used |
| Vite for React SPA | HIGH | CRA deprecated; Vite is 2025 standard for non-SSR React; React docs acknowledge it as the build-from-scratch tool |
| shadcn/ui | MEDIUM-HIGH | Dominant in 2024-2025 React ecosystem; Tailwind dependency is confirmed in stack; however, shadcn requires component-by-component setup which has a small learning curve |
| TanStack Query v5 | HIGH | API-fetching standard; v5 released 2023 and stable; replaces most Redux use cases for REST APIs |
| APScheduler for overdue jobs | MEDIUM | Works well in-process for low-frequency jobs (daily overdue check); risk is that it does not survive container restarts gracefully; acceptable for v1 but should be documented as a known limitation |
| fastapi-mail | MEDIUM | Active but less-used library; wraps aiosmtplib; the alternative (direct `aiosmtplib`) is more transparent if fastapi-mail causes issues |
| Docker Compose dev setup | HIGH | Pattern is standard; mailhog is the canonical dev SMTP sink |
| pytest + pytest-asyncio | HIGH | Official FastAPI testing recommendation; widely used |
| Vitest + React Testing Library | HIGH | Standard Vite-ecosystem testing stack |

## Key Risk: APScheduler in Docker

## Key Risk: JWT Storage on Frontend

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
