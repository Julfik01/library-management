---
status: complete
phase: 01-foundation
source:
  - 01-01-SUMMARY.md
  - 01-02-SUMMARY.md
  - 01-03-SUMMARY.md
  - 01-04-SUMMARY.md
started: 2026-06-11T06:00:00Z
updated: 2026-06-11T06:00:00Z
mode: mvp
---

## Current Test

number: complete
name: All tests passed
awaiting: none

## Tests

### Section A — User Flow (run in order; stop if any step fails)

### 1. Cold Start Smoke Test
expected: |
  Stop any running containers (`docker compose down`). Start fresh (`docker compose up --build`).
  The db, backend, mailhog, and frontend services all start without errors.
  The backend runs Alembic migrations automatically and the admin seed completes.
  Visit http://localhost:8000/health — expect {"status":"ok"} or similar.
  Visit http://localhost:5173 — expect the login page to load (no blank screen, no console errors).
result: pass
reported: "Frontend stuck on skeleton/loading screen after fix. Login page loads at localhost:5173, no infinite refresh loop."
fix_file: frontend/src/lib/axios.ts
fix_line: 39

### 2. Student Registration
expected: |
  On the login page, click "Create account" (or visit /register directly).
  Fill in: Full Name (any), a fresh email (not already used), password (8+ chars).
  Click "Create account". Expect: you are immediately taken to the Student Dashboard
  showing a welcome like "Welcome, [Full Name]" or similar role-appropriate content.
  (Note: there is a known potential issue here — if you see the login page instead of the dashboard after registering, report it.)
result: pass

### 3. Student Login + Dashboard Routing
expected: |
  Sign out (Avatar dropdown → "Sign out"), or open a private window.
  Go to /login. Log in with the student account just created.
  Expect: redirect to /dashboard showing the Student Dashboard (no "Manage Users" nav link visible for this student).
result: pass

### 4. Session Persistence Across Page Refresh
expected: |
  While logged in as the student, refresh the page (F5 or Cmd+R).
  Expect: you remain on the dashboard — not redirected to /login. The page briefly shows a loading skeleton, then restores the session.
result: pass

### 5. Logout Invalidates Session
expected: |
  Click Avatar dropdown → "Sign out". Expect: redirected to /login.
  Then try navigating directly to http://localhost:5173/dashboard.
  Expect: redirected back to /login (session is invalidated, not just cleared client-side).
result: pass

### 6. Admin Login + Create Librarian + New Librarian Logs In
expected: |
  Log in with the seeded admin credentials (ADMIN_EMAIL / ADMIN_PASSWORD from your .env).
  Expect: "Admin Dashboard" (or admin-role welcome) and a "Manage Users" nav link.
  Click "Manage Users" (or visit /admin/users/new). Fill in the Create Librarian form with a fresh email and password.
  Click "Create account". Expect: toast "Librarian account created." and the form resets (you stay on the page).
  Sign out as admin. Log in with the new librarian's credentials.
  Expect: "Librarian Dashboard" (librarian-role welcome). AUTH-06 full loop confirmed.
result: pass

### 7. Role-Based Nav Links
expected: |
  As the librarian (logged in from step 6): confirm "Manage Users" nav link is NOT visible (librarians are not admin_librarian).
  As the seeded admin: "Manage Users" is visible.
  As a student: "Manage Users" is not visible.
result: pass

### 8. Client Route Guard — Unauthorized Redirect
expected: |
  While logged in as a student (or librarian), navigate directly to http://localhost:5173/admin/users/new.
  Expect: redirected to /unauthorized showing an "Access denied" message and a "Go to dashboard" button.
  Click "Go to dashboard" — expect redirect back to /dashboard.
result: pass

### Section B — Technical Checks (only run after all Section A steps pass)

### 9. Backend RBAC Bypass — Curl Test
expected: |
  Log in as a student via the API to get an access token:
    curl -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"email":"student@example.com","password":"yourpassword"}'
  Copy the access_token. Then try to create a librarian directly:
    curl -i -X POST http://localhost:8000/admin/users \
      -H "Authorization: Bearer <student_access_token>" \
      -H "Content-Type: application/json" \
      -d '{"email":"hack@test.com","password":"password123","full_name":"Hack"}'
  Expect: HTTP 403 Forbidden (not 201, not 401). The backend enforces RBAC independently of the frontend guard.
result: pass

### 10. Duplicate Email Registration Error
expected: |
  On /register, try to register with an email that already has an account.
  Expect: an inline error message like "An account with this email already exists." (no crash, no blank page).
result: pass

### Section C — Coverage Check

### 11. All 5 Foundation Success Criteria
expected: |
  Confirm all five were demonstrated across steps 1-9:
  1. Student registered and (eventually) logged in ✓
  2. Logged-in user stayed logged in across refresh ✓
  3. Logout invalidated session server-side ✓
  4. Seeded admin created a librarian who could then log in ✓
  5. Student curl-bypass to /admin/users returned HTTP 403 ✓
  If all five are true, type "yes". If any failed, describe which one.
result: pass

## Summary

total: 11
passed: 11
issues: 0
skipped: 0
pending: 0

## Gaps

[none yet]
