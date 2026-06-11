// frontend/src/pages/ManageBooksPage.tsx
// Phase 2 stretch goal: Admin book CRUD UI

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, Plus, Pencil, Trash2, X, Search } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/axios";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";

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

const bookSchema = z.object({
  isbn: z.string().min(1, "ISBN is required"),
  title: z.string().min(1, "Title is required"),
  author: z.string().min(1, "Author is required"),
  total_copies: z.coerce.number().min(1, "Must have at least 1 copy"),
});

type BookFormValues = z.infer<typeof bookSchema>;

export function ManageBooksPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const isAdmin = user?.role === "admin_librarian";

  const [query, setQuery] = useState("");
  const [inputValue, setInputValue] = useState("");
  const [page, setPage] = useState(1);

  // Form mode: 'list' | 'add' | 'edit'
  const [mode, setMode] = useState<"list" | "add" | "edit">("list");
  const [editingBook, setEditingBook] = useState<Book | null>(null);

  const form = useForm<BookFormValues>({
    resolver: zodResolver(bookSchema),
    defaultValues: {
      isbn: "",
      title: "",
      author: "",
      total_copies: 1,
    },
  });

  const { data, isLoading, isError } = useQuery<BookSearchResponse>({
    queryKey: ["admin-books", query, page],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (query.trim()) params.set("q", query.trim());
      params.set("page", String(page));
      params.set("page_size", "10");
      const { data } = await api.get(`/books?${params.toString()}`);
      return data;
    },
    placeholderData: (prev) => prev,
  });

  const createMutation = useMutation({
    mutationFn: (values: BookFormValues) => api.post("/admin/books", values),
    onSuccess: () => {
      toast.success("Book added successfully.");
      queryClient.invalidateQueries({ queryKey: ["admin-books"] });
      setMode("list");
      form.reset();
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to add book.");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, values }: { id: number; values: BookFormValues }) =>
      api.put(`/admin/books/${id}`, values),
    onSuccess: () => {
      toast.success("Book updated successfully.");
      queryClient.invalidateQueries({ queryKey: ["admin-books"] });
      setMode("list");
      setEditingBook(null);
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to update book.");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/admin/books/${id}`),
    onSuccess: () => {
      toast.success("Book deleted.");
      queryClient.invalidateQueries({ queryKey: ["admin-books"] });
    },
    onError: (err: any) => {
      toast.error(err?.response?.data?.detail || "Failed to delete book.");
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setQuery(inputValue);
    setPage(1);
  };

  const handleAddClick = () => {
    form.reset({ isbn: "", title: "", author: "", total_copies: 1 });
    setMode("add");
  };

  const handleEditClick = (book: Book) => {
    form.reset({
      isbn: book.isbn,
      title: book.title,
      author: book.author,
      total_copies: book.total_copies,
    });
    setEditingBook(book);
    setMode("edit");
  };

  const onSubmitForm = (values: BookFormValues) => {
    if (mode === "add") {
      createMutation.mutate(values);
    } else if (mode === "edit" && editingBook) {
      updateMutation.mutate({ id: editingBook.id, values });
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-foreground">Manage Books</h1>
          <p className="text-sm text-muted-foreground">
            Add, update, or remove books from the catalog.
          </p>
        </div>
        {mode === "list" && (
          <Button onClick={handleAddClick} size="sm" className="gap-1">
            <Plus className="h-4 w-4" />
            Add Book
          </Button>
        )}
      </div>

      {(mode === "add" || mode === "edit") && (
        <Card className="mb-8">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <div>
              <CardTitle className="text-lg">
                {mode === "add" ? "Add New Book" : "Edit Book"}
              </CardTitle>
              <CardDescription>
                {mode === "add"
                  ? "Enter the book details to add it to the catalog."
                  : "Update the book's information."}
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => {
                setMode("list");
                setEditingBook(null);
              }}
            >
              <X className="h-4 w-4" />
            </Button>
          </CardHeader>
          <CardContent>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmitForm)} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name="isbn"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>ISBN</FormLabel>
                        <FormControl>
                          <Input placeholder="978-..." {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="total_copies"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Total Copies</FormLabel>
                        <FormControl>
                          <Input type="number" min={1} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <FormField
                  control={form.control}
                  name="title"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Title</FormLabel>
                      <FormControl>
                        <Input placeholder="Book Title" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="author"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Author</FormLabel>
                      <FormControl>
                        <Input placeholder="Author Name" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <div className="flex justify-end pt-2">
                  <Button
                    type="submit"
                    disabled={createMutation.isPending || updateMutation.isPending}
                  >
                    {(createMutation.isPending || updateMutation.isPending) && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    {mode === "add" ? "Save Book" : "Update Book"}
                  </Button>
                </div>
              </form>
            </Form>
          </CardContent>
        </Card>
      )}

      {mode === "list" && (
        <>
          <form onSubmit={handleSearch} className="flex gap-2 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search catalog to manage..."
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                className="pl-9"
              />
            </div>
            <Button type="submit" variant="secondary">
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

          {isError && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>Failed to load books.</AlertDescription>
            </Alert>
          )}

          <Card>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-muted-foreground uppercase bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 font-medium">ISBN</th>
                    <th className="px-4 py-3 font-medium">Title</th>
                    <th className="px-4 py-3 font-medium">Author</th>
                    <th className="px-4 py-3 font-medium text-right">Copies</th>
                    <th className="px-4 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {isLoading ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8">
                        <div className="space-y-3">
                          <Skeleton className="h-4 w-full" />
                          <Skeleton className="h-4 w-full" />
                          <Skeleton className="h-4 w-full" />
                        </div>
                      </td>
                    </tr>
                  ) : data?.items.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                        No books found.
                      </td>
                    </tr>
                  ) : (
                    data?.items.map((book) => (
                      <tr key={book.id} className="hover:bg-muted/50 transition-colors">
                        <td className="px-4 py-3 font-mono text-xs">{book.isbn}</td>
                        <td className="px-4 py-3 font-medium">{book.title}</td>
                        <td className="px-4 py-3 text-muted-foreground">{book.author}</td>
                        <td className="px-4 py-3 text-right">
                          {book.available_copies} / {book.total_copies}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-8 px-2 text-xs"
                              onClick={() => handleEditClick(book)}
                            >
                              <Pencil className="h-3 w-3 mr-1" /> Edit
                            </Button>
                            {isAdmin && (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 px-2 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
                                onClick={() => {
                                  if (confirm(`Delete "${book.title}"? This cannot be undone.`)) {
                                    deleteMutation.mutate(book.id);
                                  }
                                }}
                                disabled={deleteMutation.isPending}
                              >
                                <Trash2 className="h-3 w-3 mr-1" /> Delete
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            
            {data && data.pages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t">
                <span className="text-xs text-muted-foreground">
                  Showing page {data.page} of {data.pages} ({data.total} total)
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Prev
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="h-8 text-xs"
                    disabled={page >= data.pages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
