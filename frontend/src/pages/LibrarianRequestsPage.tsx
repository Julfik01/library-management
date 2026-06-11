import { useEffect, useState } from "react";
import { borrowApi } from "@/lib/api/borrow";
import type { BorrowRequest } from "@/lib/api/borrow";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export function LibrarianRequestsPage() {
  const [requests, setRequests] = useState<BorrowRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadRequests = () => {
    setLoading(true);
    borrowApi.listBorrowRequests("pending")
      .then(setRequests)
      .catch(() => setError("Failed to load requests"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRequests();
  }, []);

  const handleApprove = async (id: number) => {
    try {
      await borrowApi.approveBorrowRequest(id);
      loadRequests();
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to approve");
    }
  };

  const handleReject = async (id: number) => {
    const note = window.prompt("Optional rejection note:");
    if (note === null) return; // cancelled
    
    try {
      await borrowApi.rejectBorrowRequest(id, note);
      loadRequests();
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to reject");
    }
  };

  if (loading && requests.length === 0) return <Skeleton className="h-32 w-full" />;

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Pending Borrow Requests</h2>
      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}
      
      {requests.length === 0 ? (
        <p className="text-muted-foreground">No pending requests.</p>
      ) : (
        <div className="space-y-4">
          {requests.map(req => (
            <div key={req.id} className="p-4 border rounded-lg bg-card flex justify-between items-center">
              <div>
                <p className="font-medium">Book ID: {req.book_id} | Student ID: {req.student_id}</p>
                <p className="text-sm text-muted-foreground">Requested: {new Date(req.requested_at).toLocaleDateString()}</p>
              </div>
              <div className="space-x-2">
                <Button onClick={() => handleApprove(req.id)} variant="default" className="bg-green-600 hover:bg-green-700 text-white">Approve</Button>
                <Button onClick={() => handleReject(req.id)} variant="destructive">Reject</Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
