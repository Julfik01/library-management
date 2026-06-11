# Phase 03 Plan — Borrow Lifecycle

Last updated: 2026-06-11
Phase: 03 — Borrow Lifecycle (BORROW-01 – BORROW-07, LOAN-01)

Goal
- Implement end-to-end borrow lifecycle: student borrow requests, librarian approval/rejection, automatic loan creation, return flow, and nightly overdue detection/notification.

Scope (in-scope)
- POST /borrow-requests (student)
- GET /borrow-requests?status=pending (librarian)
- POST /borrow-requests/{id}/approve and /reject (librarian)
- POST /loans/{id}/return (student/librarian)
- GET /loans (student: own; librarian: all)
- APScheduler overdue job marking overdue and sending one-time notification
- Business rules: MAX_CONCURRENT_LOANS = 5; atomic approval transaction using SELECT FOR UPDATE; idempotent return and overdue notification

Out of scope
- Catalog UI polish, cover image fallbacks (Phase 2)
- Multi-instance APScheduler dedupe (Phase 5)

Deliverables
- backend: routers, schemas, services, overdue job
- frontend: request button, librarian approve queue, loans pages
- tests: unit + concurrency tests
- docs: API snippets in README and CONTEXT.md (already written)

Work breakdown (tasks, owner, estimate)
1. Backend: borrow_requests router + schemas + service — 6h
   - Create backend/app/routers/borrow_requests.py
   - Create backend/app/schemas/borrow_request.py
   - Implement approve/reject endpoints with require_role('librarian')
   - Service: transactional approval (SELECT FOR UPDATE book row), max-loans check, loan creation
   - Tests: basic approval/reject flow, 409 on no copies, 409 on max loans

2. Backend: loans router + schemas + service — 5h
   - Create backend/app/routers/loans.py
   - Create backend/app/schemas/loan.py
   - Implement return endpoint (idempotent), list endpoint with role filtering
   - Tests: return idempotency, available_copies increment

3. Backend: overdue job wiring (APScheduler) — 2h
   - Create backend/app/tasks/overdue_jobs.py
   - Hook into startup event in backend/app/main.py to add job
   - Tests: overdue job marks and sends notification once (uses MailHog)

4. Frontend: API helpers + BookDetail request button — 3h
   - frontend/src/lib/api/borrow.ts
   - BookDetailPage: Request Borrow button, flows for success/error
   - Use AuthContext to require student

5. Frontend: Librarian ApproveRequestsPage + LoansPage — 4h
   - Approve/reject UI with optimistic refresh
   - Student LoansPage with Return action (confirm modal)

6. Testing & E2E verification — 3h
   - Concurrency simulation for approval race (two parallel approval attempts)
   - Run migrations, start services, manual E2E: request→approve→loan→return

Total estimate: 23 hours (3 working days)

Branching & commit guidance
- Branch name: feature/phase-03-borrow-lifecycle
- Make small commits per task (router, service, tests). Include Co-authored-by trailer in commits (Copilot). Run tests before pushing.

Verification & Acceptance Criteria
- Unit tests pass for approval, return, max-loans, and overdue job
- Manual E2E: Student requests a book, librarian approves, loan appears, due_date=now+14d, available_copies decremented; student/librarian return increments copies; overdue job marks overdue and sends one email
- No race condition: concurrent approvals cannot reduce available_copies below 0; one approval wins, other receives 409

Risk & Mitigation
- Race on approval: use SELECT FOR UPDATE on book row and borrow_request row in same transaction
- APScheduler multi-instance: document constraint in STATE.md; single replica only for v1

Next steps
- Start Task 1 (backend borrow_requests). Update todo status to in_progress and begin implementation.

