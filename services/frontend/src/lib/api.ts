import axios, { AxiosError } from "axios";
import type { Book, BookCreate, Member, MemberCreate, LendingRecord, BorrowRequest, ReturnRequest, ReturnResponse, PaginatedResponse, DashboardStats } from "@/types";

export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  return "http://localhost:8000";
}

export const API_BASE = getApiBaseUrl();

export interface ApiError { message: string; status?: number; details?: unknown }

export function normalizeApiError(error: unknown, fallback = "Something went wrong"): ApiError {
  if (axios.isAxiosError(error)) {
    const err = error as AxiosError<{ detail?: string; message?: string }>;
    return { message: err.response?.data?.detail || err.response?.data?.message || err.message || fallback, status: err.response?.status, details: err.response?.data };
  }
  if (error instanceof Error) return { message: error.message };
  return { message: fallback };
}

export const api = axios.create({ baseURL: API_BASE, timeout: 30_000, headers: { "Content-Type": "application/json" } });

export const booksApi = {
  list: (page = 1, pageSize = 20, category?: string, sortBy?: string, sortOrder?: string) => api.get<PaginatedResponse<Book>>("/api/v1/books", {
    params: { page, page_size: Math.min(pageSize, 100), ...(category ? { category } : {}), ...(sortBy ? { sort_by: sortBy } : {}), ...(sortOrder ? { sort_order: sortOrder } : {}) },
  }),
  get: (id: string) => api.get<Book>(`/api/v1/books/${id}`),
  create: (data: BookCreate) => api.post<Book>("/api/v1/books", data),
  update: (id: string, data: BookCreate) => api.put<Book>(`/api/v1/books/${id}`, data),
  delete: (id: string) => api.delete(`/api/v1/books/${id}`),
  search: (q: string, searchBy = "all", page = 1, pageSize = 20) => api.get<PaginatedResponse<Book>>("/api/v1/books/search", { params: { q, search_by: searchBy, page, page_size: Math.min(pageSize, 100) } }),
};

export const membersApi = {
  list: (page = 1, pageSize = 20, sortBy?: string, sortOrder?: string) => api.get<PaginatedResponse<Member>>("/api/v1/members", {
    params: { page, page_size: Math.min(pageSize, 100), ...(sortBy ? { sort_by: sortBy } : {}), ...(sortOrder ? { sort_order: sortOrder } : {}) },
  }),
  get: (id: string) => api.get<Member>(`/api/v1/members/${id}`),
  create: (data: MemberCreate) => api.post<Member>("/api/v1/members", data),
  update: (id: string, data: MemberCreate) => api.put<Member>(`/api/v1/members/${id}`, data),
  deactivate: (id: string) => api.delete(`/api/v1/members/${id}`),
};

export const lendingApi = {
  borrow: (data: BorrowRequest) => api.post<LendingRecord>("/api/v1/lending/borrow", data),
  return: (data: ReturnRequest) => api.post<ReturnResponse>("/api/v1/lending/return", data),
  listBorrowed: (page = 1, pageSize = 20) => api.get<PaginatedResponse<LendingRecord>>("/api/v1/lending/borrowed", { params: { page, page_size: Math.min(pageSize, 100) } }),
  listByMember: (memberId: string, page = 1, pageSize = 20) => api.get<PaginatedResponse<LendingRecord>>(`/api/v1/lending/member/${memberId}`, { params: { page, page_size: Math.min(pageSize, 100) } }),
  bookHistory: (bookId: string, page = 1, pageSize = 20) => api.get<PaginatedResponse<LendingRecord>>(`/api/v1/lending/book/${bookId}/history`, { params: { page, page_size: Math.min(pageSize, 100) } }),
  overdue: (page = 1, pageSize = 20) => api.get<PaginatedResponse<LendingRecord>>("/api/v1/lending/overdue", { params: { page, page_size: Math.min(pageSize, 100) } }),
};

export const dashboardApi = { stats: () => api.get<DashboardStats>("/api/v1/dashboard") };
export const healthApi = { check: () => api.get("/health") };
