// frontend/src/hooks/useLoans.ts
// Typed query hook for loan read API.
// Phase 4 — LOAN-02, LOAN-03, LOAN-04, LOAN-05
// Page-size contract: DEFAULT_PAGE_SIZE = 10, centralized here.

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/axios";

// ---------------------------------------------------------------------------
// Types — mirrors backend/app/schemas/loan.py
// ---------------------------------------------------------------------------

export interface LoanListItem {
  id: number;
  book_title: string;
  student_name: string;
  loan_date: string;   // ISO-8601
  due_date: string;    // ISO-8601
  returned_at: string | null;
  status: "active" | "returned" | "overdue";
  is_overdue: boolean;
  outcome: string;
}

export interface PaginatedLoansResponse {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  items: LoanListItem[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const DEFAULT_PAGE_SIZE = 10;

// ---------------------------------------------------------------------------
// Student loan query params
// ---------------------------------------------------------------------------

export interface StudentLoanParams {
  mode: "student";
  status: "active" | "history";
  page: number;
}

// ---------------------------------------------------------------------------
// Librarian search query params
// ---------------------------------------------------------------------------

export interface LibrarianSearchParams {
  mode: "librarian";
  q: string;          // submitted search term (empty string = no search yet)
  page: number;
}

export type LoanPageParams = StudentLoanParams | LibrarianSearchParams;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useLoansQuery(params: LoanPageParams) {
  if (params.mode === "student") {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    return useQuery<PaginatedLoansResponse>({
      queryKey: ["loans", "me", params.status, params.page],
      queryFn: async () => {
        const { data } = await api.get<PaginatedLoansResponse>("/loans/me", {
          params: {
            status: params.status,
            page: params.page,
            page_size: DEFAULT_PAGE_SIZE,
          },
        });
        return data;
      },
      placeholderData: (prev) => prev,
    });
  }

  // Librarian search — only fire when a non-empty query has been submitted
  // eslint-disable-next-line react-hooks/rules-of-hooks
  return useQuery<PaginatedLoansResponse>({
    queryKey: ["loans", "search", params.q, params.page],
    queryFn: async () => {
      const { data } = await api.get<PaginatedLoansResponse>("/loans/search", {
        params: {
          q: params.q,
          page: params.page,
          page_size: DEFAULT_PAGE_SIZE,
        },
      });
      return data;
    },
    enabled: params.q.trim().length > 0,
    placeholderData: (prev) => prev,
  });
}
