# PLAN — Phase 2

Overview

Goal: Deliver the Phase 2 MVP that enables authenticated users to search the catalog, borrow and return books, and allow admins to manage inventory. Include tests and verification criteria to make the releaseable.

MVP Scope
- User authentication (login/register) with JWT
- Book search (title, author, ISBN) with pagination
- Borrow/Return workflows (availability checks, transaction records)
- Admin: add/edit/remove books
- Unit and integration tests for above flows

Stretch goals
- Email notifications for due books
- Reporting dashboard (borrow counts, overdue list)
- Role-based permissions beyond admin/user

User Stories & Acceptance Criteria
1) As a user, I can register/login.
   - AC: register returns 201 and JWT; login returns JWT and user profile.
2) As a user, I can search books by title/author/ISBN.
   - AC: search returns matching books, supports pagination, hit rate < 500ms on local env.
3) As a user, I can borrow an available book.
   - AC: borrow request succeeds only if available; availability decreases; transaction recorded.
4) As a user, I can return a borrowed book.
   - AC: return marks book available and records return timestamp.
5) As an admin, I can manage book records.
   - AC: CRUD endpoints for books with validation and tests.

Task Breakdown (suggested)
- Auth: endpoints, JWT handling, tests — 3d
- Search: API, query layer, tests — 3d
- Borrow/Return: domain logic, transactions, tests — 4d
- Admin CRUD: endpoints + validation — 2d
- Integration tests + CI adjustments — 2d
- Docs + release notes — 1d

Verification & Tests
- Unit tests for services and models (target 80% coverage on changed modules)
- Integration tests for end-to-end flows (auth → search → borrow → return)
- Manual UAT checklist: signup, search, borrow, return, admin CRUD

Deliverables
- .planning/phase-2/PLAN.md (this file)
- Feature branches per story, PRs with tests
- CI passing on merge to main

Timeline
- Estimated: 2 sprints (2 weeks each) for MVP + small stretch items; adjust after first sprint.

Next steps
- Review and adjust scope/estimates.
- Assign owners and create issues/PRs for each task.
- To start execution now, confirm and run `/gsd-execute-phase 2`.
