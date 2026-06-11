// frontend/src/pages/CatalogPage.tsx
// Phase 2: Book catalog browse and search (CAT-01, CAT-02)
// Students can search books and submit borrow requests.
// Librarians/admin_librarians can browse the catalog.

import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Search, BookOpen, ArrowLeft, ArrowRight } from "lucide-react";
import { toast } from "sonner";

interface Book {
  id: number;
  isbn: string;
  title: string;
  author: string;
  total_copies: number;
  available_copies: number;
}

interface BookSearchResponse {
  items: Book[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

async function fetchBooks(q: string, page: number): Promise<BookSearchResponse> {
  const params = new URLSearchParams();
  if (q.trim()) params.set("q", q.trim());
  params.set("page", String(page));
  params.set("page_size", "12");
  const { data } = await api.get(`/books?${params.toString()}`);
  return data;
}

async function borrowBook(bookId: number): Promise<void> {
  await api.post("/borrow", { book_id: bookId });
}

function BookCard({ book, canBorrow }: { book: Book; canBorrow: boolean }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => borrowBook(book.id),
    onSuccess: () => {
      toast.success(`Borrow request submitted for "${book.title}".`);
      queryClient.invalidateQueries({ queryKey: ["books"] });
    },
    onError: (err: { response?: { data?: { detail?: string }; status?: number } }) => {
      const detail = err?.response?.data?.detail ?? "Unable to submit borrow request.";
      toast.error(detail);
    },
  });

  const available = book.available_copies > 0;

  return (
    <Card className="flex flex-col h-full hover:shadow-md transition-shadow">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-sm font-semibold leading-tight line-clamp-2">
              {book.title}
            </CardTitle>
            <CardDescription className="mt-1 text-xs truncate">
              {book.author}
            </CardDescription>
          </div>
          <Badge
            variant={available ? "default" : "secondary"}
            className="shrink-0 text-xs"
          >
            {available ? `${book.available_copies} avail.` : "Unavailable"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col flex-1 gap-2 pt-0">
        <p className="text-xs text-muted-foreground font-mono truncate">
          ISBN: {book.isbn}
        </p>
        <p className="text-xs text-muted-foreground">
          {book.total_copies} {book.total_copies === 1 ? "copy" : "copies"} total
        </p>
        {canBorrow && (
          <div className="mt-auto pt-2">
            <Button
              size="sm"
              variant={available ? "default" : "secondary"}
              className="w-full text-xs"
              disabled={!available || mutation.isPending}
              onClick={() => mutation.mutate()}
              id={`borrow-btn-${book.id}`}
            >
              {mutation.isPending ? "Requesting..." : available ? "Request to Borrow" : "Unavailable"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function BookCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2 mt-1" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-3 w-2/3 mb-2" />
        <Skeleton className="h-8 w-full mt-4" />
      </CardContent>
    </Card>
  );
}

export function CatalogPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["books", query, page],
    queryFn: () => fetchBooks(query, page),
    placeholderData: (prev) => prev,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setQuery(inputValue);
    setPage(1);
  };

  const canBorrow = user?.role === "student";

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <BookOpen className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-xl font-semibold text-foreground">Book Catalog</h1>
          <p className="text-sm text-muted-foreground">
            {canBorrow
              ? "Search for books and submit borrow requests."
              : "Browse the library catalog."}
          </p>
        </div>
      </div>

      {/* Search form */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            id="catalog-search"
            type="text"
            placeholder="Search by title, author, or ISBN..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            className="pl-9"
          />
        </div>
        <Button type="submit" id="catalog-search-btn">
          Search
        </Button>
        {query && (
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setInputValue("");
              setQuery("");
              setPage(1);
            }}
          >
            Clear
          </Button>
        )}
      </form>

      {/* Results summary */}
      {data && (
        <p className="text-sm text-muted-foreground mb-4">
          {query
            ? `${data.total} result${data.total !== 1 ? "s" : ""} for "${query}"`
            : `${data.total} book${data.total !== 1 ? "s" : ""} in catalog`}
        </p>
      )}

      {/* Error state */}
      {isError && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>
            Unable to load the catalog. Please try again.
          </AlertDescription>
        </Alert>
      )}

      {/* Book grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {isLoading
          ? Array.from({ length: 8 }).map((_, i) => <BookCardSkeleton key={i} />)
          : data?.items.map((book) => (
              <BookCard key={book.id} book={book} canBorrow={canBorrow} />
            ))}
      </div>

      {/* Empty state */}
      {!isLoading && data?.items.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          <BookOpen className="h-12 w-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No books found{query ? ` for "${query}"` : ""}.</p>
        </div>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-center gap-4 mt-8">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            id="catalog-prev-page"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {data.page} of {data.pages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= data.pages}
            onClick={() => setPage((p) => p + 1)}
            id="catalog-next-page"
          >
            Next
            <ArrowRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      )}

      {/* Back link */}
      <div className="mt-8">
        <Link
          to="/dashboard"
          className="text-sm text-primary hover:underline"
        >
          ← Back to dashboard
        </Link>
      </div>
    </div>
  );
}
