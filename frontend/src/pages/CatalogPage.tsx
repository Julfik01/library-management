import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/lib/axios";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export function CatalogPage() {
  const [books, setBooks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/books")
      .then(res => setBooks(res.data))
      .catch(() => setError("Failed to load catalog"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton className="h-32 w-full" />;

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Library Catalog</h2>
      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {books.map(book => (
          <div key={book.id} className="p-4 border rounded-lg bg-card flex flex-col justify-between">
            <div>
              <h3 className="font-bold text-lg">{book.title}</h3>
              <p className="text-muted-foreground">{book.author}</p>
              <p className="text-sm mt-2">ISBN: {book.isbn}</p>
              <p className="text-sm">Available: {book.available_copies} / {book.total_copies}</p>
            </div>
            <div className="mt-4">
              <Button asChild className="w-full">
                <Link to={`/dashboard/catalog/${book.id}`}>View Details</Link>
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
