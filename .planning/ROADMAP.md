# Roadmap: University Library Management System

**Phases:** 5 | **Requirements:** 31 | **Coverage:** 100% ✓

---

## Phase Overview

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|-----------------|
| 1 | Foundation | Authenticated access with role enforcement | AUTH-01 – AUTH-07 | 5 criteria |
| 2 | Book Catalog | Librarians manage books; students browse and find them | CAT-01 – CAT-08 | 5 criteria |
| 3 | Borrow Lifecycle | Students request books; librarians approve, reject, and record returns | BORROW-01 – BORROW-07, LOAN-01 | 5 criteria |
| 4 | Loan Views & History | Students track loans and history; librarians search across all loans | LOAN-02 – LOAN-05 | 4 criteria |
| 5 | Notifications & Overdue | Automated overdue detection and email alerts for students and librarians | OVERDUE-01 – OVERDUE-04 | 4 criteria |

---

## Phase Details

### Phase 1: Foundation

**Goal:** Any user can register, log in, and be routed to a role-appropriate view — and the full database schema with all constraints is in place from day one.
**Mode:** mvp
**Depends on:** Nothing (first phase)
**Requirements:** AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, AUTH-06, AUTH-07

**Success Criteria** (what must be TRUE when this phase completes):

1. A new student can register with email and password and immediately log in without admin intervention.
2. A logged-in user stays logged in across browser refreshes without re-entering credentials.
3. A user who logs out cannot access protected pages until they log in again, and their session is invalidated server-side.
4. The seeded admin librarian account can log in and create a new librarian account from the admin UI.
5. Calling any librarian or admin endpoint as a student returns 403 Forbidden — role enforcement is backend-enforced, not frontend-only.

**Requirements Detail:**

- AUTH-01: Student can self-register with email and password
- AUTH-02: Any user can log in with email and password
- AUTH-03: Session persists across page refreshes via httpOnly refresh token cookie + in-memory access token
- AUTH-04: Any user can log out; refresh token is invalidated server-side
- AUTH-05: Admin librarian account is seeded via Alembic migration (credentials from environment variables)
- AUTH-06: Admin librarian can create librarian accounts
- AUTH-07: Backend enforces role-based access on all protected endpoints (student vs librarian vs admin librarian)
**Plans:** 4 plans
**Wave 1**

- [ ] 01-01-PLAN.md — Dev stack + async data layer + full 5-phase schema migration + admin seed (AUTH-05)

**Wave 2** *(blocked on Wave 1 completion)*

- [ ] 01-02-PLAN.md — Auth API: register, login, refresh, logout, RBAC, admin create-librarian (AUTH-01–04, 06, 07)

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01-03-PLAN.md — Frontend scaffold + auth context/axios + Login/Register/Dashboard slice (AUTH-01–03)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 01-04-PLAN.md — Create Librarian + Unauthorized screens + RBAC verification (AUTH-06, 07)

**UI hint:** yes

---

### Phase 2: Book Catalog

**Goal:** Librarians can manage the full book catalog, and any authenticated user can search, browse, and view book details with live availability.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** CAT-01, CAT-02, CAT-03, CAT-04, CAT-05, CAT-06, CAT-07, CAT-08

**Success Criteria** (what must be TRUE when this phase completes):

1. A librarian can add a book with all required fields, and a cover image is automatically fetched from Open Library by ISBN.
2. A librarian can edit a book's details and copy count, and can delete a book — but deletion is blocked with a clear error if the book has active loans.
3. A student can search by title, author, ISBN, or category and see paginated results, each showing the available copy count.
4. A student can open a book detail page that shows full metadata, cover image, and availability — with a "Request to Borrow" button that is disabled when 0 copies are available.
5. A student who already has a pending or active loan for a book sees the "Request to Borrow" button disabled on that book's detail page.

**Requirements Detail:**

- CAT-01: Librarian can add a book with title, author, ISBN, category/genre, publisher, year, and total copy count
- CAT-02: System auto-fetches cover image from Open Library API by ISBN when a book is added
- CAT-03: Librarian can edit any book's details and copy count
- CAT-04: Librarian can remove a book from the catalog (blocked if active loans exist for that book)
- CAT-05: Any authenticated user can search the catalog by title, author, ISBN, or category
- CAT-06: Search results display available copy count per book
- CAT-07: Book detail page shows full metadata, cover image, availability status, and a Request to Borrow button (disabled if 0 copies available or student already has a pending/active loan for that book)
- CAT-08: Catalog search results are paginated

**Plans:** TBD
**UI hint:** yes

---

### Phase 3: Borrow Lifecycle

**Goal:** A student can submit a borrow request, a librarian can approve or reject it, and a librarian can record a return — all with correct copy-count accounting and duplicate prevention.
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** BORROW-01, BORROW-02, BORROW-03, BORROW-04, BORROW-05, BORROW-06, BORROW-07, LOAN-01

**Success Criteria** (what must be TRUE when this phase completes):

1. A student can submit a borrow request for a book with at least 1 available copy, and the system rejects a duplicate request if the student already has a pending or active loan for that book.
2. A librarian sees a paginated queue of all pending borrow requests with inline Approve and Reject actions visible per request.
3. When a librarian approves a request, the book's available copy count decrements by 1 and a loan is created with a due date exactly 14 days from the approval date.
4. When a librarian rejects a request with an optional note, the request status updates to rejected and the available copy count is unchanged.
5. When a librarian records a return, the book's available copy count increments by 1 and the loan is marked as returned — with no negative copy count possible even under concurrent approvals.

**Requirements Detail:**

- BORROW-01: Student can submit a borrow request for a book with at least 1 available copy
- BORROW-02: System prevents duplicate requests — a student cannot submit a new request for a book they already have a pending or active loan for
- BORROW-03: Student can view all their borrow requests with current status (pending, approved, rejected)
- BORROW-04: Librarian sees a paginated queue of all pending borrow requests with inline Approve and Reject actions
- BORROW-05: Librarian can approve a request — atomically decrements available_copies and creates a loan with a 14-day due date from approval date
- BORROW-06: Librarian can reject a request with an optional rejection note
- BORROW-07: Student receives an email notification when their request is approved or rejected (rejection note included if present)
- LOAN-01: Librarian can record a book return — atomically increments available_copies and marks the loan as returned

**Plans:** TBD
**UI hint:** yes

---

### Phase 4: Loan Views & History

**Goal:** Students can see all their active loans and full borrow history, and librarians can search and paginate across all loans.
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** LOAN-02, LOAN-03, LOAN-04, LOAN-05

**Success Criteria** (what must be TRUE when this phase completes):

1. A student can view all their active loans showing the book title, due date, and an explicit overdue visual indicator for any loan past its due date.
2. A student can view their full borrow history including returned loans and their outcomes.
3. A librarian can search all loans by student name or book title and see matching results.
4. All loan list views — for students and librarians — are paginated so large histories load without performance issues.

**Requirements Detail:**

- LOAN-02: Student can view all their active loans with due dates and an explicit overdue visual indicator
- LOAN-03: Student can view their full borrow history (all past loans, including returned)
- LOAN-04: Librarian can search all loans by student name or book title
- LOAN-05: Loan list views are paginated

**Plans:** TBD
**UI hint:** yes

---

### Phase 5: Notifications & Overdue Detection

**Goal:** The system automatically detects overdue loans nightly and notifies students by email, and librarians have a dashboard showing all overdue items.
**Mode:** mvp
**Depends on:** Phase 4
**Requirements:** OVERDUE-01, OVERDUE-02, OVERDUE-03, OVERDUE-04

**Success Criteria** (what must be TRUE when this phase completes):

1. A nightly scheduled job runs automatically and marks any loan past its due date as overdue — no manual librarian action required.
2. A student whose loan becomes overdue receives exactly one email alert the first time the overdue flag is set — not on every subsequent scheduler run.
3. The librarian overdue dashboard lists all overdue loans sorted by most-days-overdue first, so the longest-outstanding items are immediately visible.
4. A student viewing their active loans sees an explicit overdue badge or indicator on any overdue loan — the visual status does not depend solely on email delivery.

**Requirements Detail:**

- OVERDUE-01: System automatically flags loans as overdue via a nightly scheduled job (APScheduler) — no monetary fine, status flag only
- OVERDUE-02: Student receives one email alert when their loan first becomes overdue
- OVERDUE-03: Librarian dashboard shows all overdue loans sorted by most-days-overdue first
- OVERDUE-04: Student's active loans view shows an explicit overdue badge/indicator (not only reliant on email)

**Plans:** TBD
**UI hint:** yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/4 | Not started | — |
| 2. Book Catalog | 0/? | Not started | — |
| 3. Borrow Lifecycle | 0/? | Not started | — |
| 4. Loan Views & History | 0/? | Not started | — |
| 5. Notifications & Overdue Detection | 0/? | Not started | — |

---

## Requirement Coverage

| Requirement | Phase |
|-------------|-------|
| AUTH-01 | 1 |
| AUTH-02 | 1 |
| AUTH-03 | 1 |
| AUTH-04 | 1 |
| AUTH-05 | 1 |
| AUTH-06 | 1 |
| AUTH-07 | 1 |
| CAT-01 | 2 |
| CAT-02 | 2 |
| CAT-03 | 2 |
| CAT-04 | 2 |
| CAT-05 | 2 |
| CAT-06 | 2 |
| CAT-07 | 2 |
| CAT-08 | 2 |
| BORROW-01 | 3 |
| BORROW-02 | 3 |
| BORROW-03 | 3 |
| BORROW-04 | 3 |
| BORROW-05 | 3 |
| BORROW-06 | 3 |
| BORROW-07 | 3 |
| LOAN-01 | 3 |
| LOAN-02 | 4 |
| LOAN-03 | 4 |
| LOAN-04 | 4 |
| LOAN-05 | 4 |
| OVERDUE-01 | 5 |
| OVERDUE-02 | 5 |
| OVERDUE-03 | 5 |
| OVERDUE-04 | 5 |

**Mapped:** 31/31 ✓ — No orphaned requirements.

---
*Roadmap created: 2026-06-10*
