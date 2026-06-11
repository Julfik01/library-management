# Phase 03 Context — Borrow Lifecycle

Last updated: 2026-06-11
Phase: 03 — Borrow Lifecycle
Scope: BORROW-01 – BORROW-07, LOAN-01

Summary
- Purpose: Implement student borrow request → librarian approval/rejection → loan creation → return flow and overdue sentinel.
- Constraints already decided: 14-day fixed loan period, DB schema present for borrow_requests and loans, SELECT FOR UPDATE concurrency pattern from Phase 1, APScheduler for overdue job, email via BackgroundTasks/MailHog in dev.

Key Decisions (resolved for downstream agents)
1. Approval creates the Loan automatically (approved → create Loan record, set loan_date=now, due_date=now+14d). Rationale: reduces steps for librarians and avoids orphan approved requests.
2. Reserve copies on approval (not on request). Book.available_copies is decremented inside the approval transaction with SELECT FOR UPDATE on the book row. If available_copies==0 at approval time, approval fails with 409 and borrow_request remains pending.
3. Who can mark returned: both the owning student (authenticated, must match loan.student_id) and librarians may mark a loan returned via POST /loans/{id}/return. Returned action sets returned_at, status='returned', increments book.available_copies inside a transaction. Idempotency: if returned_at already set, return is a no-op (200).
4. Max concurrent loans per student: enforce MAX_CONCURRENT_LOANS = 5 (config constant). Approval must check count of active loans for student < limit; otherwise respond 409 with explanatory message.
5. Overdue detection: nightly job queries loans with due_date < now AND status='active' and sets status='overdue' and sends email once using overdue_notified_at sentinel (already present). Job must be idempotent (set overdue_notified_at only on first send).
6. Error handling: approval is atomic — borrow_request.status and book.available_copies and loan creation must be in single DB transaction (SELECT FOR UPDATE on book record and borrow_request row).

API contract (minimal)
- POST /borrow-requests (student) -> {book_id} => 201 borrow_request
- GET /borrow-requests?status=pending (librarian) -> list
- POST /borrow-requests/{id}/approve (librarian) -> 200 {loan_id} or 409 on conflict
- POST /borrow-requests/{id}/reject (librarian) -> 200
- GET /loans (student: own loans; librarian: all) -> list
- POST /loans/{id}/return (student/librarian) -> 200

Impacted backend files (to read/update/create)
- backend/app/models/borrow_request.py (exists)
- backend/app/models/loan.py (exists)
- backend/alembic/versions/001_initial_schema.py (exists)
- backend/app/routers/borrow_requests.py (create)
- backend/app/routers/loans.py (create)
- backend/app/schemas/borrow_request.py (create)
- backend/app/schemas/loan.py (create)
- backend/app/services/borrow_service.py (create) — approval logic, SELECT FOR UPDATE, loan creation
- backend/app/services/loan_service.py (create) — return, overdue handling
- backend/app/tasks/overdue_jobs.py (create) — APScheduler job wiring
- backend/tests/test_borrow_requests.py (create)

Impacted frontend areas (to create/update)
- frontend/src/pages/BookDetailPage.tsx — Add "Request Borrow" button (student)
- frontend/src/pages/Librarian/ApproveRequestsPage.tsx — pending queue, approve/reject actions
- frontend/src/pages/LoansPage.tsx — student's loans and return action
- frontend/src/lib/api/borrow.ts — API client helpers
- frontend/src/context/AuthContext.tsx — already exists; use for auth checks

Open questions (resolved)
- Cover image placeholder: deferred (Phase 2 concern).
- Multi-instance APScheduler risk: documented in STATE.md (deferred until Phase 5).

Acceptance criteria for Phase 3
- Students can create borrow requests.
- Librarians can view pending requests and approve/reject.
- Approving auto-creates a Loan, decrements available_copies safely, and enforces max concurrent loans.
- Students and librarians can mark loans returned; returned loans increment copies and set returned_at.
- Overdue job marks overdue loans and sends one notification.
- Unit tests cover approval race, max-loans enforcement, return idempotency, and overdue job behavior.

Minimal task list (prioritized)
1. Implement backend borrow_requests router + schemas + service (approval/reject endpoints) — includes transaction safety and max-loans check.
2. Implement backend loans router + schemas + service (list, return) and overdue job wiring.
3. Add API client helpers in frontend + BookDetail "Request Borrow" button and Loans/Librarian pages.
4. Add unit tests for borrow/loan flows and DB transaction tests for concurrent approvals.
5. Manual verification: run Alembic migration, start services, perform end-to-end: request → approve → loan appears → return → copies updated.

Notes for implementers
- Use existing patterns from Phase 1 (require_role dependency for librarian endpoints, DbSession usage, password hashing is irrelevant here).
- Use async SQLAlchemy session; prefer transactional pattern in services: async with db.begin(): await db.execute(select(...).with_for_update()) ...
- Return clear HTTP 409 on business rule violations (no copies, max loans reached).

Deliverable: this CONTEXT.md + the tasks above. Planner and implementer agents may proceed without further questions unless they hit a domain edge-case not covered here.
