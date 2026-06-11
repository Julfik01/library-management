// frontend/src/App.tsx
// Route Map per UI-SPEC + AUTH-03 session bootstrap (bootstrap owned by AuthContext)
// Phase 2: Added /catalog and /requests routes, AppLayout wraps all protected pages.

import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { AppLayout } from "@/components/AppLayout";
import { Skeleton } from "@/components/ui/skeleton";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { UnauthorizedPage } from "@/pages/UnauthorizedPage";
import { CreateLibrarianPage } from "@/pages/CreateLibrarianPage";
import { CatalogPage } from "@/pages/CatalogPage";
import { BorrowRequestsPage } from "@/pages/BorrowRequestsPage";
import { ManageBooksPage } from "@/pages/ManageBooksPage";

// Full-page loading skeleton while /auth/refresh resolves (UI-SPEC Screen 3 loading state)
function AppLoadingSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      <div className="h-14 bg-muted border-b" />
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-4">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-5 w-96" />
        <Skeleton className="h-5 w-80" />
      </div>
    </div>
  );
}

export default function App() {
  const { initialized } = useAuth();

  if (!initialized) {
    return <AppLoadingSkeleton />;
  }

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />

      {/* Protected routes — all authenticated roles — wrapped in AppLayout nav */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          {/* Phase 2: Catalog (all authenticated roles) */}
          <Route path="/catalog" element={<CatalogPage />} />
          {/* Phase 2: Requests/Loans (students see own; librarians see all) */}
          <Route path="/requests" element={<BorrowRequestsPage />} />
          <Route path="/loans" element={<BorrowRequestsPage />} />
        </Route>
      </Route>

      {/* Protected routes — librarian & admin_librarian only — wrapped in AppLayout nav */}
      <Route element={<ProtectedRoute allowedRoles={["librarian", "admin_librarian"]} />}>
        <Route element={<AppLayout />}>
          <Route path="/admin/books" element={<ManageBooksPage />} />
        </Route>
      </Route>

      {/* Protected routes — admin_librarian only — wrapped in AppLayout nav */}
      <Route element={<ProtectedRoute allowedRoles={["admin_librarian"]} />}>
        <Route element={<AppLayout />}>
          <Route path="/admin/users/new" element={<CreateLibrarianPage />} />
        </Route>
      </Route>

      {/* Catch-all → /login */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
