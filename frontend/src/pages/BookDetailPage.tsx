import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api } from "@/lib/axios";
import { borrowApi } from "@/lib/api/borrow";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/AuthContext";

export function BookDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [book, setBook] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [borrowing, setBorrowing] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");

  useEffect(() => {
    if (!id) return;
    api.get(`/books/${id}`)
      .then(res => setBook(res.data))
      .catch(() => setError("Failed to load book details"))
      .finally(() => setLoading(false));
  }, [id]);

  const handleRequestBorrow = async () => {
    if (!id) return;
    setBorrowing(true);
    setError("");
    setSuccessMsg("");
    try {
      await borrowApi.createBorrowRequest(parseInt(id, 10));
      setSuccessMsg("Borrow request submitted successfully.");
      // Refresh book data
      const res = await api.get(`/books/${id}`);
      setBook(res.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to request borrow");
    } finally {
      setBorrowing(false);
    }
  };

  if (loading) return <Skeleton className="h-64 w-full" />;
  if (!book) return <Alert variant="destructive"><AlertDescription>Book not found</AlertDescription></Alert>;

  return (
    <div className="max-w-2xl mx-auto">
      <Button variant="ghost" onClick={() => navigate(-1)} className="mb-4">← Back to Catalog</Button>
      
      <div className="p-6 border rounded-lg bg-card">
        <h2 className="text-3xl font-bold mb-2">{book.title}</h2>
        <p className="text-xl text-muted-foreground mb-4">{book.author}</p>
        
        <div className="space-y-2 mb-6">
          <p><strong>ISBN:</strong> {book.isbn}</p>
          <p><strong>Total Copies:</strong> {book.total_copies}</p>
          <p><strong>Available Copies:</strong> {book.available_copies}</p>
        </div>

        {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}
        {successMsg && <Alert className="mb-4 bg-green-50 text-green-800 border-green-200"><AlertDescription>{successMsg}</AlertDescription></Alert>}

        {user?.role === "student" && (
          <Button 
            onClick={handleRequestBorrow} 
            disabled={borrowing || book.available_copies <= 0}
            className="w-full"
          >
            {borrowing ? "Requesting..." : book.available_copies > 0 ? "Request Borrow" : "No Copies Available"}
          </Button>
        )}
      </div>
    </div>
  );
}
