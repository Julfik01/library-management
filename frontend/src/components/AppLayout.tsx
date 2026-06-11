// frontend/src/components/AppLayout.tsx
// Shared layout with top navigation for all authenticated pages.
// Provides consistent nav bar across Dashboard, Catalog, Requests, etc.

import { useState } from "react";
import { Link, useNavigate, Outlet } from "react-router-dom";
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

interface NavLink {
  label: string;
  href: string;
  disabled: boolean;
}

function getNavLinks(role: string): NavLink[] {
  const browseLink: NavLink = {
    label: "Browse Catalog",
    href: "/catalog",
    disabled: false,
  };

  switch (role) {
    case "student":
      return [
        { label: "My Loans", href: "/loans", disabled: false },
        browseLink,
      ];
    case "librarian":
      return [
        { label: "Manage Books", href: "/admin/books", disabled: false },
        { label: "Requests", href: "/requests", disabled: false },
        { label: "Returns", href: "/requests", disabled: false },
        browseLink,
      ];
    case "admin_librarian":
      return [
        { label: "Manage Books", href: "/admin/books", disabled: false },
        { label: "Requests", href: "/requests", disabled: false },
        { label: "Returns", href: "/requests", disabled: false },
        { label: "Manage Users", href: "/admin/users/new", disabled: false },
        browseLink,
      ];
    default:
      return [browseLink];
  }
}

function getInitials(fullName: string): string {
  return fullName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((n) => n[0].toUpperCase())
    .join("");
}

export function AppLayout() {
  const navigate = useNavigate();
  const { user, clearAuth } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  if (!user) return null;

  const navLinks = getNavLinks(user.role);
  const initials = getInitials(user.full_name);

  const handleSignOut = async () => {
    setSigningOut(true);
    clearAuth();
    try {
      await api.post("/auth/logout");
    } catch {
      // Best-effort
    }
    navigate("/login", { replace: true });
    setSigningOut(false);
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="bg-card border-b h-14 px-6 flex items-center justify-between">
        <Link to="/dashboard" className="text-base font-semibold text-foreground hover:text-primary transition-colors">
          University Library
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map((link) =>
            link.disabled ? (
              <span
                key={link.href + link.label}
                className="text-sm px-3 py-1.5 text-muted-foreground cursor-not-allowed opacity-50"
                aria-disabled="true"
              >
                {link.label}
              </span>
            ) : (
              <Link
                key={link.href + link.label}
                to={link.href}
                className="text-sm px-3 py-1.5 text-foreground hover:text-primary transition-colors"
              >
                {link.label}
              </Link>
            )
          )}
        </nav>

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
      <main>
        <Outlet />
      </main>
    </div>
  );
}
