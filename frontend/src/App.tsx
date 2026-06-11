// frontend/src/App.tsx
// Route Map per UI-SPEC + AUTH-03 session bootstrap

import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/axios";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Skeleton } from "@/components/ui/skeleton";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { UnauthorizedPage } from "@/pages/UnauthorizedPage";
import { CreateLibrarianPage } from "@/pages/CreateLibrarianPage";

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
  const { setAuth, clearAuth } = useAuth();
  const [bootstrapping, setBootstrapping] = useState(true);

  // AUTH-03: On every app load, attempt POST /auth/refresh to restore session
  // UI-SPEC Interaction Contracts > Session Initialization
  useEffect(() => {
    const bootstrap = async () => {
      try {
        const { data } = await api.post("/auth/refresh");
        setAuth(data.access_token, data.user);
      } catch {
        // 401 or network error — clear auth and let routes redirect to /login
        clearAuth();
      } finally {
        setBootstrapping(false);
      }
    };
    bootstrap();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Show full-page skeleton while bootstrap in progress (UI-SPEC Screen 3 loading state)
  if (bootstrapping) {
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
        <Route path="/dashboard" element={<DashboardPage />} />
      </Route>

      {/* Protected routes — admin_librarian only (UI-SPEC Route Map, T-04-02: UX gate; backend enforces) */}
      <Route element={<ProtectedRoute allowedRoles={["admin_librarian"]} />}>
        <Route path="/admin/users/new" element={<CreateLibrarianPage />} />
      </Route>

      {/* Catch-all → /login */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
