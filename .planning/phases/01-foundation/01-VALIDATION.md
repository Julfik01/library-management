---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23.x (backend) / Vitest 1.x + React Testing Library 14.x (frontend) |
| **Config file** | `backend/pytest.ini` / `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && pytest tests/ -x -q` |
| **Full suite command** | `cd backend && pytest tests/ && cd ../frontend && npm run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && pytest tests/ && cd ../frontend && npm run test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {N}-01-01 | 01 | 1 | AUTH-01 | — | Registration rejects duplicate emails | unit | `pytest tests/test_auth.py -x -q` | ❌ W0 | ⬜ pending |
| {N}-01-02 | 01 | 1 | AUTH-02 | — | Login returns 401 for wrong password | unit | `pytest tests/test_auth.py -x -q` | ❌ W0 | ⬜ pending |
| {N}-01-03 | 01 | 1 | AUTH-03 | — | Refresh endpoint sets httpOnly cookie | integration | `pytest tests/test_auth.py::test_refresh -x -q` | ❌ W0 | ⬜ pending |
| {N}-01-04 | 01 | 1 | AUTH-04 | — | Logout blocklists the refresh token | unit | `pytest tests/test_auth.py::test_logout -x -q` | ❌ W0 | ⬜ pending |
| {N}-01-05 | 01 | 1 | AUTH-07 | — | Student role returns 403 on librarian endpoint | integration | `pytest tests/test_rbac.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py` — shared fixtures (async client, db session, test users)
- [ ] `backend/tests/test_auth.py` — stubs for AUTH-01 through AUTH-04
- [ ] `backend/tests/test_rbac.py` — stubs for AUTH-07
- [ ] `pytest-asyncio` 0.23.x with `asyncio_mode = "auto"` in pytest.ini

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| httpOnly cookie not readable by JS | AUTH-03 | Browser security property — cannot assert via test | Open DevTools → Application → Cookies; verify `refresh_token` has HttpOnly flag |
| Admin librarian creation via UI | AUTH-06 | End-to-end UI flow | Log in as admin, navigate to admin panel, create librarian account, verify login works |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
