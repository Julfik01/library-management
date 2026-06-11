# Phase 4: Loan Views & History - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 4-Loan-Views-History

---

## Student Loan Views

### Page shape

| Option | Description | Selected |
|--------|-------------|----------|
| One Loans page with Active / History tabs | Keeps the student experience in one place and matches the two required loan states. | ✓ |
| Separate pages for Active loans and History | Splits the experience across routes. | |
| One combined infinite list with filters | Not aligned with the requested tabbed view. | |

**User's choice:** One Loans page with Active / History tabs

### Overdue indicator

| Option | Description | Selected |
|--------|-------------|----------|
| Red overdue badge plus supporting text | Clear, accessible, and obvious at a glance. | ✓ |
| Row highlight only | Depends too much on color alone. | |
| Text label only | Less visible in a dense list. | |

**User's choice:** Red overdue badge plus supporting text

### Ordering

| Option | Description | Selected |
|--------|-------------|----------|
| Active: due soonest first; History: newest loan first | Most useful default for students tracking due dates and recent history. | ✓ |
| Active: newest first; History: newest loan first | Less helpful for active due-date tracking. | |
| Active: due soonest first; History: oldest first | Least useful for history review. | |

**User's choice:** Active: due soonest first; History: newest loan first

### List layout

| Option | Description | Selected |
|--------|-------------|----------|
| Table with columns | Best fit for paginated loan lists and searchable results. | ✓ |
| Cards / stacked rows | More mobile-friendly, but less dense for data review. | |
| Mixed: table for librarian, cards for students | Inconsistent across the phase. | |

**User's choice:** Table with columns

### History row content

| Option | Description | Selected |
|--------|-------------|----------|
| Book title, borrow date, due date, return date, and outcome | Full history context for each loan. | ✓ |
| Book title, borrow date, and outcome only | Too sparse for reviewing loan timelines. | |
| Book title and dates only | Missing the outcome detail. | |

**User's choice:** Book title, borrow date, due date, return date, and outcome

### Empty state

| Option | Description | Selected |
|--------|-------------|----------|
| Friendly empty state with a short explanation | Clear and reassuring when no loans match the view. | ✓ |
| Blank table with no rows | Looks unfinished and gives no guidance. | |
| Hide the table until data exists | Removes structure the user needs. | |

**User's choice:** Friendly empty state with a short explanation

---

## Librarian Loan Search

### Search scope

| Option | Description | Selected |
|--------|-------------|----------|
| One combined search box matching student name or book title | Simple, broad, and matches the phase requirement well. | ✓ |
| Separate fields for student name and book title | More controls, but more UI clutter. | |
| Search by student name only | Too narrow for the requirement. | |

**User's choice:** One combined search box matching student name or book title

### Search trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Only after submit | Predictable for paginated search results. | ✓ |
| Live as the user types | More dynamic, but more churn while paging. | |
| Live after a short debounce | Middle ground, but still more active than needed. | |

**User's choice:** Only after submit

### Default sort

| Option | Description | Selected |
|--------|-------------|----------|
| Most recent loan first | Best default for an operational librarian queue/search. | ✓ |
| Soonest due date first | Useful for returns, but not the default search expectation. | |
| Student name A-Z | Easier for lookup, but less useful operationally. | |

**User's choice:** Most recent loan first

### Result columns

| Option | Description | Selected |
|--------|-------------|----------|
| Student name, book title, status, and due date | Operationally useful and compact enough for search results. | ✓ |
| Student name, book title, due date, and return date | Good for history, but less useful as a search default. | |
| Student name, book title, and status only | Too little context for search results. | |

**User's choice:** Student name, book title, status, and due date

### Pagination style

| Option | Description | Selected |
|--------|-------------|----------|
| Numbered pages with next/prev | Clear for bounded result sets and consistent with paginated search. | ✓ |
| Simple previous / next only | Minimal, but less explicit about page position. | |
| Infinite scroll | Not a good fit for searchable operational lists. | |

**User's choice:** Numbered pages with next/prev
