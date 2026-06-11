import { useEffect, useState } from "react";
import { loansApi } from "@/lib/api/loans";
import type { Loan } from "@/lib/api/loans";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";

export function StudentLoansPage() {
  const [loans, setLoans] = useState<Loan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loansApi.listLoans()
      .then(setLoans)
      .catch(() => setError("Failed to load loans"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Skeleton className="h-32 w-full" />;

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-4">My Loans</h2>
      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}
      
      {loans.length === 0 && !loading && !error ? (
        <p className="text-muted-foreground">You have no loans.</p>
      ) : (
        <div className="space-y-4">
          {loans.map(loan => (
            <div key={loan.id} className="p-4 border rounded-lg bg-card flex justify-between items-center">
              <div>
                <p className="font-medium">Book ID: {loan.book_id}</p>
                <p className="text-sm text-muted-foreground">Loan Date: {new Date(loan.loan_date).toLocaleDateString()}</p>
                <p className="text-sm text-muted-foreground">Due Date: {new Date(loan.due_date).toLocaleDateString()}</p>
                {loan.returned_at && (
                  <p className="text-sm text-green-600">Returned: {new Date(loan.returned_at).toLocaleDateString()}</p>
                )}
              </div>
              <div>
                <span className={`px-2 py-1 rounded text-xs font-medium uppercase tracking-wider
                  ${loan.status === 'active' ? 'bg-blue-100 text-blue-800' : 
                    loan.status === 'returned' ? 'bg-gray-100 text-gray-800' : 
                    'bg-red-100 text-red-800'}`}>
                  {loan.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
