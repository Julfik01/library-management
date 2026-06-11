# Architecture Research — University Library Management System

**Researched:** 2026-06-10
**Stack:** FastAPI + React + PostgreSQL + Docker
**Confidence:** HIGH — patterns are well-established for this domain and stack

---

## Component Map

### Decision: Modular Monolith, Not Microservices

For this scale (university, single institution, two roles), a **modular monolith** is the correct architecture. Separate services would add deployment complexity, network latency, and distributed transaction problems (e.g. approving a borrow request must atomically decrement available copies and create a loan record — trivial in a monolith, a saga in microservices).

Each "service" is a FastAPI `APIRouter` module. They share one database and one process. Boundaries are enforced by Python module imports, not network calls.

```
┌─────────────────────────────────────────────┐
│                  FastAPI App                 │
│                                             │
│  ┌──────────┐  ┌─────────┐  ┌───────────┐  │
│  │   Auth   │  │ Catalog │  │  Borrow   │  │
│  │  Router  │  │ Router  │  │  Router   │  │
│  └────┬─────┘  └────┬────┘  └─────┬─────┘  │
│       │             │             │         │
│  ┌────▼─────────────▼─────────────▼──────┐  │
│  │         Shared Dependencies           │  │
│  │  (get_db, get_current_user, rbac)     │  │
│  └────────────────────┬──────────────────┘  │
│                       │                     │
│  ┌────────────────────▼──────────────────┐  │
│  │         SQLAlchemy / Alembic          │  │
│  └────────────────────┬──────────────────┘  │
└───────────────────────┼─────────────────────┘
                        │
              ┌─────────▼──────────┐
              │     PostgreSQL     │
              └────────────────────┘

  ┌─────────────────────────────────┐
  │         React SPA               │
  │  (Vite + React Router + Axios)  │
  └──────────────┬──────────────────┘
                 │ HTTP/JSON
                 ▼
           FastAPI App
```

### Module Responsibilities

| Module | Router Prefix | Responsibility | Talks To |
|--------|--------------|----------------|----------|
| `auth` | `/api/auth` | Registration, login, JWT issue, password hash | `users` table |
| `users` | `/api/users` | Profile reads, admin creates librarian accounts | `users` table |
| `catalog` | `/api/books` | CRUD for books, copy count tracking, search | `books` table |
| `borrows` | `/api/borrows` | Submit request, approve/reject, record return, overdue query | `borrow_requests`, `loans`, `books` (copy count) |
| `notifications` | (internal) | Email dispatch triggered by borrow lifecycle events | Called by `borrows` module; no HTTP router |
| `deps` | (shared) | `get_db`, `get_current_user`, `require_role` — injected everywhere | Used by all routers |

**The `notifications` module has no router.** It is a plain Python module called by the `borrows` service via FastAPI `BackgroundTasks`. It does not need its own HTTP surface.

### File Layout

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, include_router calls
│   ├── deps.py                  # get_db, get_current_user, require_role
│   ├── database.py              # SQLAlchemy engine, SessionLocal, Base
│   ├── config.py                # Settings via pydantic-settings
│   ├── models/
│   │   ├── user.py
│   │   ├── book.py
│   │   └── borrow.py
│   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── auth.py
│   │   ├── book.py
│   │   └── borrow.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── catalog.py
│   │   └── borrows.py
│   └── services/
│       ├── email.py             # SMTP send logic
│       └── overdue.py           # Overdue detection logic
├── alembic/
│   └── versions/
├── alembic.ini
├── requirements.txt
└── Dockerfile

frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx                  # Router setup
│   ├── api/                     # Axios client + typed request functions
│   │   ├── client.ts            # Axios instance with interceptors
│   │   ├── auth.ts
│   │   ├── books.ts
│   │   └── borrows.ts
│   ├── pages/
│   │   ├── auth/
│   │   ├── catalog/
│   │   └── borrows/
│   ├── components/              # Reusable UI
│   └── context/
│       └── AuthContext.tsx      # JWT storage, current user
├── index.html
└── Dockerfile
```

---

## Database Schema Patterns

### Guiding Principle: Count-Based Copy Model

The system tracks `total_copies` and `available_copies` on the `books` table. No per-copy rows. This is correct for this scale and scope (explicit in PROJECT.md). The trade-off: concurrent borrow approvals must use a database-level check or row-level lock on `available_copies` to prevent over-allocation.

### Core Tables

#### `users`
```sql
CREATE TABLE users (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    full_name   VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role        VARCHAR(20)  NOT NULL CHECK (role IN ('student', 'librarian', 'admin_librarian')),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users(email);
```

Notes:
- `role` uses a CHECK constraint rather than a separate roles table — three static roles don't need a join table.
- `admin_librarian` is the elevated librarian who can create other librarians. Checked in application logic, not a foreign key relationship.
- UUID primary keys prevent enumeration attacks on user IDs in API URLs.

#### `books`
```sql
CREATE TABLE books (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(500) NOT NULL,
    author          VARCHAR(255) NOT NULL,
    isbn            VARCHAR(20)  UNIQUE,
    category        VARCHAR(100),
    publisher       VARCHAR(255),
    published_year  SMALLINT,
    cover_image_url TEXT,
    total_copies    SMALLINT    NOT NULL DEFAULT 1 CHECK (total_copies >= 0),
    available_copies SMALLINT   NOT NULL DEFAULT 1 CHECK (available_copies >= 0),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT copies_not_exceed_total CHECK (available_copies <= total_copies)
);
CREATE INDEX idx_books_title  ON books USING gin(to_tsvector('english', title));
CREATE INDEX idx_books_author ON books USING gin(to_tsvector('english', author));
CREATE INDEX idx_books_isbn   ON books(isbn);
CREATE INDEX idx_books_category ON books(category);
```

Notes:
- Full-text GIN indexes on `title` and `author` support fast `ILIKE`/`to_tsquery` searches without a separate search engine.
- `CONSTRAINT copies_not_exceed_total` is a database-level guard. The application still validates this, but the DB is the final authority.
- `updated_at` should be maintained via a trigger or application layer on every UPDATE.

#### `borrow_requests`
```sql
CREATE TABLE borrow_requests (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  UUID        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    book_id     UUID        NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at  TIMESTAMPTZ,
    decided_by  UUID        REFERENCES users(id),
    notes       TEXT                               -- librarian rejection reason
);
CREATE INDEX idx_borrow_requests_student ON borrow_requests(student_id);
CREATE INDEX idx_borrow_requests_book    ON borrow_requests(book_id);
CREATE INDEX idx_borrow_requests_status  ON borrow_requests(status);
```

Notes:
- `ON DELETE RESTRICT` on both FKs: you must not be able to delete a book or user with pending/active requests. This enforces data integrity without soft deletes.
- `decided_by` records which librarian actioned the request — audit trail.
- `notes` allows rejection reasons without a separate table.

#### `loans`
```sql
CREATE TABLE loans (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    borrow_request_id UUID      NOT NULL UNIQUE REFERENCES borrow_requests(id),
    student_id      UUID        NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    book_id         UUID        NOT NULL REFERENCES books(id) ON DELETE RESTRICT,
    borrowed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    due_date        TIMESTAMPTZ NOT NULL,           -- borrowed_at + 14 days
    returned_at     TIMESTAMPTZ,                    -- NULL = active loan
    is_overdue      BOOLEAN     NOT NULL DEFAULT FALSE,
    overdue_notified_at TIMESTAMPTZ                 -- prevents duplicate emails
);
CREATE INDEX idx_loans_student  ON loans(student_id);
CREATE INDEX idx_loans_book     ON loans(book_id);
CREATE INDEX idx_loans_due_date ON loans(due_date) WHERE returned_at IS NULL;
```

Notes:
- `UNIQUE` on `borrow_request_id` enforces one-loan-per-request at the database level.
- Partial index on `due_date WHERE returned_at IS NULL` makes overdue queries fast — only active loans are indexed.
- `overdue_notified_at` is critical: without it, a nightly job would send the same overdue email every time it runs.
- `is_overdue` is a denormalised flag. It can be computed as `NOW() > due_date AND returned_at IS NULL`, but storing it allows efficient dashboard queries without recalculating on every row.

### Entity Relationships

```
users (1) ──── (N) borrow_requests ──── (1) loans
              FK: student_id, decided_by

books (1) ──── (N) borrow_requests
               (1) ──── (N) loans
```

### Key Schema Constraints Summary

| Rule | Enforced By |
|------|-------------|
| `available_copies <= total_copies` | DB CHECK constraint |
| One loan per borrow request | UNIQUE constraint on `loans.borrow_request_id` |
| Cannot delete book with active requests | ON DELETE RESTRICT |
| `available_copies >= 0` | DB CHECK constraint |
| Role limited to three values | DB CHECK constraint |

---

## API Design Patterns

### URL Conventions

REST resources are plural nouns. Actions that don't map to CRUD use sub-resources or action verbs only when necessary.

```
POST   /api/auth/register
POST   /api/auth/login                     → returns { access_token, token_type }
POST   /api/auth/logout                    → client-side token discard (stateless JWT)

GET    /api/users/me                       → current user profile
POST   /api/users                          → admin_librarian creates librarian account
PATCH  /api/users/{id}/deactivate          → soft disable (admin only)

GET    /api/books                          → paginated catalog search
POST   /api/books                          → librarian adds book
GET    /api/books/{id}
PATCH  /api/books/{id}                     → librarian edits
DELETE /api/books/{id}                     → librarian removes

GET    /api/borrows                        → librarian: all requests; student: own requests
POST   /api/borrows                        → student submits request
GET    /api/borrows/{id}
PATCH  /api/borrows/{id}/approve           → librarian approves → creates loan, decrements copies
PATCH  /api/borrows/{id}/reject            → librarian rejects
POST   /api/borrows/{id}/return            → librarian records return → increments copies

GET    /api/borrows/loans                  → student: active loans + due dates
GET    /api/borrows/overdue                → librarian: all overdue loans dashboard
```

### Pagination and Filtering for Book Search

`GET /api/books` uses query parameters. Cursor-based pagination is overkill here; offset pagination is fine for catalog sizes typical in university libraries (< 50,000 titles).

```
GET /api/books?q=python&category=Computing&page=1&limit=20&sort=title&order=asc
```

Response envelope:
```json
{
  "items": [...],
  "total": 143,
  "page": 1,
  "limit": 20,
  "pages": 8
}
```

Search strategy: use PostgreSQL `ILIKE` for simple queries. For `q` (full-text), use `to_tsvector / to_tsquery` against title and author. Do not introduce Elasticsearch for v1 — GIN indexes on PostgreSQL are sufficient.

### Authentication Flow

```
Client                        FastAPI
  │                              │
  ├─ POST /auth/login ──────────►│
  │   { email, password }        │ verify hash (bcrypt/argon2)
  │◄─ { access_token } ──────────┤ JWT: { sub: user_id, role: "student", exp }
  │                              │
  ├─ GET /books (Bearer token) ──►│
  │                              │ deps.get_current_user() decodes JWT
  │                              │ returns User object
  │◄─ 200 { items } ─────────────┤
```

Token payload: `{ "sub": "<user_uuid>", "role": "student|librarian|admin_librarian", "exp": <unix_ts> }`. Include `role` in the JWT so RBAC checks do not require a database round-trip on every request.

Access token expiry: 60 minutes for student, 8 hours for librarian (librarians work shifts). No refresh token for v1 — simplicity wins; re-login is acceptable.

### RBAC Pattern: Dependency Injection, Not Middleware

Use FastAPI dependencies for authorization, not middleware. Middleware operates before routing — it cannot easily distinguish which role is required by which endpoint. Dependencies are composable and co-located with the endpoint.

```python
# app/deps.py

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    # decode JWT, load user from DB, raise 401 if invalid
    ...

def require_role(*roles: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return checker

# Usage in routers:
LibrarianDep = Annotated[User, Depends(require_role("librarian", "admin_librarian"))]
StudentDep   = Annotated[User, Depends(require_role("student"))]
AnyUserDep   = Annotated[User, Depends(get_current_user)]
```

Apply role dependencies at the **router level** for blanket protection, and override per-endpoint when a route serves multiple roles (e.g. `GET /api/borrows` filters results differently by role).

### Background Tasks for Email Notifications

Use **FastAPI `BackgroundTasks`** for approval/rejection emails. This is the correct tool:

- Email sends are lightweight (< 1s for SMTP)
- Same process context — no broker setup required
- Acceptable failure mode: if the web worker crashes mid-send, the email is lost (acceptable for v1; not financial-critical)
- No retry requirement stated in PROJECT.md

Use a **scheduled APScheduler job** (or a simple cron + script) for overdue detection, not BackgroundTasks. Overdue checks run on a schedule (e.g. nightly at 2 AM), not in response to HTTP requests. APScheduler integrates cleanly into a FastAPI app startup event.

```python
# Triggered on borrow approve:
background_tasks.add_task(send_approval_email, user_email, book_title, due_date)

# Triggered on borrow reject:
background_tasks.add_task(send_rejection_email, user_email, book_title, notes)

# Scheduled (APScheduler, runs nightly):
def check_overdue_and_notify():
    # query loans WHERE due_date < NOW() AND returned_at IS NULL AND overdue_notified_at IS NULL
    # send overdue email, set overdue_notified_at = NOW()
    ...
```

Do not introduce Celery or Redis for v1. The operational overhead (broker process, worker process, monitoring) is not justified for two email trigger points.

---

## Data Flow

### Flow 1: Student Submits Borrow Request

```
Student         React              FastAPI/borrows            PostgreSQL
  │               │                      │                        │
  ├─ Click ──────►│                      │                        │
  │               ├─ POST /borrows ──────►│                        │
  │               │   { book_id }         │ 1. Auth: decode JWT    │
  │               │                      │ 2. Check book exists   ├─ SELECT books WHERE id=?
  │               │                      │ 3. Check available > 0 │◄─ { available_copies: 2 }
  │               │                      │ 4. Check no pending    ├─ SELECT borrow_requests
  │               │                      │    request for same    │    WHERE student=? book=?
  │               │                      │    book by this student │    AND status='pending'
  │               │                      │ 5. INSERT request      ├─ INSERT borrow_requests
  │               │◄─ 201 { request } ───┤                        │
```

### Flow 2: Librarian Approves Request

```
Librarian       React              FastAPI/borrows            PostgreSQL         BackgroundTasks
  │               │                      │                        │                    │
  ├─ Approve ────►│                      │                        │                    │
  │               ├─ PATCH /borrows/{id}/approve ──────────────►  │                    │
  │               │                      │ 1. Auth: require       │                    │
  │               │                      │    librarian role      │                    │
  │               │                      │ 2. Load request,       ├─ SELECT + FOR UPDATE
  │               │                      │    verify pending      │  (row lock on book)│
  │               │                      │ 3. BEGIN TRANSACTION   │                    │
  │               │                      │ 4. UPDATE request      ├─ UPDATE borrow_requests
  │               │                      │    status=approved     │    SET status='approved'
  │               │                      │ 5. INSERT loan         ├─ INSERT loans
  │               │                      │    due = NOW()+14d     │                    │
  │               │                      │ 6. DECREMENT copies    ├─ UPDATE books
  │               │                      │    available_copies-=1 │    SET available_copies-=1
  │               │                      │ 7. COMMIT              │                    │
  │               │                      │ 8. Queue email         │               ─────►│ send email
  │               │◄─ 200 { loan } ──────┤                        │                    │
```

The SELECT FOR UPDATE on the book row during approval prevents two librarians from approving the last copy simultaneously (race condition on `available_copies`).

### Flow 3: Overdue Detection (Scheduled)

```
APScheduler (nightly)      FastAPI/services/overdue.py      PostgreSQL        Email
       │                              │                          │               │
       ├─ trigger job ───────────────►│                          │               │
       │                              ├─ query overdue ─────────►│               │
       │                              │                          │◄─ [loan rows] │
       │                              │  for each loan:          │               │
       │                              │  - mark is_overdue=True  ├─ UPDATE loans │
       │                              │  - set overdue_notified  │               │
       │                              │                          │          ─────►│ send email
```

### Flow 4: Student Views Active Loans

```
Student         React              FastAPI/borrows            PostgreSQL
  │               │                      │                        │
  ├─ My Loans ───►│                      │                        │
  │               ├─ GET /borrows/loans ─►│                        │
  │               │                      │ 1. Auth: get_current_user
  │               │                      │ 2. Query loans         ├─ SELECT loans
  │               │                      │    WHERE student=me    │    JOIN books
  │               │                      │    AND returned IS NULL │    WHERE student_id=?
  │               │◄─ 200 [loans+books] ─┤                        │
```

---

## Frontend Architecture

### Page Structure and Routing

```
App (AuthContext Provider)
└── Router
    ├── /login                   PublicRoute → LoginPage
    ├── /register                PublicRoute → RegisterPage
    └── ProtectedRoute (requires auth)
        ├── /                    → redirect to /catalog
        ├── /catalog             → CatalogPage (student + librarian)
        ├── /catalog/:id         → BookDetailPage
        ├── /my-loans            → StudentRoute → MyLoansPage
        ├── /my-requests         → StudentRoute → MyRequestsPage
        ├── /admin/requests      → LibrarianRoute → ManageRequestsPage
        ├── /admin/books         → LibrarianRoute → ManageBooksPage
        ├── /admin/books/new     → LibrarianRoute → AddBookPage
        ├── /admin/books/:id     → LibrarianRoute → EditBookPage
        ├── /admin/overdue       → LibrarianRoute → OverdueDashboardPage
        └── /admin/users         → AdminLibrarianRoute → ManageUsersPage
```

**Route guard pattern:** Three route wrapper components check `user.role` from AuthContext:
- `ProtectedRoute` — must be logged in (any role)
- `LibrarianRoute` — must be `librarian` or `admin_librarian`
- `AdminLibrarianRoute` — must be `admin_librarian`

### API Client Layer

Centralise all HTTP calls in `src/api/`. Never call `axios.get(...)` directly from components.

```typescript
// src/api/client.ts
const client = axios.create({ baseURL: import.meta.env.VITE_API_URL });

// Request interceptor: attach Bearer token from localStorage
client.interceptors.request.use(config => {
    const token = localStorage.getItem('access_token');
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
});

// Response interceptor: redirect to /login on 401
client.interceptors.response.use(
    res => res,
    err => {
        if (err.response?.status === 401) { /* clear token, navigate('/login') */ }
        return Promise.reject(err);
    }
);
```

Each domain gets its own typed file: `api/books.ts`, `api/borrows.ts`, `api/auth.ts`. Components call these functions, not the raw client. This isolates the API contract from component code and makes mocking trivial in tests.

---

## Docker Compose Topology

### Dev Environment Services

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: library
      POSTGRES_USER: library
      POSTGRES_PASSWORD: library
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"          # exposed for local psql/pgAdmin access
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U library"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app        # hot-reload: mount source into container
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://library:library@db:5432/library
      SECRET_KEY: dev-secret-key-change-in-prod
      SMTP_HOST: mailhog
      SMTP_PORT: 1025
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    command: npm run dev -- --host 0.0.0.0 --port 3000
    volumes:
      - ./frontend:/app
      - /app/node_modules     # prevent host node_modules from shadowing container's
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend

  mailhog:
    image: mailhog/mailhog
    ports:
      - "1025:1025"           # SMTP
      - "8025:8025"           # Web UI to view sent emails

volumes:
  postgres_data:
```

### Topology Notes

- **MailHog** is the dev email sink. Configure the backend SMTP client to point to `mailhog:1025`. Developers see all outgoing emails at `http://localhost:8025`. No real emails leave the dev environment.
- `depends_on` with `condition: service_healthy` ensures the backend does not start until PostgreSQL is accepting connections (prevents Alembic migration failures on startup).
- Frontend mounts `node_modules` as a named anonymous volume so that the container's installed packages are not overwritten by a (possibly absent) host `node_modules` directory.
- `VITE_API_URL` points to `localhost:8000` — the Vite dev server proxies or the frontend calls the API directly from the browser, not from the container network. If CORS issues arise, add `CORS_ORIGINS=http://localhost:3000` to the backend env.

---

## Build Order Implications

This is the dependency order. Each layer can only be built after its dependencies exist.

```
1. Database schema (Alembic migrations)
        │
        ▼
2. Core models + database session (SQLAlchemy models, deps.py)
        │
        ▼
3. Auth module (users table, JWT, password hashing)
        │ (all subsequent modules require auth)
        ▼
4. Catalog module (books CRUD, search)
        │
        ▼
5. Borrow module (requests, loans — depends on users + books)
        │
        ▼
6. Notification service (email — triggered by borrow events)
        │
        ▼
7. Overdue scheduler (depends on loans data existing)
```

**Frontend mirrors this order:**
1. AuthContext + login/register pages (nothing works without auth)
2. API client layer (needed before any page can fetch data)
3. Catalog browsing (read-only, simplest)
4. Borrow request flow (student-facing)
5. Librarian management pages (approve/reject/return/overdue)

**Phase boundary recommendation:** Auth + Catalog + basic Borrow flow (submit + approve) form a natural first deployable milestone. Notifications and overdue detection are additive and can follow without breaking existing flows.

---

## Critical Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Monolith vs microservices | Modular monolith | Single institution, shared DB transaction needed for approve+decrement |
| RBAC mechanism | DI dependencies, not middleware | Co-located with endpoints, composable, testable |
| Copy tracking | Count fields on `books` table | Per-copy rows not needed; simpler schema per PROJECT.md |
| Email background jobs | FastAPI BackgroundTasks | Lightweight sends, no broker overhead; acceptable v1 loss tolerance |
| Overdue detection | APScheduler in-process | Scheduled, not request-driven; no external cron dependency |
| Auth token | JWT with role in payload | No DB round-trip per request; role rarely changes |
| Search | PostgreSQL GIN full-text | No Elasticsearch needed at university catalog scale |
| Race condition on approve | SELECT FOR UPDATE | Prevents over-allocation of last copy without distributed locks |
| Dev email | MailHog | Zero-config, no real email sent, inspectable via browser UI |

---

*Sources: FastAPI official documentation (bigger-applications, security/oauth2-jwt, background-tasks, sql-databases), PostgreSQL documentation, PROJECT.md requirements analysis.*
