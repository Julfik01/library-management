// frontend/src/pages/LoansPage.tsx
// Phase 4 — LOAN-02, LOAN-03, LOAN-04, LOAN-05
// Single /loans route shared by students and librarian/admin roles.
// Students: Active/History tabbed table.
// Librarians: Submit-only search box + paginated results table.
// T-04-04: role is read from authenticated context only; backend enforces authorization.

import { useState } from "react";
import { Navigate, Link } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useLoansQuery, type LoanListItem } from "@/hooks/useLoans";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/axios";
import { useNavigate } from "react-router-dom";

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function getInitials(fullName: string): string {
  return fullName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((n) => n[0].toUpperCase())
    .join("");
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------

function LoanStatusBadge({ item }: { item: LoanListItem }) {
  if (item.is_overdue || item.status === "overdue") {
    return (
      <Badge variant="destructive" className="text-xs">
        Overdue
      </Badge>
    );
  }
  if (item.status === "returned") {
    return (
      <Badge variant="success" className="text-xs">
        Returned
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="text-xs">
      Active
    </Badge>
  );
}

// ---------------------------------------------------------------------------
// Pagination controls — numbered pages + prev/next
// ---------------------------------------------------------------------------

interface PaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (p: number) => void;
}

function LoanPagination({ page, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  // Build page number list: always show first, last, current ±1, and ellipsis
  const pages: (number | "…")[] = [];
  const add = (n: number) => {
    if (!pages.includes(n)) pages.push(n);
  };
  add(1);
  if (page > 3) pages.push("…");
  if (page > 2) add(page - 1);
  add(page);
  if (page < totalPages - 1) add(page + 1);
  if (page < totalPages - 2) pages.push("…");
  add(totalPages);

  return (
    <div className="flex items-center justify-center gap-1 mt-4" role="navigation" aria-label="Pagination">
      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        aria-label="Previous page"
      >
        ‹ Prev
      </Button>

      {pages.map((p, i) =>
        p === "…" ? (
          <span key={`ellipsis-${i}`} className="px-2 text-muted-foreground text-sm select-none">
            …
          </span>
        ) : (
          <Button
            key={p}
            variant={p === page ? "default" : "outline"}
            size="sm"
            onClick={() => onPageChange(p as number)}
            aria-label={`Page ${p}`}
            aria-current={p === page ? "page" : undefined}
          >
            {p}
          </Button>
        )
      )}

      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        aria-label="Next page"
      >
        Next ›
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function LoanEmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
      <svg
        className="mb-4 h-12 w-12 opacity-30"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={1.5}
          d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
        />
      </svg>
      <p className="text-sm">{message}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton for table rows
// ---------------------------------------------------------------------------

function TableLoadingSkeleton({ cols }: { cols: number }) {
  return (
    <>
      {Array.from({ length: 4 }).map((_, i) => (
        <TableRow key={i}>
          {Array.from({ length: cols }).map((_, j) => (
            <TableCell key={j}>
              <Skeleton className="h-4 w-full" />
            </TableCell>
          ))}
        </TableRow>
      ))}
    </>
  );
}

// ---------------------------------------------------------------------------
// Student — Active loans table
// ---------------------------------------------------------------------------

function ActiveLoansTable({
  page,
  onPageChange,
}: {
  page: number;
  onPageChange: (p: number) => void;
}) {
  const { data, isLoading, isError } = useLoansQuery({
    mode: "student",
    status: "active",
    page,
  });

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Book</TableHead>
            <TableHead>Borrowed</TableHead>
            <TableHead>Due Date</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            <TableLoadingSkeleton cols={4} />
          ) : isError ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-destructive py-8">
                Failed to load loans. Please try again.
              </TableCell>
            </TableRow>
          ) : data && data.items.length > 0 ? (
            data.items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-medium">{item.book_title}</TableCell>
                <TableCell>{fmtDate(item.loan_date)}</TableCell>
                <TableCell>
                  <span
                    className={
                      item.is_overdue ? "text-destructive font-medium" : undefined
                    }
                  >
                    {fmtDate(item.due_date)}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex flex-col gap-1">
                    <LoanStatusBadge item={item} />
                    {item.is_overdue && (
                      <span className="text-xs text-destructive">
                        This book is past its due date.
                      </span>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={4} className="p-0">
                <LoanEmptyState message="You have no active loans right now. Browse the catalog to find a book to borrow." />
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {data && (
        <LoanPagination
          page={data.page}
          totalPages={data.total_pages}
          onPageChange={onPageChange}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Student — History loans table
// ---------------------------------------------------------------------------

function HistoryLoansTable({
  page,
  onPageChange,
}: {
  page: number;
  onPageChange: (p: number) => void;
}) {
  const { data, isLoading, isError } = useLoansQuery({
    mode: "student",
    status: "history",
    page,
  });

  return (
    <div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Book</TableHead>
            <TableHead>Borrowed</TableHead>
            <TableHead>Due Date</TableHead>
            <TableHead>Returned</TableHead>
            <TableHead>Outcome</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {isLoading ? (
            <TableLoadingSkeleton cols={5} />
          ) : isError ? (
            <TableRow>
              <TableCell colSpan={5} className="text-center text-destructive py-8">
                Failed to load history. Please try again.
              </TableCell>
            </TableRow>
          ) : data && data.items.length > 0 ? (
            data.items.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-medium">{item.book_title}</TableCell>
                <TableCell>{fmtDate(item.loan_date)}</TableCell>
                <TableCell>{fmtDate(item.due_date)}</TableCell>
                <TableCell>
                  {item.returned_at ? fmtDate(item.returned_at) : "—"}
                </TableCell>
                <TableCell>
                  <LoanStatusBadge item={item} />
                </TableCell>
              </TableRow>
            ))
          ) : (
            <TableRow>
              <TableCell colSpan={5} className="p-0">
                <LoanEmptyState message="No borrow history yet. Books you return will appear here." />
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {data && (
        <LoanPagination
          page={data.page}
          totalPages={data.total_pages}
          onPageChange={onPageChange}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Student view — tabbed Active / History
// ---------------------------------------------------------------------------

function StudentLoansView() {
  const [activeTab, setActiveTab] = useState<"active" | "history">("active");
  const [activePage, setActivePage] = useState(1);
  const [historyPage, setHistoryPage] = useState(1);

  const handleTabChange = (value: string) => {
    setActiveTab(value as "active" | "history");
  };

  return (
    <div>
      <h1 className="text-xl font-semibold text-foreground mb-4">My Loans</h1>
      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList className="mb-4">
          <TabsTrigger value="active" id="tab-active">Active</TabsTrigger>
          <TabsTrigger value="history" id="tab-history">History</TabsTrigger>
        </TabsList>

        <TabsContent value="active">
          <ActiveLoansTable
            page={activePage}
            onPageChange={(p) => setActivePage(p)}
          />
        </TabsContent>

        <TabsContent value="history">
          <HistoryLoansTable
            page={historyPage}
            onPageChange={(p) => setHistoryPage(p)}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Librarian view — submit-only search + paginated results
// ---------------------------------------------------------------------------

function LibrarianLoansView() {
  const [inputValue, setInputValue] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useLoansQuery({
    mode: "librarian",
    q: submittedQuery,
    page,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = inputValue.trim();
    if (!q) return;
    setSubmittedQuery(q);
    setPage(1);
  };

  const handleClear = () => {
    setInputValue("");
    setSubmittedQuery("");
    setPage(1);
  };

  return (
    <div>
      <h1 className="text-xl font-semibold text-foreground mb-4">Loan Records</h1>

      {/* Search bar — submit-only (T-04-06) */}
      <form
        onSubmit={handleSearch}
        className="flex gap-2 mb-6"
        role="search"
        aria-label="Search loans"
      >
        <Input
          id="loan-search-input"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Search by student name or book title…"
          className="max-w-md"
          aria-label="Search query"
        />
        <Button type="submit" id="loan-search-submit" disabled={!inputValue.trim()}>
          Search
        </Button>
        {submittedQuery && (
          <Button
            type="button"
            variant="outline"
            onClick={handleClear}
            id="loan-search-clear"
          >
            Clear
          </Button>
        )}
      </form>

      {/* Results */}
      {!submittedQuery ? (
        <LoanEmptyState message="Enter a student name or book title above and press Search to find loan records." />
      ) : (
        <div>
          {submittedQuery && (
            <p className="text-sm text-muted-foreground mb-3">
              Results for <span className="font-medium">"{submittedQuery}"</span>
              {data ? ` — ${data.total_items} record${data.total_items !== 1 ? "s" : ""}` : ""}
            </p>
          )}
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Student</TableHead>
                <TableHead>Book</TableHead>
                <TableHead>Borrowed</TableHead>
                <TableHead>Due Date</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableLoadingSkeleton cols={5} />
              ) : isError ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-destructive py-8">
                    Search failed. Please try again.
                  </TableCell>
                </TableRow>
              ) : data && data.items.length > 0 ? (
                data.items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell>{item.student_name}</TableCell>
                    <TableCell className="font-medium">{item.book_title}</TableCell>
                    <TableCell>{fmtDate(item.loan_date)}</TableCell>
                    <TableCell>
                      <span className={item.is_overdue ? "text-destructive font-medium" : undefined}>
                        {fmtDate(item.due_date)}
                      </span>
                    </TableCell>
                    <TableCell>
                      <LoanStatusBadge item={item} />
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={5} className="p-0">
                    <LoanEmptyState
                      message={`No loan records match "${submittedQuery}". Try a different name or book title.`}
                    />
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>

          {data && (
            <LoanPagination
              page={data.page}
              totalPages={data.total_pages}
              onPageChange={(p) => setPage(p)}
            />
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page shell — shared nav header (same as DashboardPage pattern)
// ---------------------------------------------------------------------------

function NavLink({ href, label, disabled }: { href: string; label: string; disabled: boolean }) {
  if (disabled) {
    return (
      <span className="text-sm px-3 py-1.5 text-muted-foreground cursor-not-allowed opacity-50" aria-disabled="true">
        {label}
      </span>
    );
  }
  return (
    <Link to={href} className="text-sm px-3 py-1.5 text-foreground hover:text-primary transition-colors">
      {label}
    </Link>
  );
}

function getNavLinks(role: string) {
  const browseLink = { label: "Browse Catalog", href: "/catalog", disabled: true };
  const loansLink = { label: role === "student" ? "My Loans" : "Loans", href: "/loans", disabled: false };

  switch (role) {
    case "student":
      return [loansLink, browseLink];
    case "librarian":
      return [
        { label: "Requests", href: "/requests", disabled: true },
        { label: "Returns", href: "/returns", disabled: true },
        loansLink,
        browseLink,
      ];
    case "admin_librarian":
      return [
        { label: "Requests", href: "/requests", disabled: true },
        { label: "Returns", href: "/returns", disabled: true },
        loansLink,
        { label: "Manage Users", href: "/admin/users/new", disabled: false },
        browseLink,
      ];
    default:
      return [browseLink];
  }
}

// ---------------------------------------------------------------------------
// Main export
// ---------------------------------------------------------------------------

export function LoansPage() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const isLibrarian = user.role === "librarian" || user.role === "admin_librarian";

  return (
    <div className="max-w-5xl mx-auto py-8">
      {isLibrarian ? <LibrarianLoansView /> : <StudentLoansView />}
    </div>
  );
}
