# Phase 4: Loan Views & History - Research

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **One Loans page with tabs:** Students should get a single Loans page with **Active** and **History** tabs, not separate routes.
- **List layout:** Loan lists should be rendered as a **table with columns**, not cards or stacked rows.
- **Active tab ordering:** Sort active loans by **due soonest first**.
- **History tab ordering:** Sort borrow history by **newest loan first**.
- **Overdue treatment:** Active overdue loans should use a **red overdue badge plus supporting text** so the status is obvious without relying on color alone.
- **History row content:** History rows should show **book title, borrow date, due date, return date, and outcome**.
- **Empty states:** Use a **friendly empty state with a short explanation** instead of a blank table.
- **One combined search box:** Librarian search should use a single query box that matches **student name or book title**.
- **Search trigger:** Search should run **only after submit**, not live while typing.
- **Default sort:** Search results should default to **most recent loan first**.
- **Result columns:** Librarian results should prioritize **student name, book title, status, and due date**.
- **Pagination controls:** Use **numbered pages with next/prev** rather than infinite scroll.

### the agent's Discretion

None — not specified in CONTEXT.md.

### Deferred Ideas (OUT OF SCOPE)

None.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LOAN-02 | Student can view all their active loans with due dates and an explicit overdue visual indicator | Backend loan-read query must filter `status='active'`; frontend must render active-loan table rows and overdue badge from returned API fields. |
| LOAN-03 | Student can view their full borrow history (all past loans, including returned) | Backend history query must include returned loans, sorted newest-first; frontend must render borrow-history columns and empty state. |
| LOAN-04 | Librarian can search all loans by student name or book title | Backend search endpoint must join `users` + `books`, accept submitted query text, and return matched loans only after submit. |
| LOAN-05 | Loan list views are paginated | Backend must expose page metadata and stable ordering; frontend must keep page state in the tab/search view and render next/prev + numbered pages. |
</phase_requirements>

## Summary

Phase 4 is a read-heavy feature on top of the existing async FastAPI + React stack. The backend already has the key data primitives: `Loan.status` supports `active/returned/overdue` and `overdue_notified_at`, `BorrowRequest` records the approval chain, and `User.full_name` + `Book.title` are already the fields needed for librarian search [CITED: backend/app/models/loan.py; backend/app/models/borrow_request.py; backend/app/models/user.py; backend/app/models/book.py]. That means this phase is mostly about adding read endpoints, query shaping, and UI presentation — not new borrow/return logic [CITED: .planning/phases/04-loan-views-history/04-CONTEXT.md].

The planner should keep the backend authoritative for scoping and sorting, then let the React side render role-specific tables with query-state driven pagination. Existing project patterns already favor backend RBAC (`require_role`), in-memory auth state, Axios with `withCredentials`, and TanStack Query for server state [CITED: backend/app/dependencies/auth.py; frontend/src/context/AuthContext.tsx; frontend/src/lib/axios.ts; frontend/src/pages/CreateLibrarianPage.tsx]. No new dependency is required for this phase [CITED: backend/requirements.txt; frontend/package.json].

**Primary recommendation:** build one loan-read API surface with role-aware filters and pagination, then render a student tabbed table and a librarian search table on top of it [CITED: .planning/phases/04-loan-views-history/04-CONTEXT.md; .planning/ROADMAP.md].

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Student active loans table + overdue badge | Browser / Client | API / Backend | The browser owns tab switching, table rendering, and badge presentation; the backend must supply only active loans and overdue state [CITED: .planning/phases/04-loan-views-history/04-CONTEXT.md]. |
| Student borrow history table | Browser / Client | API / Backend | The client renders the history columns and empty state; the backend owns the history query and sort order [CITED: .planning/phases/04-loan-views-history/04-CONTEXT.md]. |
| Librarian loan search + pagination UI | Browser / Client | API / Backend | The client owns submitted search, page navigation, and column layout; the backend owns joins, filtering, and page boundaries [CITED: .planning/phases/04-loan-views-history/04-CONTEXT.md]. |
| Loan search/filter execution | API / Backend | Database / Storage | SQLAlchemy should join `loans`, `users`, and `books`; PostgreSQL executes the filter/sort efficiently [CITED: backend/app/models/*.py; backend/app/database.py]. |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.12 [CITED: backend/requirements.txt] | Read APIs, request validation, RBAC dependencies | Already used by the app and matches the existing async router/dependency style [CITED: backend/app/routers/auth.py; backend/app/dependencies/auth.py]. |
| SQLAlchemy | 2.0.41 [CITED: backend/requirements.txt] | Query joins, ordering, pagination, ownership scoping | Existing model layer is SQLAlchemy 2.0 async; this phase needs query composition, not raw SQL [CITED: backend/app/database.py]. |
| asyncpg | 0.29.0 [CITED: backend/requirements.txt] | PostgreSQL async driver | Required by the current async engine setup [CITED: backend/app/database.py]. |
| Pydantic | 2.11.5 [CITED: backend/requirements.txt] | Loan list/search response schemas | Existing project uses Pydantic v2 response models and ORM mode equivalents [CITED: backend/app/schemas/*.py]. |
| PostgreSQL | 16 [CITED: compose.yml; STATE.md] | Source of truth for loan rows and joins | Existing schema and test setup assume PostgreSQL semantics [CITED: backend/tests/conftest.py]. |
| React | 18.3.1 [CITED: frontend/package.json] | Loan pages and role-specific table rendering | Existing frontend shell is already React SPA-based [CITED: frontend/src/App.tsx]. |
| React Router DOM | 6.30.4 [CITED: frontend/package.json] | Route-level entry points and search-param state | Existing app already uses route-based auth gates [CITED: frontend/src/App.tsx; frontend/src/components/ProtectedRoute.tsx]. |
| TanStack Query | 5.101.0 [CITED: frontend/package.json] | Cache, refetch, and page/query-key management | Existing project already uses it for API mutations; it fits page-based read queries well [CITED: frontend/src/pages/CreateLibrarianPage.tsx]. |
| React Hook Form | 7.78.0 [CITED: frontend/package.json] | Submitted librarian search form | Existing forms already use RHF + Zod; keep the same pattern for search submit [CITED: frontend/src/pages/LoginPage.tsx; frontend/src/pages/RegisterPage.tsx]. |
| Zod | 3.25.76 [CITED: frontend/package.json] | Client-side validation for page/search inputs | Existing forms validate input with Zod and `zodResolver` [CITED: frontend/src/pages/LoginPage.tsx; frontend/src/pages/RegisterPage.tsx]. |
| Axios | 1.17.0 [CITED: frontend/package.json] | Auth-aware HTTP client | Existing `api` instance already sends cookies and access tokens [CITED: frontend/src/lib/axios.ts]. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.x [CITED: backend/pytest.ini; backend/tests/*] | Backend validation | Use for API contract tests and pagination/ordering checks. |
| pytest-asyncio | 0.23.x [CITED: backend/pytest.ini; backend/tests/conftest.py] | Async test support | Use for async route and DB tests. |
| httpx | 0.27.x [CITED: backend/tests/conftest.py; backend/tests/test_*.py] | ASGI test client | Use for endpoint tests against the FastAPI app. |
| Existing shadcn-style UI primitives | repo-scaffolded [CITED: frontend/src/components/ui/*] | Table shell pieces, buttons, cards, alerts, skeletons | Use these before adding any custom component library. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQLAlchemy query builder | Raw SQL | Harder to maintain, easier to leak bugs into role scoping and pagination. |
| React Query page keys | Local component state + `useEffect` | Worse cache behavior, harder refresh/retry behavior. |
| `react-hook-form` search submit | Ad hoc form state | More boilerplate and less validation consistency. |
| Client-only filtering | Server-side filters + pagination | Client-only cannot safely enforce access control or scale across full histories. |

**Installation:**
```bash
# No new external packages are required for Phase 4.
```

## Architecture Patterns

### System Architecture Diagram

```text
Student browser
  -> Loans page (Active / History tabs)
  -> React Query + Axios
  -> GET /loans/me?page=&page_size=&status=
  -> FastAPI dependency checks current user
  -> SQLAlchemy filters loans by current_user.id
  -> PostgreSQL returns paginated rows
  -> React renders table + overdue badge + empty state

Librarian browser
  -> Loans search page / librarian view
  -> React Hook Form submit
  -> React Query + Axios
  -> GET /loans/search?q=&page=&page_size=
  -> FastAPI require_role("librarian", "admin_librarian")
  -> SQLAlchemy joins loans + users + books
  -> PostgreSQL returns paginated matches
  -> React renders table + numbered pages
```

### Recommended Project Structure

```text
backend/app/
├── routers/loans.py        # loan-read endpoints
├── schemas/loan.py         # list/search response models
└── services/loan_service.py # query helpers, pagination, scoping

frontend/src/
├── pages/LoansPage.tsx          # student tabs / librarian search shell
├── components/loans/             # table, tabs, search bar, pagination
└── hooks/useLoans.ts             # query hooks keyed by role/status/page/search
```

### Pattern 1: Role-scoped read model
**What:** Build the loan query in the backend around the authenticated user and role, then project a read-only response model for the UI [CITED: backend/app/dependencies/auth.py; backend/app/schemas/user.py].
**When to use:** Any endpoint that exposes user-specific loan state or librarian-wide search.
**Example:**
```python
# Source pattern: backend/app/dependencies/auth.py and existing SQLAlchemy async setup
stmt = (
    select(Loan)
    .where(Loan.student_id == current_user.id)  # student scope
    .order_by(Loan.due_date.asc())
    .limit(page_size)
    .offset((page - 1) * page_size)
)
```

### Pattern 2: Submitted search + page-keyed cache
**What:** Keep the librarian query in a form submit handler, and key the fetch on `q`, `page`, and `page_size` [CITED: frontend/src/pages/CreateLibrarianPage.tsx; frontend/src/lib/axios.ts].
**When to use:** Searchable, paginated read views.
**Example:**
```ts
// Source pattern: frontend/src/pages/CreateLibrarianPage.tsx + frontend/src/lib/axios.ts
const queryKey = ["loans", role, submittedQuery, page, pageSize];
```

### Anti-Patterns to Avoid

- **Client-side loan filtering:** leaks data and breaks role scoping; the backend must own student-only and librarian-wide visibility [CITED: backend/app/dependencies/auth.py].
- **Loading all loans then slicing in React:** defeats pagination and will get slow on large histories [CITED: .planning/ROADMAP.md].
- **Using `returned_at` alone to decide active/history:** `Loan.status` already exists and should drive the view state [CITED: backend/app/models/loan.py].

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Access control | Frontend-only role gating | FastAPI `require_role` + current-user scoping | Frontend gating is UX-only and can be bypassed [CITED: backend/app/dependencies/auth.py; frontend/src/components/ProtectedRoute.tsx]. |
| Paginated read queries | Fetch-all-and-slice client logic | SQLAlchemy `limit/offset` + total-count metadata | Needed for large histories and stable ordering [CITED: .planning/ROADMAP.md]. |
| Search matching | Raw SQL string concatenation | SQLAlchemy joins + bound `ilike`/filters | Avoids injection and keeps query plans maintainable [CITED: backend/app/database.py]. |
| Overdue state | Derive from UI date math | Use persisted `Loan.status='overdue'` | The model already stores the canonical status [CITED: backend/app/models/loan.py]. |

**Key insight:** this phase is mostly a read-model problem. Keep the write lifecycle in earlier phases and make the loan views purely query-driven [CITED: .planning/ROADMAP.md; .planning/REQUIREMENTS.md].

## Common Pitfalls

### Pitfall 1: Active loans leak into history
**What goes wrong:** the active tab shows returned loans, or history omits overdue loans.
**Why it happens:** filtering by `returned_at` or `due_date` instead of `Loan.status`.
**How to avoid:** use `status='active'` for the active tab and `status IN ('returned', ...)` for history; keep overdue as an active-state badge [CITED: backend/app/models/loan.py; .planning/phases/04-loan-views-history/04-CONTEXT.md].
**Warning signs:** active tab contains rows with `returned_at` set; overdue badge disappears when a loan is still active.

### Pitfall 2: Librarian search leaks other users' loans
**What goes wrong:** the search endpoint returns too many rows or ignores role constraints.
**Why it happens:** the query is built without `require_role` or without backend ownership/role checks.
**How to avoid:** protect the endpoint and apply filters in SQLAlchemy before pagination [CITED: backend/app/dependencies/auth.py].
**Warning signs:** students can reproduce librarian-only results with curl/Postman.

### Pitfall 3: Pagination jumps or duplicates rows
**What goes wrong:** page 2 repeats page 1 rows or ordering changes between refreshes.
**Why it happens:** no deterministic `order_by` before `limit/offset`.
**How to avoid:** always sort first, then paginate; keep the default sort stable and explicit [CITED: .planning/phases/04-loan-views-history/04-CONTEXT.md].
**Warning signs:** same search returns different row order after reload.

### Pitfall 4: UI hides status meaning
**What goes wrong:** overdue state is only color-coded or only implied by dates.
**Why it happens:** the view does not render the badge + supporting text specified in CONTEXT.
**How to avoid:** render explicit overdue text and a red badge together [CITED: .planning/phases/04-loan-views-history/04-CONTEXT.md].
**Warning signs:** accessibility review cannot tell overdue from normal active rows.

## Code Examples

Verified patterns from current project code:

### Backend RBAC dependency
```python
# Source: backend/app/dependencies/auth.py
current_user: Annotated[User, Depends(require_role("admin_librarian"))]
```

### Frontend API + React Query pattern
```tsx
// Source: frontend/src/pages/CreateLibrarianPage.tsx
const mutation = useMutation({
  mutationFn: (values) => api.post("/admin/users", values),
});
```

### Frontend auth-aware Axios instance
```ts
// Source: frontend/src/lib/axios.ts
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  withCredentials: true,
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Load-all loans in the browser | Server-side paginated queries keyed by role/search/page | Phase 4 scope [CITED: .planning/ROADMAP.md] | Keeps large histories fast and secure. |
| Frontend-only access checks | Backend `require_role` + current-user scoping | Phase 1 foundation [CITED: backend/app/dependencies/auth.py] | Prevents role bypass. |
| Card-based record lists | Dense tables for history/search views | Phase 4 context decision [CITED: .planning/phases/04-loan-views-history/04-CONTEXT.md] | Better for data review and pagination. |

**Deprecated/outdated:**
- Client-side filtering for multi-user loan data: too easy to bypass and too slow at scale [CITED: backend/app/dependencies/auth.py; .planning/ROADMAP.md].

## Assumptions Log

If this table is empty: all claims in this research were verified or cited — no user confirmation needed.

## Open Questions

1. **What exact route shape should the loans UI use for librarian access?**
   - What we know: student UI is one tabbed Loans page; librarian needs submitted search + pagination [CITED: .planning/phases/04-loan-views-history/04-CONTEXT.md].
   - What's unclear: whether librarian search lives on the same route, a sibling route, or a role-specific dashboard subpage.
   - Recommendation: keep the backend resource unified, then choose the route shape that best fits the existing navigation pattern.

2. **What should the default page size be?**
   - What we know: views must paginate [CITED: .planning/REQUIREMENTS.md].
   - What's unclear: no existing project-wide pagination size is established.
   - Recommendation: pick one page size and use it consistently across student and librarian views.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Node.js | Frontend build + UI work | ✓ | 24.16.0 [CITED: environment probe] | — |
| npm | Frontend dependency/runtime commands | ✓ | 11.13.0 [CITED: environment probe] | — |
| Docker | Compose-based backend/frontend/db execution | ✓ | 29.4.3 [CITED: environment probe] | — |
| Docker Compose | Dev stack orchestration | ✓ | 5.1.3 [CITED: environment probe] | — |
| Python | Direct backend execution on host | ✗ | — | Use `docker compose exec backend ...` or run backend inside the compose service [CITED: compose.yml]. |
| psql | Direct DB CLI on host | ✗ | — | Use the `db` compose service instead [CITED: compose.yml]. |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- Python: run backend work through Docker Compose.
- psql: use the PostgreSQL container/service.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio + httpx [CITED: backend/pytest.ini; backend/tests/conftest.py] |
| Config file | `backend/pytest.ini` [CITED: backend/pytest.ini] |
| Quick run command | `cd backend; pytest tests/test_loans.py -x` |
| Full suite command | `cd backend; pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOAN-02 | Active loans endpoint returns only current user rows and marks overdue clearly | integration | `cd backend; pytest tests/test_loans.py::TestStudentActiveLoans -x` | ❌ Wave 0 |
| LOAN-03 | History endpoint returns past loans including returned outcomes | integration | `cd backend; pytest tests/test_loans.py::TestStudentLoanHistory -x` | ❌ Wave 0 |
| LOAN-04 | Librarian search matches student name or book title after submit | integration | `cd backend; pytest tests/test_loans.py::TestLibrarianLoanSearch -x` | ❌ Wave 0 |
| LOAN-05 | Pagination metadata, stable ordering, and next/prev page boundaries | integration | `cd backend; pytest tests/test_loans.py::TestLoanPagination -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend; pytest tests/test_loans.py -x`
- **Per wave merge:** `cd backend; pytest`
- **Phase gate:** full backend suite green before verification handoff

### Wave 0 Gaps

- [ ] `backend/tests/test_loans.py` — covers LOAN-02 through LOAN-05.
- [ ] `backend/app/routers/loans.py` — needed for API contract tests.
- [ ] `backend/app/schemas/loan.py` — needed for response-shape assertions.
- [ ] `frontend` test framework — no Vitest/RTL setup exists yet for UI smoke coverage [CITED: frontend/package.json].

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | yes | Reuse existing auth bootstrap and backend auth dependencies [CITED: frontend/src/context/AuthContext.tsx; backend/app/dependencies/auth.py]. |
| V3 Session Management | yes | Continue using httpOnly refresh cookie + in-memory access token [CITED: backend/app/routers/auth.py; frontend/src/context/AuthContext.tsx]. |
| V4 Access Control | yes | Enforce current-user scoping and librarian role checks in the backend [CITED: backend/app/dependencies/auth.py]. |
| V5 Input Validation | yes | Validate page, page_size, and query text with Pydantic/Zod before query execution [CITED: backend/app/schemas/*.py; frontend/src/pages/LoginPage.tsx]. |
| V6 Cryptography | no new work | Reuse existing JWT/password helpers; do not add new crypto logic [CITED: backend/app/services/auth_service.py]. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unauthorized loan disclosure / IDOR | Information Disclosure | Backend scoping on `current_user.id` plus librarian-only search access [CITED: backend/app/dependencies/auth.py]. |
| Search injection | Tampering | SQLAlchemy expressions and bound parameters only; no string-concatenated SQL [CITED: backend/app/database.py]. |
| Pagination abuse | Denial of Service | Cap page size, enforce deterministic ordering, and return totals from the server [CITED: .planning/ROADMAP.md]. |
| Frontend-only authorization | Elevation of Privilege | Treat `ProtectedRoute` as UX only; backend remains the authority [CITED: frontend/src/components/ProtectedRoute.tsx; backend/app/dependencies/auth.py]. |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/04-loan-views-history/04-CONTEXT.md` — locked UI/behavior decisions.
- `.planning/REQUIREMENTS.md` — LOAN-02 through LOAN-05 requirements.
- `.planning/ROADMAP.md` — phase goal and success criteria.
- `.planning/STATE.md` — app stack and carried-forward decisions.
- `CLAUDE.md` — project stack and workflow constraints.
- `backend/app/models/loan.py`, `borrow_request.py`, `user.py`, `book.py` — field-level query inputs and status semantics.
- `backend/app/dependencies/auth.py`, `backend/app/routers/auth.py` — auth/RBAC pattern to reuse.
- `frontend/src/context/AuthContext.tsx`, `frontend/src/components/ProtectedRoute.tsx`, `frontend/src/lib/axios.ts`, `frontend/src/pages/CreateLibrarianPage.tsx`, `frontend/src/pages/DashboardPage.tsx` — frontend auth/query patterns and UI shell.
- `backend/tests/*`, `backend/pytest.ini` — existing validation infrastructure.
- `compose.yml`, `backend/requirements.txt`, `frontend/package.json` — runtime and dependency baseline.

### Secondary (MEDIUM confidence)
- PyPI registry queries (FastAPI, SQLAlchemy, etc.) and npm registry queries (React, React Router, TanStack Query, etc.) run on 2026-06-11 — used to confirm current registry availability.
- Environment probes on 2026-06-11 — used to confirm host runtime availability.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pinned repo versions plus current registry checks and existing code patterns.
- Architecture: HIGH — directly constrained by CONTEXT/ROADMAP and existing app structure.
- Pitfalls: HIGH — derived from current models, auth code, and phase scope.

**Research date:** 2026-06-11
**Valid until:** 2026-07-11
