# Phase 4: Loan Views & History - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 4 delivers student loan visibility and librarian-wide loan search:
- Students can view active loans and full borrow history.
- Librarians can search across all loans.
- Loan lists are paginated.

This phase does not add new borrowing or return capabilities; it only exposes the loan data already created in earlier phases.

</domain>

<decisions>
## Implementation Decisions

### Student loan views

- **One Loans page with tabs:** Students should get a single Loans page with **Active** and **History** tabs, not separate routes.
- **List layout:** Loan lists should be rendered as a **table with columns**, not cards or stacked rows.
- **Active tab ordering:** Sort active loans by **due soonest first**.
- **History tab ordering:** Sort borrow history by **newest loan first**.
- **Overdue treatment:** Active overdue loans should use a **red overdue badge plus supporting text** so the status is obvious without relying on color alone.
- **History row content:** History rows should show **book title, borrow date, due date, return date, and outcome**.
- **Empty states:** Use a **friendly empty state with a short explanation** instead of a blank table.

### Librarian loan search

- **One combined search box:** Librarian search should use a single query box that matches **student name or book title**.
- **Search trigger:** Search should run **only after submit**, not live while typing.
- **Default sort:** Search results should default to **most recent loan first**.
- **Result columns:** Librarian results should prioritize **student name, book title, status, and due date**.
- **Pagination controls:** Use **numbered pages with next/prev** rather than infinite scroll.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` — Phase 4 goal, requirements, and success criteria
- `.planning/REQUIREMENTS.md` — LOAN-02 through LOAN-05 definitions
- `.planning/STATE.md` — existing loan model and app-wide decisions
- `.planning/phases/01-foundation/01-CONTEXT.md` — carried-forward auth/schema decisions
- `.planning/phases/01-foundation/01-DISCUSSION-LOG.md` — prior decision trail
- `CLAUDE.md` — project stack and workflow constraints
- `backend/app/models/loan.py` — loan status fields and overdue sentinel
- `backend/app/models/user.py` — student full_name source for loan search
- `backend/app/models/book.py` — book title source for loan search
- `frontend/src/pages/DashboardPage.tsx` — existing shell/navigation pattern
- `frontend/src/context/AuthContext.tsx` — auth bootstrap and user identity shape
- `frontend/src/components/ProtectedRoute.tsx` — route gating pattern

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Dashboard shell, top nav, avatar/dropdown, separator, button, skeleton, and card primitives already exist.
- AuthContext already exposes the authenticated user role and full_name needed for student/librarian views.

### Established Patterns
- Frontend routes are role-gated with `ProtectedRoute`; backend remains the authority.
- The app currently uses a single dashboard shell with muted future-nav links for not-yet-built phases.
- Loan data model already distinguishes `active`, `returned`, and `overdue`.

### Integration Points
- Student loan views should derive status from `backend/app/models/loan.py`.
- Librarian search should join loan rows to `users.full_name` and `books.title`.
- There is no existing reusable table or pagination component in the frontend yet.

</code_context>

<specifics>
## Specifics

- The student view should treat "overdue" as a state of an active loan, not a separate history bucket.
- History is borrow history, not borrow-request history.
- Search is broad enough to cover student name or book title, but not extra filters or new loan actions.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>

---
*Phase: 4-Loan-Views-History*
*Context gathered: 2026-06-11*
