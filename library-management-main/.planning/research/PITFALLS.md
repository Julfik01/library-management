# Pitfalls Research — University Library Management System

**Domain:** University Library Management System (FastAPI + React + PostgreSQL + Docker)
**Researched:** 2026-06-10
**Overall confidence:** HIGH — all pitfalls drawn from well-documented, recurring patterns in the FastAPI/SQLAlchemy/React/PostgreSQL ecosystem

---

## Critical Pitfalls (can derail the project)

These mistakes cause data corruption, security holes, or require full rewrites of core subsystems.

---

### CP-1: Concurrent Borrow Requests Causing Over-Allocation

**What goes wrong:**
Two students simultaneously request the last available copy of a book. Both requests read `available_copies = 1`, both pass the "is available?" check, and both get approved. The library now has `-1` available copies — a book is out on loan that doesn't physically exist.

**Why it happens:**
The naive implementation reads `available_copies`, checks `> 0`, then decrements it in two separate SQL statements without a lock. Between the read and the write, another request wins the race.

**Consequences:**
Silent data corruption. The `available_copies` column drifts negative. Librarians approve loans for books that aren't there. Difficult to detect without periodic audits.

**Prevention:**
Use a PostgreSQL `SELECT ... FOR UPDATE` lock on the book row inside the approval transaction:

```sql
-- Inside the approve-loan transaction:
SELECT id, available_copies FROM books WHERE id = :book_id FOR UPDATE;
-- then check available_copies > 0, then decrement
UPDATE books SET available_copies = available_copies - 1 WHERE id = :book_id;
```

In SQLAlchemy async:
```python
result = await session.execute(
    select(Book).where(Book.id == book_id).with_for_update()
)
book = result.scalar_one()
if book.available_copies < 1:
    raise HTTPException(status_code=409, detail="No copies available")
book.available_copies -= 1
```

Also add a `CHECK (available_copies >= 0)` constraint at the database level as a hard backstop.

**Detection (warning signs):**
- `available_copies` column ever goes negative in the database
- Two active loans exist for a book that only has 1 copy
- Load testing with concurrent approval requests triggers 500 errors or negative counts

**Phase this surfaces:** Phase 2-3 (Borrow Request approval logic). Will not appear in single-user manual testing. Only surfaces under concurrent load or when two librarians work simultaneously.

---

### CP-2: SQLAlchemy Async Session Shared Across Requests (Scope Leak)

**What goes wrong:**
The async `AsyncSession` is created at application startup (or as a module-level global) instead of per-request. Multiple concurrent requests share a single session, causing `MissingGreenlet`, `DetachedInstanceError`, `sqlalchemy.exc.InvalidRequestError: This Session's transaction has been rolled back due to a previous exception` errors, or worse — silently returning stale data from one request to another.

**Why it happens:**
Developers familiar with Flask/SQLAlchemy sync patterns use a pattern like `db = AsyncSession(engine)` at module level, or inject the session incorrectly through a dependency.

**Consequences:**
Intermittent 500 errors under load, transactions bleeding across requests, potential data exposure between concurrent sessions. Very hard to reproduce in single-user testing.

**Prevention:**
Always create sessions via a per-request dependency using `async_sessionmaker` or `AsyncSession` as a FastAPI `Depends`:

```python
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
        # session is closed automatically after request
```

Set `expire_on_commit=False` — without this, accessing ORM attributes after `await session.commit()` triggers lazy-load attempts that fail in async context.

**Detection (warning signs):**
- `MissingGreenlet` or `greenlet_spawn` errors in logs
- `DetachedInstanceError` when accessing model attributes after commit
- Different request handlers returning each other's data

**Phase this surfaces:** Phase 1 (database scaffolding). If the session factory is set up wrong from day one, every endpoint will be affected.

---

### CP-3: JWT Tokens Never Expire / No Token Invalidation on Logout

**What goes wrong:**
JWTs are issued with a long expiry (or no expiry). When a user logs out, the token is discarded on the frontend but remains valid on the backend. A stolen or intercepted token grants indefinite access. Additionally, if a librarian account is deactivated, their existing tokens still work.

**Why it happens:**
JWTs are stateless by design — the server cannot "invalidate" them without extra infrastructure. Developers skip the token blocklist step because it adds complexity.

**Consequences:**
Security hole. Stolen sessions persist. Deactivated accounts retain access. For a university system, this is a compliance risk.

**Prevention:**
- Set `access_token` expiry short: 15–60 minutes.
- Issue a `refresh_token` (longer-lived: 7–30 days) stored as `httpOnly` cookie.
- Maintain a `refresh_token_blocklist` table (or Redis set). On logout, insert the refresh token's `jti` claim. On refresh requests, reject blocklisted tokens.
- On access token expiry check the user's `is_active` flag in the database (the token can carry the user ID; one DB lookup per refresh is acceptable).

**Detection (warning signs):**
- Logout doesn't actually revoke access when token is replayed via curl
- No `exp` claim in the decoded JWT payload
- No server-side state for tracking invalidated tokens

**Phase this surfaces:** Phase 1 (auth). The foundation is set here. Adding a blocklist retroactively requires schema changes and refactoring token endpoints.

---

### CP-4: Alembic Migrations Not Matching SQLAlchemy Models (Silent Drift)

**What goes wrong:**
A developer changes a SQLAlchemy model (adds a column, changes a type, adds a constraint) but forgets to generate or run the Alembic migration. The app starts fine because SQLAlchemy doesn't enforce schema at startup. Queries fail at runtime with `ProgrammingError: column "x" does not exist` — but only when that code path is hit.

**Why it happens:**
The ORM and the database schema are decoupled. Alembic only knows about changes when you explicitly run `alembic revision --autogenerate`. Auto-generate also misses some changes (server-side defaults, partial indexes, custom types).

**Consequences:**
Works in dev (where `Base.metadata.create_all()` may have been called), breaks in staging/production. Schema drift accumulates and becomes a large migration debt.

**Prevention:**
- Never use `Base.metadata.create_all()` in production paths — Alembic owns the schema.
- Add a CI check: after each model change, run `alembic revision --autogenerate -m "check"` and verify the generated migration is empty (i.e. models and DB are in sync).
- Always commit migration files to git in the same PR as the model change.
- For Docker: run `alembic upgrade head` as the container entrypoint, before starting the application.

**Detection (warning signs):**
- `ProgrammingError: column X does not exist` or `relation X does not exist` errors at runtime
- `alembic current` shows a revision behind `alembic heads`
- Model has columns that don't appear in `\d tablename` in psql

**Phase this surfaces:** Throughout. Most dangerous at Phase 2-3 when schema stabilizes and migrations accumulate. A missed migration in Phase 1 can cascade silently through all later phases.

---

### CP-5: Loan State Machine Without Database Enforcement

**What goes wrong:**
Loan status transitions (`pending → approved → returned`, `pending → rejected`, `approved → overdue`) are only enforced in Python application logic. No database constraint prevents setting `status = 'returned'` on a `rejected` loan, or `status = 'approved'` on an already-`returned` loan. Invalid state transitions corrupt the borrow history.

**Why it happens:**
Simple `String` or `Enum` column without a transition guard. The state machine is implicit in the service layer, but the database accepts any valid enum value regardless of the current state.

**Consequences:**
Librarian dashboard shows confusing history. Overdue detection queries return wrong results. Available copy counts drift if the return handler is called on an already-returned loan (decrement runs twice).

**Prevention:**
- Use a PostgreSQL `CHECK` constraint or, better, enforce transitions in a dedicated service method that reads the current state before allowing the write.
- Add a `UNIQUE` constraint to prevent two active loans for the same book+student combination.
- The `available_copies` decrement/increment must be tied atomically to the state transition — never update them separately.
- Add DB-level constraint: `available_copies <= total_copies` and `available_copies >= 0`.

**Detection (warning signs):**
- Loans with `status = 'returned'` but no `returned_at` timestamp
- `available_copies > total_copies` for any book
- Student can see a loan in both "active" and "history" simultaneously

**Phase this surfaces:** Phase 2 (loan lifecycle). Often discovered during edge-case manual testing or when writing the overdue-detection query.

---

## Common Mistakes (cause rework)

These mistakes don't corrupt data but require significant refactoring to fix.

---

### CM-1: CORS Misconfiguration Between FastAPI and React Dev Server

**What goes wrong:**
The FastAPI `CORSMiddleware` is configured with `allow_origins=["*"]` during development, then tightened to a specific domain in production. The production URL is set incorrectly (missing port, wrong scheme, trailing slash), causing all API requests from the React app to fail with CORS errors in production while working fine locally.

Alternatively: `allow_credentials=True` is combined with `allow_origins=["*"]`, which browsers reject — credentials (cookies, Authorization headers) cannot be sent to a wildcard origin.

**Prevention:**
```python
# Never use * with allow_credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
Use an environment variable (`ALLOWED_ORIGINS`) for the origin list. In Docker Compose, set `ALLOWED_ORIGINS=http://localhost:5173` for dev and the real URL for prod. Never hardcode origins.

**Detection (warning signs):**
- Browser console: `Access to fetch at 'http://...' from origin 'http://...' has been blocked by CORS policy`
- API works in Postman/curl but fails from the browser
- Credentials (cookies) not being sent despite `withCredentials: true` on the frontend

**Phase this surfaces:** Phase 1 (initial API connection). Can re-surface when moving to a staging or production environment.

---

### CM-2: Blocking Email Sending in the Request Thread

**What goes wrong:**
Email notifications (borrow approved/rejected, overdue alerts) are sent synchronously inside the FastAPI endpoint handler using `smtplib` or a sync SMTP client. The endpoint blocks for 1–5 seconds waiting for the SMTP server to respond. Under load, this exhausts the worker thread pool. If the SMTP server is unavailable, the entire API request fails — the librarian gets an error when approving a loan just because the email service is down.

**Why it happens:**
Synchronous SMTP is the simplest implementation. Developers add it inline to the approval endpoint as a quick feature.

**Consequences:**
Slow endpoints. SMTP outage causes approval/rejection endpoints to return 500. Request timeouts under load.

**Prevention:**
Use FastAPI's `BackgroundTasks` for email sending:
```python
async def approve_loan(
    loan_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    loan = await approve_loan_service(db, loan_id)
    background_tasks.add_task(send_approval_email, loan.student_email, loan)
    return {"status": "approved"}
```
`BackgroundTasks` runs after the response is sent. For overdue batch emails, use a scheduled task (APScheduler or a separate cron container) — never a blocking loop in the main process.

For the async email client, use `aiosmtplib` (not `smtplib`) or an HTTP-based provider (SendGrid, Mailgun) via `httpx` async.

**Detection (warning signs):**
- Approval endpoint takes 2+ seconds even with no database load
- SMTP outage causes 500 on the approval/rejection endpoint
- `smtplib.SMTP()` anywhere in an `async def` handler

**Phase this surfaces:** Phase 3 (notification feature). Easy to write wrong the first time; refactoring to background tasks later is straightforward but requires retesting the email flow.

---

### CM-3: React State Not Reflecting Backend State After Mutations

**What goes wrong:**
A librarian approves a borrow request. The UI shows the request as still "pending" because the component's local state was not updated after the API call succeeded. Or: the available copy count shown on the book detail page is stale after a loan is approved elsewhere.

**Why it happens:**
Developers update local React state manually (e.g., filter the request out of an array) instead of refetching from the server. Manual state surgery diverges from backend truth quickly, especially with multiple concurrent librarian sessions.

**Consequences:**
Librarians see ghost pending requests. Students see wrong available copy counts. Confusing UX. Bugs that only appear with multiple simultaneous users.

**Prevention:**
Use React Query (`@tanstack/react-query`). After every mutation, invalidate the relevant queries:
```javascript
const mutation = useMutation({
  mutationFn: approveLoan,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['loans', 'pending'] });
    queryClient.invalidateQueries({ queryKey: ['books'] });
  },
});
```
Never manually splice arrays or patch objects in state after a write. Let the server be the source of truth and refetch.

**Detection (warning signs):**
- UI shows stale data after approve/reject/return actions
- Refreshing the page fixes the display issue
- `useState` arrays being manually `.filter()`-ed after mutations instead of cache invalidation

**Phase this surfaces:** Phase 2-3 (any mutation-heavy feature). Appears immediately when building the librarian dashboard.

---

### CM-4: Docker Volume Mounts Breaking Hot Reload

**What goes wrong:**
FastAPI (Uvicorn with `--reload`) and React (Vite dev server) hot reload stop working inside Docker. Changes to files don't trigger reloads. OR: the `node_modules` directory is mounted from the host, overwriting the container's installed packages (or vice versa), causing module-not-found errors.

**Why it happens:**
Two distinct sub-problems:
1. **Uvicorn `--reload` on Linux in Docker** uses `inotify`. On Windows hosts with WSL2 + bind mounts, `inotify` events are not reliably fired for changes made from the Windows side.
2. **node_modules volume collision**: mounting the entire frontend directory into the container without excluding `node_modules` causes the host's (empty or different) `node_modules` to shadow the container's installed packages.

**Prevention:**
For FastAPI hot reload on WSL2: make code changes from within WSL (not from the Windows Explorer side). Alternatively use `watchfiles` as the reload watcher (`uvicorn main:app --reload --reload-dir /app`) — it's more reliable than the default.

For node_modules: add a named Docker volume for `node_modules` to prevent the bind mount from overwriting it:
```yaml
services:
  frontend:
    volumes:
      - ./frontend:/app          # bind mount source code
      - node_modules:/app/node_modules  # named volume protects installed packages
volumes:
  node_modules:
```

**Detection (warning signs):**
- Code changes require container restart to take effect
- `Module not found` errors in the React container that don't exist locally
- `node_modules` inside container is empty or has wrong versions

**Phase this surfaces:** Phase 1 (dev environment setup). Causes ongoing friction throughout all phases if not fixed early.

---

### CM-5: Missing Indexes on High-Traffic Query Columns

**What goes wrong:**
The `loans` and `borrow_requests` tables grow to tens of thousands of rows. Queries like "all pending requests" (`WHERE status = 'pending'`), "all overdue loans" (`WHERE due_date < NOW() AND status = 'active'`), and "student's loan history" (`WHERE student_id = :id`) do full sequential scans. The librarian dashboard becomes noticeably slow.

**Prevention:**
Add indexes at migration time, not after slowness is reported:
```sql
CREATE INDEX ix_loans_status ON loans(status);
CREATE INDEX ix_loans_student_id ON loans(student_id);
CREATE INDEX ix_loans_due_date ON loans(due_date) WHERE status = 'active';
CREATE INDEX ix_books_title_gin ON books USING gin(to_tsvector('english', title || ' ' || author));
```
The last one enables full-text search on the catalog. Adding it retroactively to a large table requires a lock in older PostgreSQL versions.

**Detection (warning signs):**
- `EXPLAIN ANALYZE` shows `Seq Scan` on `loans` or `books` tables
- Dashboard load time increases linearly with data volume
- PostgreSQL slow query log entries for status-filter queries

**Phase this surfaces:** Phase 2-3 (loan management, overdue detection). Often ignored until load testing or going live with real data.

---

### CM-6: Alembic `--autogenerate` Missing Non-Model Changes

**What goes wrong:**
`alembic revision --autogenerate` does not detect: server-side defaults set outside SQLAlchemy, partial/conditional indexes, `CHECK` constraints defined in raw SQL, full-text search indexes, custom PostgreSQL types, and sequences. Developers assume autogenerate catches everything and ship migrations with missing constraints.

**Prevention:**
After autogenerate, always review the generated migration file manually before committing. For anything autogenerate misses, add it by hand in `op.execute()`:
```python
def upgrade():
    op.execute("ALTER TABLE books ADD CONSTRAINT chk_copies CHECK (available_copies >= 0 AND available_copies <= total_copies)")
    op.execute("CREATE INDEX CONCURRENTLY ix_books_fts ON books USING gin(to_tsvector('english', title || ' ' || author))")
```
Use `CREATE INDEX CONCURRENTLY` in migrations to avoid table locks on existing data.

**Detection (warning signs):**
- `CHECK` constraints exist in the model but not in `\d tablename` in psql
- Full-text search fails in production but works in dev (where `create_all` ran)
- Migration file is unexpectedly empty after a model change that added constraints

**Phase this surfaces:** Phase 1-2 (initial schema, then refinement). Constraint gaps discovered late are expensive to backfill.

---

### CM-7: Role Checking Done Only on the Frontend

**What goes wrong:**
The React app hides the "Approve Request" button from students. A student inspects the network request and calls the API directly. The FastAPI endpoint has no role check — it accepts the request and processes the approval.

**Why it happens:**
Developers implement `if (user.role === 'librarian')` in the React component and consider the feature protected. Backend role enforcement is skipped as "redundant."

**Prevention:**
Every mutation endpoint that requires librarian access must check the role on the backend:
```python
def require_librarian(current_user: User = Depends(get_current_user)):
    if current_user.role not in ("librarian", "admin"):
        raise HTTPException(status_code=403, detail="Librarian access required")
    return current_user
```
Frontend role gates are UX only, never security. Backend enforcement is mandatory.

**Detection (warning signs):**
- Student can call `POST /loans/{id}/approve` via curl and it succeeds
- No `403` response when replaying a librarian request with a student token
- Role check only appears in React component logic, not in FastAPI dependency

**Phase this surfaces:** Phase 1-2 (auth + first protected endpoints). Easy to miss on initial build, security review catches it.

---

## Minor Gotchas (easy to fix when hit)

These surface quickly, have obvious error messages, and are fixed in under an hour.

---

### MG-1: `expire_on_commit=True` Causes Lazy Load Errors After Commit

**What goes wrong:** Default `expire_on_commit=True` on the SQLAlchemy session expires all ORM attributes after `commit()`. In async context, accessing `loan.student.email` after committing raises `MissingGreenlet` because the lazy load can't execute.

**Prevention:** Set `expire_on_commit=False` on the `async_sessionmaker`. Eagerly load relationships with `selectinload()` in queries where you need related objects after commit.

---

### MG-2: Vite Proxy Not Configured for API Requests in Dev

**What goes wrong:** React dev server runs on `localhost:5173`, FastAPI on `localhost:8000`. Fetch calls to `/api/...` return 404 because they hit the Vite server, not FastAPI. Developers add the full `http://localhost:8000` URL in frontend code, then it breaks in production.

**Prevention:** Configure `vite.config.ts` proxy:
```typescript
server: {
  proxy: {
    '/api': 'http://backend:8000'  // 'backend' = Docker Compose service name
  }
}
```
All frontend code uses relative `/api/...` paths. Works in both dev and production without code changes.

---

### MG-3: Pydantic v2 Validation Behavior Breaking v1 Patterns

**What goes wrong:** FastAPI projects started in 2024+ use Pydantic v2 by default. Patterns from v1 tutorials (`orm_mode = True`, `validator` decorator, `class Config`) cause silent failures or `PydanticUserError`. `orm_mode` is now `model_config = ConfigDict(from_attributes=True)`.

**Prevention:** Use Pydantic v2 patterns from the start. If copying from a tutorial, check whether it was written for v1 or v2. Key difference: `model_config = ConfigDict(from_attributes=True)` on response schemas that serialize ORM models.

---

### MG-4: `.env` File Not Excluded From Docker Build Context

**What goes wrong:** The `.env` file (containing `SECRET_KEY`, SMTP credentials, database password) is copied into the Docker image via `COPY . .` in the Dockerfile. If the image is pushed to a registry, secrets are exposed.

**Prevention:** Add `.env` to `.dockerignore`. Pass secrets via Docker Compose `env_file:` directive or environment variables, not baked into the image.

---

### MG-5: Missing `PYTHONDONTWRITEBYTECODE` and `PYTHONUNBUFFERED` in Docker

**What goes wrong:** Python writes `.pyc` cache files into the mounted source volume (polluting the host filesystem). Stdout/stderr logs are buffered and don't appear in `docker logs` in real time, making debugging confusing.

**Prevention:** Set in Dockerfile:
```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
```

---

### MG-6: Returning SQLAlchemy ORM Objects Directly From Endpoints

**What goes wrong:** A FastAPI endpoint returns an ORM model instance directly. FastAPI attempts JSON serialization, hits lazy-loaded relationships, and raises `MissingGreenlet` or returns partial data. Or, internal fields (e.g., `hashed_password`) are exposed in the response.

**Prevention:** Always define Pydantic response schemas (`response_model=`) for every endpoint. Never return raw ORM objects. The response schema also enforces that sensitive fields like `hashed_password` are excluded.

---

### MG-7: Overdue Detection Running on Every Request

**What goes wrong:** The overdue status check (`UPDATE loans SET status='overdue' WHERE due_date < NOW()`) runs inside the endpoint handler for "get my loans" — updating state as a side effect of a read. Under load, every student page load triggers a write transaction.

**Prevention:** Run overdue detection as a scheduled background job (APScheduler inside FastAPI startup, or a separate cron container). Store the overdue flag in the database. Endpoints only read; they do not compute and write state.

---

### MG-8: PostgreSQL Password With Special Characters Breaking Connection String

**What goes wrong:** `DATABASE_URL=postgresql+asyncpg://user:p@ssw0rd!@db:5432/library` — the `@` and `!` in the password break URL parsing. The connection fails with a cryptic `invalid dsn` error.

**Prevention:** Always URL-encode special characters in the database password, or use `sqlalchemy.engine.url.URL.create()` to construct the connection URL programmatically from separate host/user/password components rather than a single string.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Phase 1: Auth & session setup | CP-2 (shared async session), CP-3 (JWT never expires), CM-7 (backend role check missing) | Set up session factory, token expiry, and role dependency from day one |
| Phase 1: Docker dev environment | CM-4 (hot reload broken), MG-4 (.env in image), MG-5 (buffered logs) | Add `.dockerignore`, named volume for `node_modules`, set ENV flags |
| Phase 1: Database scaffolding | CP-4 (migration drift), MG-6 (ORM objects returned directly) | Alembic-first from day one; define all response schemas |
| Phase 2: Book catalog | CM-5 (missing indexes), MG-2 (Vite proxy) | Add GIN index for full-text search at schema creation time |
| Phase 2: Borrow request flow | CP-1 (concurrent borrow race), CP-5 (state machine enforcement), CM-3 (stale React state) | `SELECT FOR UPDATE`, DB `CHECK` constraint, React Query invalidation |
| Phase 3: Loan lifecycle & returns | CP-5 (double return decrement), CM-2 (blocking email), MG-7 (overdue on read) | Atomic state transitions, BackgroundTasks for email, scheduled job for overdue |
| Phase 3: Notifications | CM-2 (blocking SMTP), MG-7 (overdue on read path) | aiosmtplib + BackgroundTasks; APScheduler for batch overdue emails |
| Deployment / staging | CM-1 (CORS tightening), MG-4 (.env in image), CP-4 (migration not run) | ALLOWED_ORIGINS env var, .dockerignore, alembic upgrade in entrypoint |

---

## Sources

- Confidence level: HIGH — all pitfalls reflect recurring, well-documented issues in the FastAPI/SQLAlchemy/React/PostgreSQL ecosystem as of 2025-2026.
- FastAPI official docs: async session patterns, BackgroundTasks, CORS middleware
- SQLAlchemy 2.0 docs: async session lifecycle, `expire_on_commit`, `with_for_update()`
- Alembic docs: autogenerate limitations (server defaults, partial indexes, custom types)
- PostgreSQL docs: `SELECT FOR UPDATE`, `CHECK` constraints, `CREATE INDEX CONCURRENTLY`
- Pydantic v2 migration guide: `model_config`, `from_attributes`
- React Query docs: query invalidation after mutations
- Docker docs: named volumes, `dockerignore`, environment variable injection
