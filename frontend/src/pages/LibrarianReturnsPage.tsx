import { useEffect, useState } from "react";
import { loansApi } from "@/lib/api/loans";
import type { Loan } from "@/lib/api/loans";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export function LibrarianReturnsPage() {
  const [loans, setLoans] = useState<Loan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadLoans = () => {
    setLoading(true);
    loansApi.listLoans("active")
      .then(setLoans)
      .catch(() => setError("Failed to load active loans"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadLoans();
  }, []);

  const handleReturn = async (id: number) => {
    try {
      await loansApi.returnLoan(id);
      loadLoans();
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to process return");
    }
  };

  if (loading && loans.length === 0) return <Skeleton className="h-32 w-full" />;

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">Process Returns (Active Loans)</h2>
      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}
      
      {loans.length === 0 ? (
        <p className="text-muted-foreground">No active loans.</p>
      ) : (
        <div className="space-y-4">
          {loans.map(loan => (
            <div key={loan.id} className="p-4 border rounded-lg bg-card flex justify-between items-center">
              <div>
                <p className="font-medium">Book ID: {loan.book_id} | Student ID: {loan.student_id}</p>
                <p className="text-sm text-muted-foreground">Loan Date: {new Date(loan.loan_date).toLocaleDateString()}</p>
                <p className="text-sm text-muted-foreground">Due Date: {new Date(loan.due_date).toLocaleDateString()}</p>
              </div>
              <Button onClick={() => handleReturn(loan.id)} variant="default">Mark Returned</Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
