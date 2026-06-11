// frontend/src/pages/DashboardPage.tsx
// UI-SPEC Screen 3: Dashboard Shell — AUTH-03, AUTH-07
// Copywriting Contract: role-appropriate welcome headings and body text (exact match)
// Nav links: Phase-2+ links shown muted (not hidden) — UI-SPEC Screen 3

import { useState } from "react";
import { useNavigate, Link, Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// Nav link configuration by role (UI-SPEC Screen 3)
interface NavLink {
  label: string;
  href: string;
  disabled: boolean;
}

function getNavLinks(role: string): NavLink[] {
  const browseLink: NavLink = {
    label: "Browse Catalog",
    href: "/catalog",
    disabled: true, // Phase 2
  };

  switch (role) {
    case "student":
      return [
        { label: "My Loans", href: "/dashboard/loans", disabled: false },
        { label: "My Requests", href: "/dashboard/my-requests", disabled: false },
        browseLink,
      ];
    case "librarian":
      return [
        { label: "Requests", href: "/dashboard/requests", disabled: false },
        { label: "Returns", href: "/dashboard/returns", disabled: false },
        browseLink,
      ];
    case "admin_librarian":
      return [
        { label: "Requests", href: "/dashboard/requests", disabled: false },
        { label: "Returns", href: "/dashboard/returns", disabled: false },
        { label: "Manage Users", href: "/admin/users/new", disabled: false },
        browseLink,
      ];
    default:
      return [browseLink];
  }
}

// Role-appropriate welcome content (UI-SPEC Copywriting Contract — exact copy)
export function WelcomeContent({ role }: { role: string }) {
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

// Get user initials from full_name for Avatar
function getInitials(fullName: string): string {
  return fullName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((n) => n[0].toUpperCase())
    .join("");
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { user, clearAuth } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const navLinks = getNavLinks(user.role);
  const initials = getInitials(user.full_name);

  // Logout: POST /auth/logout → clearAuth immediately → navigate /login
  // UI-SPEC Interaction Contracts > Logout
  const handleSignOut = async () => {
    setSigningOut(true);
    // Optimistic: clear auth immediately regardless of API response
    clearAuth();
    try {
      await api.post("/auth/logout");
    } catch {
      // Best-effort server invalidation — session already cleared on client
    }
    navigate("/login", { replace: true });
    setSigningOut(false);
  };

  return (
    <div className="min-h-screen bg-background">
      {/* TopNav (UI-SPEC Screen 3) */}
      <header className="bg-card border-b h-14 px-6 flex items-center justify-between">
        {/* Left: App name */}
        <span className="text-base font-semibold text-foreground">
          University Library
        </span>

        {/* Center: Nav links */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map((link) =>
            link.disabled ? (
              <span
                key={link.href}
                className="text-sm px-3 py-1.5 text-muted-foreground cursor-not-allowed opacity-50"
                aria-disabled="true"
              >
                {link.label}
              </span>
            ) : (
              <Link
                key={link.href}
                to={link.href}
                className="text-sm px-3 py-1.5 text-foreground hover:text-primary transition-colors"
              >
                {link.label}
              </Link>
            )
          )}
        </nav>

        {/* Right: Avatar + dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="h-8 w-8 rounded-full p-0">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="text-xs font-medium">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem
              onClick={handleSignOut}
              disabled={signingOut}
              className="cursor-pointer"
            >
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </header>

      <Separator />

      {/* Main content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
