import { useEffect, useState } from "react";
import { borrowApi } from "@/lib/api/borrow";
import type { BorrowRequest } from "@/lib/api/borrow";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";

export function StudentRequestsPage() {
  const [requests, setRequests] = useState<BorrowRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    borrowApi.listBorrowRequests()
      .then(setRequests)
      .catch(() => setError("Failed to load requests"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton className="h-32 w-full" />;

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">My Borrow Requests</h2>
      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}
      
      {requests.length === 0 && !loading && !error ? (
        <p className="text-muted-foreground">You have no borrow requests.</p>
      ) : (
        <div className="space-y-4">
          {requests.map(req => (
            <div key={req.id} className="p-4 border rounded-lg bg-card">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-medium">Book ID: {req.book_id}</p>
                  <p className="text-sm text-muted-foreground">Requested: {new Date(req.requested_at).toLocaleDateString()}</p>
                </div>
                <div className="flex flex-col items-end gap-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium uppercase tracking-wider
                    ${req.status === 'approved' ? 'bg-green-100 text-green-800' : 
                      req.status === 'rejected' ? 'bg-red-100 text-red-800' : 
                      'bg-yellow-100 text-yellow-800'}`}>
                    {req.status}
                  </span>
                  {req.rejection_note && (
                    <span className="text-xs text-red-600 max-w-xs text-right">
                      Note: {req.rejection_note}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
