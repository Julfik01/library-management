# University Library Management System

## What This Is

A web-based library management system for a university. Students can search the book catalog, submit borrow requests, and track their borrowed items and due dates. Librarians can manage the catalog, approve or reject borrow requests, record returns, and monitor overdue items through a dashboard.

## Core Value

A student can find a book, request to borrow it, and track when it's due — and a librarian can process that request and manage the full borrow lifecycle end-to-end.

## Requirements

### Validated

(None yet — ship to validate)

### Active

**Authentication & Accounts**
- [ ] Student can self-register with email and password
- [ ] Librarian accounts are created by an admin (elevated librarian role)
- [ ] Any user can log in with email and password and stay logged in across sessions
- [ ] Any user can log out

**Book Catalog**
- [ ] Librarian can add a book with title, author, ISBN, category/genre, publisher, year, cover image, and total copy count
- [ ] Librarian can edit book details
- [ ] Librarian can remove a book from the catalog
- [ ] Student and librarian can search the catalog by title, author, ISBN, or category
- [ ] Catalog shows available copy count per book

**Borrow Requests**
- [ ] Student can submit a borrow request for an available book
- [ ] Librarian can approve or reject a pending borrow request
- [ ] Approved request sets a 14-day loan period; no renewals
- [ ] Student is notified (email) when their request is approved or rejected

**Returns & Overdue**
- [ ] Librarian can record a book return and update available count
- [ ] System flags loans as overdue after 14 days; no monetary fines
- [ ] Librarian dashboard shows all overdue items
- [ ] Student receives email alert when their loan becomes overdue

**Student Self-Service**
- [ ] Student can view their active loans and due dates
- [ ] Student can view their borrow request history (pending, approved, rejected)

### Out of Scope

- University SSO / LDAP / SAML — custom auth is sufficient for v1
- Late fees or fines — overdue is flagged only, no monetary penalty
- Loan renewals — return and re-request if needed
- Per-copy tracking (barcodes, shelf location per copy) — count-based model is sufficient
- Mobile app — web only
- Bulk import of users from CSV — self-registration covers v1

## Context

- **Stack**: FastAPI (Python) backend, React frontend, PostgreSQL database, Docker for local dev and deployment
- **Roles**: Two user types — Student (borrower) and Librarian (admin). A special "admin librarian" can create other librarian accounts
- **Copy model**: Each book title tracks total copies and available copies. No per-copy identity
- **Loan model**: 14 days from approval date. No renewals. Overdue = past due date, no fine
- **Notifications**: Email only (overdue alerts, borrow request status updates). Not real-time in-app

## Constraints

- **Tech Stack**: FastAPI + React + PostgreSQL + Docker — decided, no alternatives considered
- **Auth**: Custom email/password with JWT — no SSO integration for v1
- **Borrow Period**: Fixed 14 days — no configurable loan periods in v1
- **Scope**: University context — no public or multi-institution access

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Custom email/password auth | Simpler to build; no dependency on university IT systems | — Pending |
| Count-based copy tracking (not per-copy) | Reduces schema complexity; sufficient for typical university library scale | — Pending |
| No fines | Reduces payment infrastructure scope; enforcement handled manually | — Pending |
| Docker for dev + deployment | Reproducible environment; consistent local/production parity | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-10 after initialization*
