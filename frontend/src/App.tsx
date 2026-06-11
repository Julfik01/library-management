// frontend/src/App.tsx
// Route Map per UI-SPEC + AUTH-03 session bootstrap (bootstrap owned by AuthContext)

import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Skeleton } from "@/components/ui/skeleton";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { UnauthorizedPage } from "@/pages/UnauthorizedPage";
import { CreateLibrarianPage } from "@/pages/CreateLibrarianPage";

import { DashboardHome } from "@/pages/DashboardHome";
import { CatalogPage } from "@/pages/CatalogPage";
import { BookDetailPage } from "@/pages/BookDetailPage";
import { StudentRequestsPage } from "@/pages/StudentRequestsPage";
import { StudentLoansPage } from "@/pages/StudentLoansPage";
import { LibrarianRequestsPage } from "@/pages/LibrarianRequestsPage";
import { LibrarianReturnsPage } from "@/pages/LibrarianReturnsPage";

// Full-page loading skeleton while /auth/refresh resolves (UI-SPEC Screen 3 loading state)
function AppLoadingSkeleton() {
  return (
    <div className="min-h-screen bg-background">
      {/* NavBar skeleton */}
      <div className="h-14 bg-muted border-b" />
      {/* Content skeleton */}
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

  // Block route rendering until AuthContext bootstrap completes (UI-SPEC Screen 3)
  if (!initialized) {
    return <AppLoadingSkeleton />;
  }

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/unauthorized" element={<UnauthorizedPage />} />

      {/* Protected routes — all authenticated roles */}
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<DashboardPage />}>
          <Route index element={<DashboardHome />} />
          <Route path="catalog" element={<CatalogPage />} />
          <Route path="catalog/:id" element={<BookDetailPage />} />
          <Route path="my-requests" element={<StudentRequestsPage />} />
          <Route path="loans" element={<StudentLoansPage />} />
          {/* Admin / Librarian only (protected by API) */}
          <Route path="requests" element={<LibrarianRequestsPage />} />
          <Route path="returns" element={<LibrarianReturnsPage />} />
        </Route>
      </Route>

      {/* Protected routes — admin_librarian only */}
      <Route element={<ProtectedRoute allowedRoles={["admin_librarian"]} />}>
        <Route path="/admin/users/new" element={<CreateLibrarianPage />} />
      </Route>

      {/* Catch-all → /login */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
