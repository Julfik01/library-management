---
phase: 4
slug: loan-views-history
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-11
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio / httpx (backend) and npm build verification (frontend) |
| **Config file** | `backend/pytest.ini` / `frontend/package.json` |
| **Quick run command** | `cd backend; pytest tests/test_loans.py -x -q` |
| **Full suite command** | `cd backend; pytest && cd frontend; npm run build` |
| **Estimated runtime** | ~1-3 minutes |

---

## Sampling Rate

- **After backend task commits:** Run `cd backend; pytest tests/test_loans.py -x -q`
- **After frontend task commits:** Run `cd frontend; npm run build`
- **Before /gsd-verify-work:** Full backend pytest plus frontend build must be green
- **Max feedback latency:** 30 seconds

---

## Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LOAN-02 | Active loans endpoint returns only current user rows sorted by due date ascending | integration | `cd backend; pytest tests/test_loans.py::TestStudentActiveLoans -x -q` | ❌ Wave 0 |
| LOAN-03 | History endpoint returns returned loans sorted by loan date descending | integration | `cd backend; pytest tests/test_loans.py::TestStudentLoanHistory -x -q` | ❌ Wave 0 |
| LOAN-04 | Librarian search matches student name or book title and respects role checks | integration | `cd backend; pytest tests/test_loans.py::TestLibrarianLoanSearch -x -q` | ❌ Wave 0 |
| LOAN-05 | Pagination metadata and page boundaries are stable at page size 10 | integration | `cd backend; pytest tests/test_loans.py::TestLoanPagination -x -q` | ❌ Wave 0 |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Loans page tabs and empty states | LOAN-02, LOAN-03 | UI behavior and copy are easier to confirm in-browser | Open `/loans` as a student and verify Active / History tabs plus empty-state copy |
| Librarian search flow | LOAN-04, LOAN-05 | Search submit and pagination controls are interaction-driven | Open `/loans` as a librarian, submit a search, and verify numbered pages plus next/prev |

---

## Validation Sign-Off

- [ ] All tasks have automated verification or Wave 0 coverage
- [ ] Sampling continuity: no wave without automated coverage
- [ ] Backend loan tests exist before execution handoff
- [ ] Frontend build passes before execution handoff
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
