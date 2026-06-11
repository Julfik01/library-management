// frontend/src/pages/DashboardPage.tsx
// UI-SPEC Screen 3: Dashboard Shell — AUTH-03, AUTH-07
// Nav is provided by AppLayout — this page renders only the main content.
// Copywriting Contract: role-appropriate welcome headings and body text (exact match)

import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

// Role-appropriate welcome content (UI-SPEC Copywriting Contract — exact copy)
function WelcomeContent({ role }: { role: string }) {
  switch (role) {
    case "student":
      return (
        <div>
          <h1 className="text-xl font-semibold text-foreground">
            Welcome to University Library
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Browse the catalog to find books and submit borrow requests.
          </p>
        </div>
      );
    case "librarian":
      return (
        <div>
          <h1 className="text-xl font-semibold text-foreground">
            Librarian Dashboard
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Review pending borrow requests and record returns.
          </p>
        </div>
      );
    case "admin_librarian":
      return (
        <div>
          <h1 className="text-xl font-semibold text-foreground">
            Admin Dashboard
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Manage user accounts and oversee library operations.
          </p>
        </div>
      );
    default:
      return (
        <div>
          <h1 className="text-xl font-semibold text-foreground">Dashboard</h1>
        </div>
      );
  }
}

export function DashboardPage() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <main className="max-w-5xl mx-auto px-6 py-8">
      <WelcomeContent role={user.role} />
    </main>
  );
}
