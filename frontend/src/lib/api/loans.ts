import { api } from "../axios";

export interface Loan {
  id: number;
  borrow_request_id: number;
  student_id: number;
  book_id: number;
  status: string; // 'active' | 'returned' | 'overdue'
  loan_date: string;
  due_date: string;
  returned_at: string | null;
  overdue_notified_at: string | null;
}

export const loansApi = {
  listLoans: async (status?: string) => {
    const params = status ? { status } : {};
    const { data } = await api.get<Loan[]>("/loans", { params });
    return data;
  },

  returnLoan: async (id: number) => {
    const { data } = await api.post(`/loans/${id}/return`);
    return data;
  },
};
