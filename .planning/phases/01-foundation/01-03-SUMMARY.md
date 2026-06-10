---
phase: 01-foundation
plan: 03
subsystem: frontend
tags: [react, vite, typescript, shadcn, tailwind, axios, tanstack-query, auth, react-hook-form, zod]

# Dependency graph
requires:
  - 01-02 (POST /auth/register, POST /auth/login, POST /auth/refresh, POST /auth/logout — all endpoints wired here)
provides:
  - Vite 6 + React 18 + TypeScript frontend scaffold (npm run build clean)
  - Tailwind CSS v3 + shadcn/ui (New York, Neutral, CSS variables) component library
  - AuthContext.tsx: in-memory access token + user state (D-08 — no localStorage)
  - lib/axios.ts: withCredentials:true + Bearer inject interceptor + 401 refresh+queue interceptor
  - ProtectedRoute.tsx: client-side route guard (UX-only, CM-7)
  - App.tsx: AUTH-03 session bootstrap (POST /auth/refresh on mount → Skeleton → routes)
  - Route map: /login, /register, /dashboard (protected), /unauthorized, catch-all→/login
  - LoginPage.tsx: AUTH-02 login screen per UI-SPEC Screen 1
  - RegisterPage.tsx: AUTH-01 register screen per UI-SPEC Screen 2
  - DashboardPage.tsx: AUTH-07 role-gated dashboard shell per UI-SPEC Screen 3
  - UnauthorizedPage.tsx: /unauthorized screen per UI-SPEC Screen 5
  - frontend/Dockerfile: node:20-alpine dev container (port 5173)
affects:
  - compose.yml frontend service (now buildable with the created Dockerfile)
  - 01-04 (Create Librarian page builds on this scaffold and auth context)
  - All future phases (frontend auth context provides token to all API calls)

# Tech tracking
tech-stack:
  added:
    - vite@6 (Vite 6 build tool — npm create vite@latest)
    - react@18.3.1 (pinned — Pitfall 7 React 18 vs 19)
    - react-dom@18.3.1
    - typescript@5.x (via Vite template)
    - tailwindcss@3.4.19 (pinned v3 — UI-SPEC ordering constraint before shadcn)
    - postcss + autoprefixer (Tailwind PostCSS pipeline)
    - shadcn/ui@2.10.0 (New York style, Neutral base, CSS variables ON)
    - react-router-dom@6
    - @tanstack/react-query@5
    - axios@1
    - react-hook-form@7
    - zod@3
    - @hookform/resolvers (zod integration)
    - clsx + tailwind-merge (shadcn cn() utility)
    - class-variance-authority (shadcn component variants)
    - lucide-react (shadcn icon library)
    - sonner + next-themes (shadcn Toaster)
    - @radix-ui/react-slot, @radix-ui/react-label, @radix-ui/react-avatar,
      @radix-ui/react-separator, @radix-ui/react-dropdown-menu (shadcn Radix primitives)
  patterns:
    - In-memory access token: React Context (AuthContext) + module-level setter (setAccessToken) in axios.ts
    - Axios interceptor pattern: request injects Bearer, response queues 401s during single refresh attempt
    - AUTH-03 bootstrap: useEffect in App.tsx POSTs /auth/refresh before rendering routes
    - Form validation: react-hook-form + zod, mode="onTouched" + reValidateMode="onChange"
    - shadcn via components.json: avoids interactive init issues with Tailwind v3

key-files:
  created:
    - frontend/package.json (React 18, Tailwind v3, shadcn@2 deps)
    - frontend/vite.config.ts (@ alias: src/*)
    - frontend/tsconfig.app.json (@ paths, ignoreDeprecations 6.0)
    - frontend/tsconfig.json (@ paths for shadcn detection)
    - frontend/tailwind.config.js (content paths, shadcn color tokens, Inter font)
    - frontend/postcss.config.js
    - frontend/index.html
    - frontend/components.json (shadcn config: New York, neutral, CSS vars)
    - frontend/Dockerfile (node:20-alpine, port 5173)
    - frontend/src/index.css (Tailwind directives + shadcn Neutral CSS variables + Inter import)
    - frontend/src/lib/utils.ts (cn() via clsx + twMerge)
    - frontend/src/lib/axios.ts (withCredentials + interceptors)
    - frontend/src/context/AuthContext.tsx (in-memory token, setAuth/clearAuth)
    - frontend/src/hooks/useAuth.ts (re-export)
    - frontend/src/components/ProtectedRoute.tsx (UX route guard)
    - frontend/src/components/ui/button.tsx
    - frontend/src/components/ui/input.tsx
    - frontend/src/components/ui/label.tsx
    - frontend/src/components/ui/card.tsx
    - frontend/src/components/ui/form.tsx
    - frontend/src/components/ui/alert.tsx
    - frontend/src/components/ui/avatar.tsx
    - frontend/src/components/ui/separator.tsx
    - frontend/src/components/ui/skeleton.tsx
    - frontend/src/components/ui/sonner.tsx
    - frontend/src/components/ui/dropdown-menu.tsx
    - frontend/src/main.tsx (QueryClientProvider + AuthProvider + BrowserRouter + Toaster)
    - frontend/src/App.tsx (route map + AUTH-03 bootstrap)
    - frontend/src/pages/LoginPage.tsx (AUTH-02 — Sign in screen)
    - frontend/src/pages/RegisterPage.tsx (AUTH-01 — Create account screen)
    - frontend/src/pages/DashboardPage.tsx (AUTH-07 — role-appropriate dashboard shell)
    - frontend/src/pages/UnauthorizedPage.tsx (/unauthorized screen)
  modified: []

key-decisions:
  - "shadcn@2 via components.json (not interactive init): avoids shadcn@4 Tailwind v4 requirement; Tailwind v3 pins retained per UI-SPEC"
  - "React 18.3.1 pinned: Pitfall 7 — some shadcn/Radix deps have React 19 friction; 18 is stable"
  - "ignoreDeprecations: '6.0' in tsconfig.app.json: TypeScript 5 deprecates baseUrl; needed for @ alias without module:node16"
  - "dropdown-menu added in Task 2: not in original list but required by DashboardPage Avatar dropdown; Rule 2 auto-add"
  - "AUTH-03 bootstrap in App.tsx useEffect: bare axios call before QueryClient ready (UI-SPEC Session Initialization)"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03]

# Metrics
duration: 13min
completed: 2026-06-11
---

# Phase 1 Plan 03: Frontend Scaffold + Auth UI Summary

**Vite+React18+TS+Tailwind3+shadcn frontend with in-memory AuthContext, axios 401-refresh interceptors, session-persistent routing, and Login/Register/Dashboard screens wired to the live backend**

## Performance

- **Duration:** 13 min
- **Started:** 2026-06-11T05:10:50Z (approx)
- **Completed:** 2026-06-11T05:24:00Z (approx)
- **Tasks executed:** 2 of 3 (Task 3 is a human-verify checkpoint)
- **Files created:** 32

## Accomplishments

### Task 1: Scaffold + Auth Infrastructure
- Vite 6 + React 18 (pinned) + TypeScript frontend scaffolded
- Tailwind CSS v3 installed before shadcn init (critical ordering per UI-SPEC Pitfall 7)
- shadcn/ui@2 initialized via `components.json` (New York style, Neutral base, CSS variables ON)
- 10 shadcn components installed: button, input, label, card, form, alert, avatar, separator, skeleton, sonner
- `@` path alias configured in both vite.config.ts and tsconfig.app.json
- shadcn Neutral CSS variable set in index.css + Inter font import
- `AuthContext.tsx`: in-memory access token + user state (D-08 — no localStorage)
- `lib/axios.ts`: withCredentials:true + request interceptor (Bearer) + 401-refresh response interceptor with request queue
- `hooks/useAuth.ts`: re-export hook
- `ProtectedRoute.tsx`: no token → /login; wrong role → /unauthorized; else Outlet (CM-7)
- `frontend/Dockerfile`: node:20-alpine, port 5173

### Task 2: Routing + Screens
- `main.tsx`: QueryClientProvider + AuthProvider + BrowserRouter + Sonner Toaster
- `App.tsx`: AUTH-03 bootstrap — useEffect POSTs /auth/refresh, shows Skeleton, stores token or redirects to /login
- Route map: /login, /register, /unauthorized (public); /dashboard (ProtectedRoute); catch-all → /login
- `LoginPage.tsx`: shadcn Card + Form (react-hook-form + zod, onTouched mode); exact UI-SPEC copy; 401 Alert; footer link
- `RegisterPage.tsx`: full_name (2-100), email, password (min 8); 409 conflict error; "Create account" / "Creating account..."
- `DashboardPage.tsx`: TopNav with "University Library", role-gated nav links (Phase-2 shown muted not hidden), Avatar dropdown, role-appropriate welcome content
- `UnauthorizedPage.tsx`: ShieldOff icon + "Access denied" + "Go to dashboard"
- `dropdown-menu` shadcn component added for Avatar dropdown

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Vite scaffold + auth context + axios interceptors | 5dd3bfe | frontend/src/context/AuthContext.tsx, frontend/src/lib/axios.ts, frontend/src/components/ProtectedRoute.tsx, shadcn UI components |
| 2 | Routing + session bootstrap + Login/Register/Dashboard screens | e9ad060 | frontend/src/App.tsx, frontend/src/main.tsx, frontend/src/pages/* |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used components.json instead of interactive `npx shadcn@latest init`**
- **Found during:** Task 1 — shadcn init
- **Issue:** `npx shadcn@latest` (v4.11) requires Tailwind v4, but plan specifies Tailwind v3 (UI-SPEC constraint, RESEARCH.md Pitfall 7). Interactive init blocked with "No Tailwind CSS configuration found."
- **Fix:** Created `components.json` manually with New York style, Neutral base color, CSS variables ON. Used `npx shadcn@2 add <component>` which correctly targets Tailwind v3. shadcn@2 is the last version supporting Tailwind v3.
- **Files modified:** frontend/components.json (created)
- **Commit:** 5dd3bfe

**2. [Rule 1 - Bug] Added `ignoreDeprecations: "6.0"` to tsconfig.app.json**
- **Found during:** Task 1 — first build attempt
- **Issue:** TypeScript 5.x deprecates `baseUrl` option (needed for `@` path alias). Build failed with TS5101 error.
- **Fix:** Added `"ignoreDeprecations": "6.0"` to suppress the warning. The `baseUrl` + `paths` combination remains the correct approach for bundler moduleResolution in Vite projects.
- **Files modified:** frontend/tsconfig.app.json
- **Commit:** 5dd3bfe

**3. [Rule 2 - Missing Critical] Added `dropdown-menu` shadcn component**
- **Found during:** Task 2 — DashboardPage implementation
- **Issue:** UI-SPEC Screen 3 requires an Avatar with a "Sign out" dropdown. DashboardPage needs `<DropdownMenu>` from shadcn. Not in the original component inventory list.
- **Fix:** Ran `npx shadcn@2 add dropdown-menu` and used it in DashboardPage.
- **Files modified:** frontend/src/components/ui/dropdown-menu.tsx (created)
- **Commit:** e9ad060

**4. [Rule 2 - Missing Critical] Added `@hookform/resolvers` package**
- **Found during:** Task 2 — LoginPage/RegisterPage form wiring
- **Issue:** `react-hook-form` + `zod` requires `@hookform/resolvers` to bridge the two libraries (zodResolver). Not explicitly listed in the plan's package list.
- **Fix:** Added `npm install @hookform/resolvers`.
- **Files modified:** frontend/package.json
- **Commit:** e9ad060

**Total deviations:** 4 (2 bug/blocking fixes, 2 missing critical functionality)
**Impact on plan:** All fixes required for correct operation. No scope creep.

## Checkpoint: Awaiting Human Verification

Task 3 is a `checkpoint:human-verify` gate. Human verification of the full register → login → refresh → logout flow is required before this plan can be marked complete.

## Threat Surface Scan

All threat mitigations from plan's threat model applied:
- T-03-01: Access token in React Context / module-level memory only; no localStorage reference in AuthContext.tsx or axios.ts — XSS protection
- T-03-02: ProtectedRoute documented as UX-only; backend require_role is the authority (CM-7) — comment in ProtectedRoute.tsx
- T-03-03: axios instance uses withCredentials:true (sends httpOnly refresh cookie on POST /auth/refresh)
- T-03-04: Backend CORS pins http://localhost:5173; frontend never assumes wildcard
- T-03-SC: All packages verified in RESEARCH.md Package Legitimacy Audit (no [ASSUMED]/[SUS]/[SLOP] flags)

No new threat surface beyond the plan's threat model.

## Known Stubs

None — all wired to live backend endpoints from plan 01-02. No hardcoded data, no placeholder text.

## Self-Check


All key files verified present on disk:
- frontend/src/context/AuthContext.tsx: FOUND
- frontend/src/lib/axios.ts: FOUND
- frontend/src/pages/LoginPage.tsx: FOUND
- frontend/src/pages/RegisterPage.tsx: FOUND
- frontend/src/pages/DashboardPage.tsx: FOUND
- frontend/src/App.tsx: FOUND
- frontend/Dockerfile: FOUND

Both task commits verified in git log:
- `5dd3bfe` feat(01-03): Task 1 — Vite+React18+TS+Tailwind3+shadcn scaffold, auth context, axios interceptors
- `e9ad060` feat(01-03): Task 2 — routing, session bootstrap, Login/Register/Dashboard screens

## Self-Check: PASSED

---
*Phase: 01-foundation*
*Completed: 2026-06-11 (tasks 1-2; task 3 awaiting human checkpoint)*

