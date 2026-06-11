# Features Research — University Library Management System

**Domain:** University library management (web-based, two-role: Student + Librarian)
**Researched:** 2026-06-10
**Confidence:** HIGH (domain is well-established; patterns derived from Koha, Evergreen, Ex Libris Alma, Sierra, and widely documented academic LMS UX research)

---

## Table Stakes (must have or users leave)

These are the features users arrive expecting. Absence causes immediate friction and erodes trust in the system. Every production academic library system — open-source (Koha, Evergreen) and commercial (Alma, Sierra, Polaris) — ships all of these on day one.

| Feature | Why Expected | Complexity | Status in PROJECT.md |
|---------|--------------|------------|----------------------|
| Catalog search with keyword matching | Students cannot browse thousands of titles; search is the primary access point | Low | Specified (title, author, ISBN, category) |
| Available copy count on every book card | Students won't request a book they can't get; unavailability must be visible before they click in | Low | Specified |
| Book detail page (title, author, ISBN, publisher, year, cover, category, copies) | Users expect a canonical page per book; rushing to request without context feels hostile | Low | Specified (via add/edit form fields) |
| Borrow request submission | Core student workflow. If this is broken or obscure, the system has no purpose | Low | Specified |
| Request status visibility (pending / approved / rejected) | Students will email or call the librarian repeatedly if they cannot self-check status | Low | Specified (borrow request history) |
| Active loans list with due dates | "When is my book due?" is the single most common student query in any library system | Low | Specified |
| Overdue indication on student dashboard | Students expect a clear visual flag — not just an email — when they are overdue | Low | Partially specified (email alert exists; UI flag implied) |
| Librarian request queue (pending requests) | Librarians must have a single view to action incoming requests; without it, requests are lost | Low-Med | Implied by approve/reject workflow |
| Approve / reject borrow requests with outcome visible to student | Core librarian workflow. One action must simultaneously update copy count and trigger email | Low-Med | Specified |
| Record book return + update available count | Without this, copy counts diverge from reality immediately | Low | Specified |
| Overdue items dashboard for librarian | Librarians need a list of all currently overdue loans to chase students manually | Low | Specified |
| Catalog CRUD for librarian (add, edit, delete book) | Librarians must maintain catalog accuracy; stale data breaks student trust | Low-Med | Specified |
| Email notification on request approve/reject | Students are not in the app all day; async notification is the contract the system makes with them | Med (email infra) | Specified |
| Email notification on overdue | Same rationale; overdue without notification shifts blame to the system | Med (email infra + scheduler) | Specified |
| Session persistence (stay logged in) | Re-logging in on every visit is a hard blocker for adoption at any institution | Low | Specified |
| Role-based access (student vs librarian views) | Mixing roles is a security and UX failure; students must not see the librarian queue | Low | Implied by two-role design |

### UX Patterns Expected at Table Stakes Level

**Search UI:**
- Keyword search bar prominently at top of catalog page (not buried in a menu)
- Filter sidebar or horizontal filter bar: Category/Genre, Availability (available now toggle), Year range
- Sort options: Relevance (default), Title A-Z, Author A-Z, Year newest first
- Paginated results, 20–30 items per page, with total count shown ("Showing 1–20 of 143 results")
- Each result card shows: cover thumbnail (or placeholder), title, author, available copies badge (green if > 0, gray/red if 0)

**Book Detail Page:**
- Cover image (left) + metadata block (right) — standard two-column layout
- Availability badge prominently above the "Request to Borrow" button
- "Request to Borrow" button disabled/hidden when available copies = 0
- ISBN, publisher, year, category shown below the fold

**Student Dashboard:**
- Three panels: Active Loans, Pending Requests, Request History
- Active Loans table: Book title, due date, overdue badge if applicable
- Visual overdue state: red date text or "OVERDUE" pill — not just an absence of green

**Librarian Dashboard:**
- Four panels: Pending Requests (actioned first), Overdue Loans, Recent Returns, Catalog Quick Stats
- Pending Requests table: Student name, book title, request date, Approve / Reject inline actions
- Overdue table: Student name, book title, due date, days overdue (calculated column)

---

## Differentiators (competitive advantage)

These features are absent from minimal viable library systems but present in mature ones. They increase adoption and reduce librarian workload. None are required for v1 but each has a clear ROI path.

| Feature | Value Proposition | Complexity | Recommended Phase |
|---------|-------------------|------------|-------------------|
| Advanced catalog filters (multi-select genre, year range, availability-only toggle) | Reduces "no results" frustration; students find books faster | Low-Med | Phase 2 |
| Borrow history for students (all past loans, not just active) | Lets students re-request books they've read before; builds trust that the system remembers them | Low | Phase 2 |
| Librarian search across all loans (by student name or book title) | Librarians managing 500+ active loans need to find specific ones without scrolling | Low-Med | Phase 2 |
| Catalog statistics for librarian (most borrowed titles, total active loans, overdue rate) | Informs purchasing and policy decisions; makes the librarian look competent to administration | Med | Phase 3 |
| Book request waitlist (queue when all copies are borrowed) | Standard in Koha and Evergreen; prevents "available copies = 0, no path forward" dead end | Med-High | Phase 3 |
| Bulk catalog operations (multi-select delete, bulk copy count edit) | Librarians importing a new semester's acquisitions are blocked without this | Med | Phase 3 |
| Librarian notes on borrow requests (internal reason for rejection) | Rejection without reason generates support overhead; a one-line note field eliminates it | Low | Phase 2 |
| Student email notification when a previously unavailable book becomes available | Closes the "no copies" dead end; drives re-engagement | Med (requires interest tracking) | Phase 3 |
| Cover image fallback via ISBN lookup (Open Library / Google Books API) | Catalog without covers looks unpolished; auto-fetching on ISBN entry costs one API call per book | Med | Phase 2 |
| Pagination + sorting on all list views | Catalog, request queue, loans list all degrade badly at scale without this | Low | Phase 2 |
| Admin librarian user management UI (create/deactivate librarian accounts) | Without UI, account management is a direct DB operation — unacceptable for non-technical staff | Low-Med | Phase 2 |

---

## Anti-Features (deliberately NOT in v1)

These are features commonly found in commercial library systems that would add scope, complexity, or external dependencies without proportionate v1 value. Each has a documented rationale.

| Anti-Feature | Why Exclude in v1 | What to Do Instead |
|--------------|-------------------|-------------------|
| Loan renewals | Adds state complexity (renewal count, renewed-from loan chain), creates edge cases with copy availability. PROJECT.md explicitly out-of-scope. | Student returns and re-requests. Librarian approves same-day if available. |
| Monetary fines / fee calculation | Requires payment infrastructure (Stripe or similar), fine accumulation logic, dispute handling, balance display on student profile. Disproportionate complexity for v1. | Overdue is flagged only. Manual enforcement (librarian contacts student) handles the rare case. |
| Per-copy barcode tracking (individual copy identity) | Doubles schema complexity (Book → Copy → Loan instead of Book → Loan). Requires physical barcode labels on every copy. No benefit unless the library has dozens of copies per title. | Count-based model (total_copies, available_copies) is sufficient and already decided. |
| University SSO / LDAP / SAML | External IT dependency, institution-specific integration, maintenance burden. Already out-of-scope in PROJECT.md. | Custom email/password JWT auth. Students self-register. |
| Mobile app (iOS / Android) | Doubles frontend effort. Web app with responsive design covers mobile browsers adequately for v1. | Responsive React frontend. |
| Inter-library loan (ILL) | Requires integration with external institutions, entirely different request workflow, separate approval chain. | Out of scope permanently for a single-institution system. |
| MARC/BIBFRAME cataloging support | Librarian-facing metadata standard used in full OPAC systems. Overkill for a university system managing hundreds to low-thousands of titles. | Simple structured fields (title, author, ISBN, category, publisher, year) are sufficient. |
| Reading lists / curated collections by librarian | Nice-to-have for academic guidance, but requires a separate data model (list → books) and UI. Not a core workflow. | Defer to v2 if librarians request it. |
| Book reviews / ratings by students | Social feature that adds moderation complexity and content storage with no transactional value in v1. | Defer to v2 or drop entirely. |
| Real-time in-app notifications | Requires WebSocket infrastructure or polling. Email covers the async contract established in PROJECT.md. | Email notifications only, as specified. |
| CSV bulk user import | Self-registration covers v1 onboarding. Bulk import adds validation complexity and error reporting UI. Already out-of-scope in PROJECT.md. | Students self-register. Admin librarian creates individual librarian accounts. |
| Configurable loan periods (per book, per role) | Fixed 14-day period removes an entire class of edge cases (what period applies to this loan?). Already decided in PROJECT.md. | Hardcode 14 days. Change requires a code deploy, not a settings toggle — acceptable for v1. |
| Print / export reports (PDF, CSV) | Useful for administration reporting, but a standalone feature requiring layout/templating work. | Librarian reads overdue and stats from the UI dashboard. |

---

## Feature Dependencies

Build order is dictated by these dependency chains. A feature cannot be tested or demoed without all its upstream dependencies in place.

```
Authentication (JWT sessions, role assignment)
  └── Role-based routing (student vs librarian views)
        ├── Student catalog view
        │     └── Book search + filters
        │           └── Book detail page
        │                 └── Borrow request submission
        │                       └── Request status display (student)
        │                             └── Active loans list + due dates
        │                                   └── Overdue indicator (student UI)
        │
        └── Librarian catalog management (CRUD)
              └── Librarian pending requests queue
                    ├── Approve request
                    │     ├── Copy count decrement (available_copies -1)
                    │     ├── Loan record creation (due_date = now + 14 days)
                    │     └── Email notification (approved)
                    └── Reject request
                          └── Email notification (rejected)

Loan record (created on approval)
  └── Record return
        └── Copy count increment (available_copies +1)

Scheduled job (overdue detection: due_date < now AND returned = false)
  ├── Overdue flag on loan record
  ├── Email notification (overdue alert to student)
  └── Librarian overdue dashboard
```

### Critical path for MVP demo (shortest path to a working end-to-end flow)

1. Auth + role routing
2. Book catalog (librarian adds a book)
3. Student searches catalog, views book, submits borrow request
4. Librarian sees pending request, approves it (loan created, copy count decremented)
5. Student sees active loan with due date
6. Librarian records return (copy count incremented)
7. Overdue scheduler runs, flags overdue loan, triggers email

Every other feature is a branch off this spine, not part of the critical path.

### Dependency rules for phasing

| If building... | Must exist first |
|----------------|-----------------|
| Borrow request submission | Auth, catalog with at least one book, available_copies > 0 logic |
| Approve/reject workflow | Borrow request model, email service wired up |
| Return recording | Approved loan exists, copy count model |
| Overdue flagging | Loan records with due_date, background scheduler (Celery or APScheduler) |
| Student active loans view | Loan records linked to student user |
| Librarian overdue dashboard | Overdue flag on loan records |
| Email notifications | Email provider configured (SMTP or transactional service like SendGrid/Mailgun) |
| Admin librarian creates librarian accounts | Auth system with role field, admin-level permission check |

---

## Common UX Patterns for Library Systems

These are patterns observed across Koha, Evergreen, and modern SaaS academic library UIs. They inform component design decisions.

### Catalog / Search

- **Two-panel layout**: Filters sidebar (left, ~240px) + results grid (right). On mobile, filters collapse into a drawer.
- **Result card anatomy**: Cover thumbnail (80x120px or placeholder icon), title (bold), author (subdued), year, category pill, availability badge ("2 of 5 available" or "Unavailable").
- **Availability badge color convention**: Green = copies available; Orange = limited (1 copy); Gray/Red = unavailable. Users have internalized this from retail (in-stock / out-of-stock).
- **Search-as-you-type vs submit**: Submit-on-enter is fine for v1. Search-as-you-type adds debounce complexity and is a differentiator, not table stakes.
- **Empty state**: "No books found for 'X'. Try a broader search or browse by category." — a common gap that causes users to assume the system is broken.

### Borrow Request Flow

- **Single confirm step**: Student clicks "Request to Borrow" → confirmation dialog ("Request 'Title'? You'll be notified by email when approved.") → Submit. No multi-step form needed for a no-configuration request.
- **Prevent duplicate requests**: If student already has a pending or active loan for this book, the button changes to "Request Pending" or "Currently Borrowed" — disabled. This is a data-integrity requirement masquerading as a UX pattern.

### Student Dashboard

- **Status pills over separate pages**: "Pending", "Approved", "Rejected", "Returned", "Overdue" — colored pills on a single unified list is better than four separate tabs requiring navigation.
- **Due date prominence**: Display as both an absolute date ("Due Jun 24") and relative ("12 days left" or "3 days overdue"). Relative time is more actionable.

### Librarian Queue

- **Inline actions**: Approve and Reject buttons directly on the queue row. Do not require navigating to a detail page for a one-click decision.
- **Destructive action confirmation**: Reject should show a small confirmation (popover or inline confirm) to prevent accidental rejects. Approve does not need this — approval is reversible via return recording; rejection is not (student gets notified).
- **Overdue sort**: Default sort for overdue table should be "most days overdue first" — the worst cases surface at the top.

---

## Sources

This research is based on training knowledge of:
- Koha ILS (open-source, widely deployed in universities) — feature set and UX conventions
- Evergreen ILS (open-source, North American academic libraries) — cataloging and circulation patterns
- Ex Libris Alma / Primo (commercial academic library system) — UX patterns and feature scope
- OPAC (Online Public Access Catalog) UX research literature — search and discovery patterns
- Standard academic library workflows documented in IFLA (International Federation of Library Associations) guidelines

**Confidence:** HIGH for table stakes (universal across all production systems), MEDIUM for differentiators (depend on institutional needs and v2 roadmap), HIGH for anti-features (explicitly excluded with PROJECT.md rationale).
