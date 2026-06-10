import axios from "axios";
import type {
  Book, BookCreate, BookUpdate,
  Member, MemberCreate, MemberUpdate,
  LendingRecord, BorrowRequest, ReturnRequest, ReturnResponse,
  PaginatedResponse, DashboardStats,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
  headers: { "Content-Type": "application/json" },
});

// ── Books ─────────────────────────────────────────────────────────────────
export const booksApi = {
  list: (page = 1, pageSize = 20, category?: string, sortBy = "created_at", sortOrder = "desc") =>
    api.get<PaginatedResponse<Book>>("/api/v1/books", {
      params: { page, page_size: pageSize, category, sort_by: sortBy, sort_order: sortOrder },
    }),
  get: (id: string) => api.get<Book>(`/api/v1/books/${id}`),
  create: (data: BookCreate) => api.post<Book>("/api/v1/books", data),
  update: (id: string, data: BookUpdate) => api.put<Book>(`/api/v1/books/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/books/${id}`),
  search: (q: string, searchBy = "all", page = 1, pageSize = 20) =>
    api.get<PaginatedResponse<Book>>("/api/v1/books/search", {
      params: { q, search_by: searchBy, page, page_size: pageSize },
    }),
};

// ── Members ───────────────────────────────────────────────────────────────
export const membersApi = {
  list: (page = 1, pageSize = 20, sortBy = "created_at", sortOrder = "desc") =>
    api.get<PaginatedResponse<Member>>("/api/v1/members", {
      params: { page, page_size: pageSize, sort_by: sortBy, sort_order: sortOrder },
    }),
  get: (id: string) => api.get<Member>(`/api/v1/members/${id}`),
  create: (data: MemberCreate) => api.post<Member>("/api/v1/members", data),
  update: (id: string, data: MemberUpdate) => api.put<Member>(`/api/v1/members/${id}`, data),
  deactivate: (id: string) => api.delete(`/api/v1/members/${id}`),
};

// ── Lending ───────────────────────────────────────────────────────────────
export const lendingApi = {
  borrow: (data: BorrowRequest) => api.post<LendingRecord>("/api/v1/lending/borrow", data),
  return: (data: ReturnRequest) => api.post<ReturnResponse>("/api/v1/lending/return", data),
  listBorrowed: (page = 1, pageSize = 20) =>
    api.get<PaginatedResponse<LendingRecord>>("/api/v1/lending/borrowed", {
      params: { page, page_size: pageSize },
    }),
  listByMember: (memberId: string, page = 1, pageSize = 20) =>
    api.get<PaginatedResponse<LendingRecord>>(`/api/v1/lending/member/${memberId}`, {
      params: { page, page_size: pageSize },
    }),
  bookHistory: (bookId: string, page = 1, pageSize = 20) =>
    api.get<PaginatedResponse<LendingRecord>>(`/api/v1/lending/book/${bookId}/history`, {
      params: { page, page_size: pageSize },
    }),
  overdue: (page = 1, pageSize = 20) =>
    api.get<PaginatedResponse<LendingRecord>>("/api/v1/lending/overdue", {
      params: { page, page_size: pageSize },
    }),
};

// ── Dashboard ─────────────────────────────────────────────────────────────
export const dashboardApi = {
  stats: () => api.get<DashboardStats>("/api/v1/dashboard"),
};
