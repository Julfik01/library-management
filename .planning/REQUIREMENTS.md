# Requirements: University Library Management System

**Defined:** 2026-06-10
**Core Value:** A student can find a book, request to borrow it, and track when it's due — and a librarian can process that request and manage the full borrow lifecycle end-to-end.

## v1 Requirements

### Authentication & Accounts

- [x] **AUTH-01**: Student can self-register with email and password
- [x] **AUTH-02**: Any user can log in with email and password
- [x] **AUTH-03**: Session persists across page refreshes via httpOnly refresh token cookie + in-memory access token
- [x] **AUTH-04**: Any user can log out; refresh token is invalidated server-side
- [x] **AUTH-05**: Admin librarian account is seeded via Alembic migration (credentials from environment variables)
- [x] **AUTH-06**: Admin librarian can create librarian accounts
- [x] **AUTH-07**: Backend enforces role-based access on all protected endpoints (student vs librarian vs admin librarian)

### Book Catalog

- [ ] **CAT-01**: Librarian can add a book with title, author, ISBN, category/genre, publisher, year, and total copy count
- [ ] **CAT-02**: System auto-fetches cover image from Open Library API by ISBN when a book is added
- [ ] **CAT-03**: Librarian can edit any book's details and copy count
- [ ] **CAT-04**: Librarian can remove a book from the catalog (blocked if active loans exist for that book)
- [ ] **CAT-05**: Any authenticated user can search the catalog by title, author, ISBN, or category
- [ ] **CAT-06**: Search results display available copy count per book
- [ ] **CAT-07**: Book detail page shows full metadata, cover image, availability status, and a Request to Borrow button (disabled if 0 copies available or student already has a pending/active loan for that book)
- [ ] **CAT-08**: Catalog search results are paginated

### Borrow Requests

- [ ] **BORROW-01**: Student can submit a borrow request for a book with at least 1 available copy
- [ ] **BORROW-02**: System prevents duplicate requests — a student cannot submit a new request for a book they already have a pending or active loan for
- [ ] **BORROW-03**: Student can view all their borrow requests with current status (pending, approved, rejected)
- [ ] **BORROW-04**: Librarian sees a paginated queue of all pending borrow requests with inline Approve and Reject actions
- [ ] **BORROW-05**: Librarian can approve a request — atomically decrements available_copies and creates a loan with a 14-day due date from approval date
- [ ] **BORROW-06**: Librarian can reject a request with an optional rejection note
- [ ] **BORROW-07**: Student receives an email notification when their request is approved or rejected (rejection note included if present)

### Loan Management & Returns

- [ ] **LOAN-01**: Librarian can record a book return — atomically increments available_copies and marks the loan as returned
- [ ] **LOAN-02**: Student can view all their active loans with due dates and an explicit overdue visual indicator
- [ ] **LOAN-03**: Student can view their full borrow history (all past loans, including returned)
- [ ] **LOAN-04**: Librarian can search all loans by student name or book title
- [ ] **LOAN-05**: Loan list views are paginated

### Overdue Detection & Notifications

- [ ] **OVERDUE-01**: System automatically flags loans as overdue via a nightly scheduled job (APScheduler) — no monetary fine, status flag only
- [ ] **OVERDUE-02**: Student receives one email alert when their loan first becomes overdue
- [ ] **OVERDUE-03**: Librarian dashboard shows all overdue loans sorted by most-days-overdue first
- [ ] **OVERDUE-04**: Student's active loans view shows an explicit overdue badge/indicator (not only reliant on email)

## v2 Requirements

### Waitlists & Availability Alerts

- **WAIT-01**: Student can join a waitlist for a book with 0 available copies
- **WAIT-02**: Student is notified when a waitlisted book becomes available

### Advanced Catalog Features

- **ADVCAT-01**: Catalog supports multi-select genre filter and availability toggle
- **ADVCAT-02**: Cover image upload option (librarian uploads file instead of relying on Open Library)

### Librarian Analytics

- **STAT-01**: Librarian can view catalog statistics (most borrowed titles, overdue rate)
- **STAT-02**: Admin librarian can view system-wide usage summary

### Loan Renewals

- **RENEW-01**: Student can request a loan renewal once if no pending requests exist for the book

## Out of Scope

| Feature | Reason |
|---------|--------|
| University SSO / LDAP / SAML | Custom auth is sufficient for v1; SSO requires IT coordination |
| Late fees or fines | No payment infrastructure; enforcement is manual/policy-based |
| Per-copy tracking (barcodes, shelf location) | Count-based model is sufficient for a single-location university library |
| Mobile app | Web-first; mobile can be added post-v1 |
| Bulk user import from CSV | Self-registration covers v1 onboarding needs |
| Real-time in-app notifications | Email notifications are sufficient; WebSocket adds complexity |
| Multi-institution / multi-branch | Single university scope only |
| Public (unauthenticated) catalog browsing | Requires authentication to request books anyway; auth gate on search is acceptable |

## Traceability

*Updated: 2026-06-10 after roadmap creation.*

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| AUTH-04 | Phase 1 | Complete |
| AUTH-05 | Phase 1 | Complete |
| AUTH-06 | Phase 1 | Complete |
| AUTH-07 | Phase 1 | Complete |
| CAT-01 | Phase 2 | Pending |
| CAT-02 | Phase 2 | Pending |
| CAT-03 | Phase 2 | Pending |
| CAT-04 | Phase 2 | Pending |
| CAT-05 | Phase 2 | Pending |
| CAT-06 | Phase 2 | Pending |
| CAT-07 | Phase 2 | Pending |
| CAT-08 | Phase 2 | Pending |
| BORROW-01 | Phase 3 | Pending |
| BORROW-02 | Phase 3 | Pending |
| BORROW-03 | Phase 3 | Pending |
| BORROW-04 | Phase 3 | Pending |
| BORROW-05 | Phase 3 | Pending |
| BORROW-06 | Phase 3 | Pending |
| BORROW-07 | Phase 3 | Pending |
| LOAN-01 | Phase 3 | Pending |
| LOAN-02 | Phase 4 | Pending |
| LOAN-03 | Phase 4 | Pending |
| LOAN-04 | Phase 4 | Pending |
| LOAN-05 | Phase 4 | Pending |
| OVERDUE-01 | Phase 5 | Pending |
| OVERDUE-02 | Phase 5 | Pending |
| OVERDUE-03 | Phase 5 | Pending |
| OVERDUE-04 | Phase 5 | Pending |

**Coverage:**

- v1 requirements: 31 total
- Mapped to phases: 31 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-10*
*Last updated: 2026-06-10 after roadmap creation*
