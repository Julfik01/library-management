// frontend/src/components/AdminNavLink.tsx
// Renders the "Manage Users" nav link exclusively for admin_librarian role (UI-SPEC Screen 3)
// UX-only role check — backend require_role is the authoritative control (CM-7, T-04-02)

import { Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

/**
 * AdminNavLink: renders a "Manage Users" navigation link that is only visible
 * when the authenticated user holds the admin_librarian role.
 *
 * Security note (T-04-02): This is a UX convenience only. Authorization is
 * enforced server-side via require_role("admin_librarian") on POST /admin/users.
 */
export function AdminNavLink() {
  const { user } = useAuth();

  if (user?.role !== "admin_librarian") {
    return null;
  }

  return (
    <Link
      to="/admin/users/new"
      className="text-sm px-3 py-1.5 text-foreground hover:text-primary transition-colors"
    >
      Manage Users
    </Link>
  );
}
