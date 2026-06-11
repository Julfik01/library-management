// frontend/src/pages/BorrowRequestsPage.tsx
// Phase 2: Librarian borrow requests management (BR-02, BR-03, BR-06)
// Librarians can view pending borrow requests and approve/reject them.
// Students can view their own loans and request history.

import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/axios";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle, XCircle, ClipboardList } from "lucide-react";
import { toast } from "sonner";

interface BorrowRequest {
  id: number;
  student_id: number;
  book_id: number;
  status: "pending" | "approved" | "rejected";
  requested_at: string;
  reviewed_at: string | null;
  reviewed_by: number | null;
}

interface Loan {
  id: number;
  borrow_request_id: number;
  student_id: number;
  book_id: number;
  status: "active" | "returned" | "overdue";
  loan_date: string;
  due_date: string;
  returned_at: string | null;
}

const statusColors: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  pending: "default",
  approved: "secondary",
  rejected: "destructive",
  active: "default",
  returned: "secondary",
  overdue: "destructive",
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function BorrowRequestRow({
  request,
  canManage,
  onApprove,
  onReject,
  isActionPending,
}: {
  request: BorrowRequest;
  canManage: boolean;
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
  isActionPending: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-3 gap-4">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium">Request #{request.id}</span>
          <Badge variant={statusColors[request.status] ?? "outline"} className="text-xs">
            {request.status}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          Book ID: {request.book_id} &bull; Requested: {formatDate(request.requested_at)}
          {request.reviewed_at && ` · Reviewed: ${formatDate(request.reviewed_at)}`}
        </p>
      </div>
      {canManage && request.status === "pending" && (
        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            variant="default"
            className="h-7 text-xs gap-1"
            disabled={isActionPending}
            onClick={() => onApprove(request.id)}
            id={`approve-btn-${request.id}`}
          >
            <CheckCircle className="h-3 w-3" />
            Approve
          </Button>
          <Button
            size="sm"
            variant="destructive"
            className="h-7 text-xs gap-1"
            disabled={isActionPending}
            onClick={() => onReject(request.id)}
            id={`reject-btn-${request.id}`}
          >
            <XCircle className="h-3 w-3" />
            Reject
          </Button>
        </div>
      )}
    </div>
  );
}

function LoanRow({
  loan,
  canReturn,
  onReturn,
  isActionPending,
}: {
  loan: Loan;
  canReturn: boolean;
  onReturn: (id: number) => void;
  isActionPending: boolean;
}) {
  const isOverdue =
    loan.status === "active" && new Date(loan.due_date) < new Date();

  return (
    <div className="flex items-center justify-between py-3 gap-4">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-sm font-medium">Loan #{loan.id}</span>
          <Badge
            variant={isOverdue ? "destructive" : statusColors[loan.status] ?? "outline"}
            className="text-xs"
          >
            {isOverdue ? "overdue" : loan.status}
          </Badge>
        </div>
        <p className="text-xs text-muted-foreground">
          Book ID: {loan.book_id} &bull; Due: {formatDate(loan.due_date)}
          {loan.returned_at && ` · Returned: ${formatDate(loan.returned_at)}`}
        </p>
      </div>
      {canReturn && loan.status === "active" && (
        <Button
          size="sm"
          variant="outline"
          className="h-7 text-xs shrink-0"
          disabled={isActionPending}
          onClick={() => onReturn(loan.id)}
          id={`return-btn-${loan.id}`}
        >
          Record Return
        </Button>
      )}
    </div>
  );
}

export function BorrowRequestsPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const isLibrarian = user?.role === "librarian" || user?.role === "admin_librarian";
  const [activeTab, setActiveTab] = useState<"requests" | "loans">("requests");

  // Fetch borrow requests
  const {
    data: requests,
    isLoading: requestsLoading,
    isError: requestsError,
  } = useQuery<BorrowRequest[]>({
    queryKey: ["borrow-requests"],
    queryFn: async () => {
      const { data } = await api.get("/borrow");
      return data;
    },
  });

  // Fetch loans
  const {
    data: loans,
    isLoading: loansLoading,
    isError: loansError,
  } = useQuery<Loan[]>({
    queryKey: ["loans"],
    queryFn: async () => {
      const { data } = await api.get("/loans");
      return data;
    },
  });

  const approveMutation = useMutation({
    mutationFn: (requestId: number) =>
      api.post(`/borrow/${requestId}/approve`),
    onSuccess: () => {
      toast.success("Borrow request approved. Loan created.");
      queryClient.invalidateQueries({ queryKey: ["borrow-requests"] });
      queryClient.invalidateQueries({ queryKey: ["loans"] });
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err?.response?.data?.detail ?? "Unable to approve request.");
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (requestId: number) =>
      api.post(`/borrow/${requestId}/reject`),
    onSuccess: () => {
      toast.success("Borrow request rejected.");
      queryClient.invalidateQueries({ queryKey: ["borrow-requests"] });
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err?.response?.data?.detail ?? "Unable to reject request.");
    },
  });

  const returnMutation = useMutation({
    mutationFn: (loanId: number) => api.post(`/loans/${loanId}/return`),
    onSuccess: () => {
      toast.success("Book return recorded.");
      queryClient.invalidateQueries({ queryKey: ["loans"] });
    },
    onError: (err: { response?: { data?: { detail?: string } } }) => {
      toast.error(err?.response?.data?.detail ?? "Unable to record return.");
    },
  });

  const pendingRequests = requests?.filter((r) => r.status === "pending") ?? [];
  const processedRequests = requests?.filter((r) => r.status !== "pending") ?? [];

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <ClipboardList className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-xl font-semibold text-foreground">
            {isLibrarian ? "Borrow Requests & Loans" : "My Requests & Loans"}
          </h1>
          <p className="text-sm text-muted-foreground">
            {isLibrarian
              ? "Review pending requests and manage active loans."
              : "Track your borrow requests and active loans."}
          </p>
        </div>
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 mb-6 border-b">
        <button
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeTab === "requests"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("requests")}
          id="tab-requests"
        >
          Requests
          {pendingRequests.length > 0 && (
            <span className="ml-2 bg-primary text-primary-foreground text-xs px-1.5 py-0.5 rounded-full">
              {pendingRequests.length}
            </span>
          )}
        </button>
        <button
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeTab === "loans"
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
          onClick={() => setActiveTab("loans")}
          id="tab-loans"
        >
          Loans
        </button>
      </div>

      {/* Requests tab */}
      {activeTab === "requests" && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {isLibrarian ? "Pending Requests" : "My Borrow Requests"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {requestsError && (
              <Alert variant="destructive">
                <AlertDescription>Unable to load requests.</AlertDescription>
              </Alert>
            )}
            {requestsLoading && (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            )}
            {!requestsLoading && !requestsError && (
              <>
                {/* Pending */}
                {isLibrarian && pendingRequests.length > 0 && (
                  <>
                    <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                      Pending
                    </p>
                    <div className="divide-y">
                      {pendingRequests.map((req) => (
                        <BorrowRequestRow
                          key={req.id}
                          request={req}
                          canManage={isLibrarian}
                          onApprove={(id) => approveMutation.mutate(id)}
                          onReject={(id) => rejectMutation.mutate(id)}
                          isActionPending={
                            approveMutation.isPending || rejectMutation.isPending
                          }
                        />
                      ))}
                    </div>
                    {processedRequests.length > 0 && <Separator className="my-4" />}
                  </>
                )}

                {/* Non-pending / all student requests */}
                {(isLibrarian ? processedRequests : requests ?? []).length > 0 ? (
                  <>
                    {isLibrarian && processedRequests.length > 0 && (
                      <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                        Processed
                      </p>
                    )}
                    <div className="divide-y">
                      {(isLibrarian ? processedRequests : requests ?? []).map((req) => (
                        <BorrowRequestRow
                          key={req.id}
                          request={req}
                          canManage={isLibrarian}
                          onApprove={(id) => approveMutation.mutate(id)}
                          onReject={(id) => rejectMutation.mutate(id)}
                          isActionPending={
                            approveMutation.isPending || rejectMutation.isPending
                          }
                        />
                      ))}
                    </div>
                  </>
                ) : (
                  !isLibrarian && (
                    <p className="text-sm text-muted-foreground py-4 text-center">
                      You haven't submitted any borrow requests yet.{" "}
                      <Link to="/catalog" className="text-primary hover:underline">
                        Browse the catalog
                      </Link>{" "}
                      to get started.
                    </p>
                  )
                )}

                {isLibrarian && pendingRequests.length === 0 && processedRequests.length === 0 && (
                  <p className="text-sm text-muted-foreground py-4 text-center">
                    No borrow requests yet.
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Loans tab */}
      {activeTab === "loans" && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {isLibrarian ? "All Loans" : "My Active Loans"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loansError && (
              <Alert variant="destructive">
                <AlertDescription>Unable to load loans.</AlertDescription>
              </Alert>
            )}
            {loansLoading && (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            )}
            {!loansLoading && !loansError && (
              <>
                {(loans ?? []).length > 0 ? (
                  <div className="divide-y">
                    {(loans ?? []).map((loan) => (
                      <LoanRow
                        key={loan.id}
                        loan={loan}
                        canReturn={isLibrarian}
                        onReturn={(id) => returnMutation.mutate(id)}
                        isActionPending={returnMutation.isPending}
                      />
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground py-4 text-center">
                    {isLibrarian ? "No loans recorded yet." : "You have no active loans."}
                  </p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}

      <div className="mt-6">
        <Link to="/dashboard" className="text-sm text-primary hover:underline">
          ← Back to dashboard
        </Link>
      </div>
    </div>
  );
}
