# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-10
**Phase:** 1-Foundation
**Areas discussed:** Schema scope on day one

---

## Schema Scope on Day One

### Full schema upfront vs. per-phase migrations

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — all tables upfront | One authoritative baseline migration. Phases 2–5 add data and endpoints but never add tables or alter schema. Prevents 'schema drift' across phases and matches ROADMAP intent. | ✓ |
| No — just auth tables now | Phase 1 creates users/sessions/roles only. Later phases add their own tables via new migrations. Lighter Phase 1, but schema is spread across phases. | |

**User's choice:** All tables upfront — single baseline migration

---

### Migration organization

| Option | Description | Selected |
|--------|-------------|----------|
| One single migration — all tables in one file | A single `001_initial_schema.py` creates every table, FK, index, and constraint. Simple to review, easy to reason about dependencies, atomic rollback. | ✓ |
| One migration per domain | Separate files: 001_auth.py, 002_books.py, 003_loans.py. Tables have FK dependencies, so ordering still matters and diffing across files is harder. | |
| You decide | Leave migration organization to the planner. | |

**User's choice:** Single migration file

---

### users table: include full_name?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — include full_name | Phase 4 requires searching loans by 'student name' — full_name needs to exist somewhere. Capturing at registration is the natural place. | ✓ |
| No — email only for now | Omit full_name; Phase 4 search would use email. Simpler schema but changes what 'student name' means. | |

**User's choice:** Include full_name on users table

---

### refresh_token_blocklist table

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — include from day one | AUTH-04 requires server-side refresh token invalidation on logout. The table must exist before any auth endpoint is live. | ✓ |
| No — simpler invalidation strategy | Skip the blocklist; invalidate by deleting the cookie only (less secure). | |

**User's choice:** Include refresh_token_blocklist in Phase 1 migration

---

### Status field type: ENUMs vs VARCHAR CHECK

| Option | Description | Selected |
|--------|-------------|----------|
| VARCHAR + CHECK constraints | Simpler to add new values later (no ALTER TYPE needed), easier in Alembic migrations, readable in pg_dump. | ✓ |
| PostgreSQL native ENUMs | Enforced at DB type level, slightly faster lookup. But ALTER TYPE can't run inside a transaction and Alembic handling is fiddly. | |

**User's choice:** VARCHAR + CHECK constraints for all status fields

---

### overdue_notified_at on loans table

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — overdue_notified_at on loans table | NULL = not yet notified; timestamp = notified. APScheduler checks overdue AND IS NULL → send + set. Idempotent, no extra table. | ✓ |
| Separate notifications table | More general, reusable for other email types, but adds schema complexity for a single-column use case. | |

**User's choice:** overdue_notified_at TIMESTAMPTZ on loans table

---

### Index strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Essential indexes now | Add obviously-needed indexes: UNIQUE on users.email, UNIQUE on books.isbn, index on loans.due_date, index on borrow_requests.status. Skip speculative tuning indexes. | ✓ |
| Constraints only for now | Just unique constraints and FKs in Phase 1. Add query-specific indexes as features are built. | |
| You decide | Leave index strategy to the planner. | |

**User's choice:** Essential indexes now

---

### GIN full-text index timing

| Option | Description | Selected |
|--------|-------------|----------|
| Add GIN index in Phase 1 migration | 'Full schema from day one' means indexes too. No downside — an index on an empty table has zero cost. | ✓ |
| Wait until Phase 2 | GIN index is a Phase 2 concern since that's when search is built. | |

**User's choice:** GIN index in Phase 1 migration alongside all other indexes

---

## Claude's Discretion

- Specific index naming convention — use SQLAlchemy/Alembic conventions
- Password column name — follow FastAPI docs convention (`hashed_password`)
- `role` column implementation detail — VARCHAR CHECK vs. separate roles table (VARCHAR CHECK preferred for simplicity)
- React in-memory token store (React Context vs. module-level variable) — Context preferred for testability

## Deferred Ideas

None raised during discussion.
