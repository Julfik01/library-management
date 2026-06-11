import { api } from "../axios";

export interface BorrowRequest {
  id: number;
  student_id: number;
  book_id: number;
  status: string;
  requested_at: string;
  reviewed_at: string | null;
  reviewed_by: number | null;
  rejection_note: string | null;
}

export const borrowApi = {
  createBorrowRequest: async (bookId: number) => {
    const { data } = await api.post<BorrowRequest>("/borrow-requests", { book_id: bookId });
    return data;
  },

  listBorrowRequests: async (status?: string) => {
    const params = status ? { status } : {};
    const { data } = await api.get<BorrowRequest[]>("/borrow-requests", { params });
    return data;
  },

  approveBorrowRequest: async (id: number) => {
    const { data } = await api.post<{ loan_id: number }>(`/borrow-requests/${id}/approve`);
    return data;
  },

  rejectBorrowRequest: async (id: number, rejectionNote?: string) => {
    const { data } = await api.post<{ message: string }>(`/borrow-requests/${id}/reject`, {
      rejection_note: rejectionNote || null,
    });
    return data;
  },
};
