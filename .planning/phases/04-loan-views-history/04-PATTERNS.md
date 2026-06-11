# Phase 4: Loan Views & History - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 14
**Analogs found:** 12 / 14

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `backend/app/routers/loans.py` | controller | request-response | `backend/app/routers/admin.py` | role-match |
| `backend/app/services/loan_service.py` | service | CRUD | `backend/app/services/auth_service.py` | role-match |
| `backend/app/schemas/loan.py` | model/schema | transform | `backend/app/schemas/user.py` | exact |
| `backend/app/main.py` | config | request-response | `backend/app/main.py` | exact |
| `backend/tests/test_loans.py` | test | request-response | `backend/tests/test_auth.py` | exact |
| `frontend/src/pages/LoansPage.tsx` | component | request-response | `frontend/src/pages/DashboardPage.tsx` | role-match |
| `frontend/src/components/loans/LoanTabs.tsx` | component | request-response | `frontend/src/pages/DashboardPage.tsx` | role-match |
| `frontend/src/components/loans/LoansTable.tsx` | component | request-response | `frontend/src/pages/DashboardPage.tsx` | partial |
| `frontend/src/components/loans/LoanSearchBar.tsx` | component | request-response | `frontend/src/pages/CreateLibrarianPage.tsx` | exact |
| `frontend/src/components/loans/LoanPagination.tsx` | component | request-response | none | no analog |
| `frontend/src/components/loans/LoanEmptyState.tsx` | component | request-response | `frontend/src/pages/LoginPage.tsx` | partial |
| `frontend/src/hooks/useLoans.ts` | hook | request-response | none | no analog |
| `frontend/src/App.tsx` | config | request-response | `frontend/src/App.tsx` | exact |
| `frontend/src/pages/DashboardPage.tsx` | component | request-response | `frontend/src/pages/DashboardPage.tsx` | exact |

## Pattern Assignments

### `backend/app/routers/loans.py` (controller, request-response)

**Copy from:** `backend/app/routers/admin.py` and `backend/app/dependencies/auth.py`

**Imports / dependency shape** (`backend/app/routers/admin.py` lines 11-20, 25-30):
```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.database import DbSession
from app.dependencies.auth import require_role
from app.models.user import User
from app.schemas.user import CreateLibrarianRequest, UserOut
```

**Backend auth pattern** (`backend/app/dependencies/auth.py` lines 67-92):
```python
def require_role(*roles: str):
    async def check_role(
        current_user: Annotated[User, Depends(get_current_user)]
    ) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {roles}",
            )
        return current_user
    return check_role
```

**Read-endpoint pattern** (`backend/app/routers/admin.py` lines 25-63):
```python
@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_librarian(
    data: CreateLibrarianRequest,
    current_user: Annotated[User, Depends(require_role("admin_librarian"))],
    db: DbSession,
) -> UserOut:
    result = await db.execute(select(User).where(User.email == data.email))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
```

### `backend/app/services/loan_service.py` (service, CRUD)

**Copy from:** `backend/app/services/auth_service.py`

**Async helper / query pattern** (`lines 92-125`, `177-200`):
```python
async def is_token_blocklisted(db: AsyncSession, token: str) -> bool:
    result = await db.execute(
        select(RefreshTokenBlocklist).where(
            RefreshTokenBlocklist.token_hash == token_hash
        )
    )
    return result.scalar_one_or_none() is not None


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
```

**Service style to reuse:** module-level helper functions, `AsyncSession` input, `select(...)` queries, `scalar_one_or_none()`, no request/response logic in the service layer.

### `backend/app/schemas/loan.py` (model/schema, transform)

**Copy from:** `backend/app/schemas/user.py`

**ORM output model pattern** (`lines 8-15`):
```python
class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str

    model_config = {"from_attributes": True}
```

**Request schema / validator pattern** (`backend/app/schemas/auth.py` lines 10-31):
```python
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
```

### `backend/app/main.py` (config, request-response)

**Copy from:** current `backend/app/main.py`

**Router registration pattern** (`lines 27-29`):
```python
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
```

### `backend/tests/test_loans.py` (test, request-response)

**Copy from:** `backend/tests/test_auth.py` and `backend/tests/test_admin.py`

**Integration test style** (`backend/tests/test_auth.py` lines 176-277):
```python
class TestRegister:
    async def test_register_creates_student(self, client: AsyncClient):
        resp = await client.post("/auth/register", json={...})
        assert resp.status_code in (200, 201)
```

**RBAC test style** (`backend/tests/test_admin.py` lines 89-129):
```python
class TestRBAC:
    async def test_student_forbidden_from_admin_endpoint(self, client: AsyncClient):
        resp = await client.post("/admin/users", json={...})
        assert resp.status_code == 403
```

### `frontend/src/pages/LoansPage.tsx` (component, request-response)

**Copy from:** `frontend/src/pages/DashboardPage.tsx`

**Shell + auth guard pattern** (`lines 113-203`):
```tsx
export function DashboardPage() {
  const { user, clearAuth } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return (
    <div className="min-h-screen bg-background">
      <header className="bg-card border-b h-14 px-6 flex items-center justify-between">
```

**Role-aware rendering pattern** (`lines 20-55`, `58-101`):
```tsx
function getNavLinks(role: string): NavLink[] { ... }
function WelcomeContent({ role }: { role: string }) { ... }
```

### `frontend/src/components/loans/LoanTabs.tsx` (component, request-response)

**Copy from:** `frontend/src/pages/DashboardPage.tsx`

**Role/state switch pattern** (`lines 20-55`):
```tsx
switch (role) {
  case "student":
    return [...]
  case "librarian":
    return [...]
}
```

Use the same conditional rendering style for tab state (`Active` / `History`) instead of introducing a new routing layer.

### `frontend/src/components/loans/LoansTable.tsx` (component, request-response)

**Copy from:** `frontend/src/pages/DashboardPage.tsx`

**List rendering pattern** (`lines 150-170`):
```tsx
<nav className="hidden md:flex items-center gap-1">
  {navLinks.map((link) =>
    link.disabled ? (
      <span key={link.href} className="text-sm px-3 py-1.5 ...">
```

Reuse the same "array -> rows" rendering style for table rows, badges, and empty-state fallback.

### `frontend/src/components/loans/LoanSearchBar.tsx` (component, request-response)

**Copy from:** `frontend/src/pages/CreateLibrarianPage.tsx`

**RHF + Zod form pattern** (`lines 27-73`, `87-189`):
```tsx
const createLibrarianSchema = z.object({
  full_name: z.string().min(2, "..."),
  email: z.string().email("..."),
  password: z.string().min(8, "Minimum 8 characters"),
});

const form = useForm<CreateLibrarianFormValues>({
  resolver: zodResolver(createLibrarianSchema),
  mode: "onTouched",
});
```

**Submit / loading / error pattern** (`lines 54-85`, `170-188`):
```tsx
const mutation = useMutation({
  mutationFn: (values) => api.post("/admin/users", values),
});
```

### `frontend/src/components/loans/LoanPagination.tsx` (component, request-response)

**No analog found in the codebase.**

Use the research pattern for numbered pages + next/prev:
`GET /loans/me?page=&page_size=&status=` and `GET /loans/search?q=&page=&page_size=`.

### `frontend/src/components/loans/LoanEmptyState.tsx` (component, request-response)

**Copy from:** `frontend/src/pages/LoginPage.tsx`

**Card + friendly copy pattern** (`lines 65-148`):
```tsx
return (
  <div className="min-h-screen bg-background flex items-center justify-center px-4 py-16">
    <Card className="w-full max-w-[400px] shadow-md">
      <CardHeader className="pb-4">
```

Use the same compact, explanatory copy style for "no loans yet" and "no matches" states.

### `frontend/src/hooks/useLoans.ts` (hook, request-response)

**No analog found in the codebase.**

Use the existing React Query baseline from `frontend/src/main.tsx` and the API client from `frontend/src/lib/axios.ts`:
```ts
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 1000 * 60 * 5,
    },
  },
});
```

### `frontend/src/App.tsx` (config, request-response)

**Copy from:** current `frontend/src/App.tsx`

**Protected route map** (`lines 38-57`):
```tsx
<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route path="/register" element={<RegisterPage />} />
  <Route element={<ProtectedRoute />}>
    <Route path="/dashboard" element={<DashboardPage />} />
  </Route>
</Routes>
```

Add the loans route beside the existing protected routes, keeping `ProtectedRoute` as the UX gate.

### `frontend/src/pages/DashboardPage.tsx` (component, request-response)

**Copy from:** current `frontend/src/pages/DashboardPage.tsx`

**Role-based nav link pattern** (`lines 20-55`):
```tsx
function getNavLinks(role: string): NavLink[] {
  switch (role) {
    case "student":
      return [
        { label: "My Loans", href: "/loans", disabled: true },
```

Enable the loans link / add a librarian loans entry with the same `NavLink` array style.

## Shared Patterns

### Backend RBAC + DB session
**Source:** `backend/app/dependencies/auth.py` + `backend/app/database.py`
```python
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
```
```python
DbSession = Annotated[AsyncSession, Depends(get_db)]
```

### Loan query inputs
**Source:** `backend/app/models/loan.py`, `backend/app/models/user.py`, `backend/app/models/book.py`
```python
status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
full_name: Mapped[str] = mapped_column(String(255), nullable=False)
title: Mapped[str] = mapped_column(String(500), nullable=False)
```

### Frontend auth + API client
**Source:** `frontend/src/context/AuthContext.tsx` + `frontend/src/lib/axios.ts`
```tsx
const { user, clearAuth } = useAuth();
```
```ts
export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  withCredentials: true,
});
```

### Page shell
**Source:** `frontend/src/pages/DashboardPage.tsx`
```tsx
<header className="bg-card border-b h-14 px-6 flex items-center justify-between">
```

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `frontend/src/components/loans/LoanPagination.tsx` | component | request-response | No existing pagination component. |
| `frontend/src/hooks/useLoans.ts` | hook | request-response | No existing query hook; first `useQuery`-style hook in repo. |

## Metadata

**Pattern search scope:** `backend/app`, `backend/tests`, `frontend/src`
**Pattern extraction date:** 2026-06-11
