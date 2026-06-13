import axios, { AxiosError } from "axios";
import type {
  Book,
  BookCreate,
  Member,
  MemberCreate,
  LendingRecord,
  BorrowRequest,
  ReturnRequest,
  ReturnResponse,
  PaginatedResponse,
  DashboardStats,
} from "@/types";
import { API_CONFIG } from "@/lib/config";
import { API_ENDPOINTS } from "@/lib/endpoints";

// Re-exported for backward compatibility with existing imports.
export { getApiBaseUrl, API_BASE } from "@/lib/config";

export interface ApiError {
  message: string;
  status?: number;
  details?: unknown;
}

export function normalizeApiError(
  error: unknown,
  fallback = "Something went wrong",
): ApiError {
  if (axios.isAxiosError(error)) {
    const err = error as AxiosError<{ detail?: string; message?: string }>;
    return {
      message:
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        fallback,
      status: err.response?.status,
      details: err.response?.data,
    };
  }
  if (error instanceof Error) return { message: error.message };
  return { message: fallback };
}

export const api = axios.create({
  baseURL: API_CONFIG.baseUrl,
  timeout: API_CONFIG.timeoutMs,
  headers: { ...API_CONFIG.defaultHeaders },
});

/** Clamp a requested page size to the configured maximum. */
const clampPageSize = (pageSize: number) =>
  Math.min(pageSize, API_CONFIG.maxPageSize);

const DEFAULT_PAGE_SIZE: number = API_CONFIG.defaultPageSize;

export const booksApi = {
  list: (
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
    category?: string,
    sortBy?: string,
    sortOrder?: string,
  ) =>
    api.get<PaginatedResponse<Book>>(API_ENDPOINTS.books.root, {
      params: {
        page,
        page_size: clampPageSize(pageSize),
        ...(category ? { category } : {}),
        ...(sortBy ? { sort_by: sortBy } : {}),
        ...(sortOrder ? { sort_order: sortOrder } : {}),
      },
    }),
  get: (id: string) => api.get<Book>(API_ENDPOINTS.books.byId(id)),
  create: (data: BookCreate) => api.post<Book>(API_ENDPOINTS.books.root, data),
  update: (id: string, data: BookCreate) =>
    api.put<Book>(API_ENDPOINTS.books.byId(id), data),
  delete: (id: string) => api.delete(API_ENDPOINTS.books.byId(id)),
  search: (q: string, searchBy = "all", page = 1, pageSize = DEFAULT_PAGE_SIZE) =>
    api.get<PaginatedResponse<Book>>(API_ENDPOINTS.books.search, {
      params: { q, search_by: searchBy, page, page_size: clampPageSize(pageSize) },
    }),
};

export const membersApi = {
  list: (
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
    sortBy?: string,
    sortOrder?: string,
  ) =>
    api.get<PaginatedResponse<Member>>(API_ENDPOINTS.members.root, {
      params: {
        page,
        page_size: clampPageSize(pageSize),
        ...(sortBy ? { sort_by: sortBy } : {}),
        ...(sortOrder ? { sort_order: sortOrder } : {}),
      },
    }),
  get: (id: string) => api.get<Member>(API_ENDPOINTS.members.byId(id)),
  create: (data: MemberCreate) =>
    api.post<Member>(API_ENDPOINTS.members.root, data),
  update: (id: string, data: MemberCreate) =>
    api.put<Member>(API_ENDPOINTS.members.byId(id), data),
  deactivate: (id: string) => api.delete(API_ENDPOINTS.members.byId(id)),
};

export const lendingApi = {
  borrow: (data: BorrowRequest) =>
    api.post<LendingRecord>(API_ENDPOINTS.lending.borrow, data),
  return: (data: ReturnRequest) =>
    api.post<ReturnResponse>(API_ENDPOINTS.lending.return, data),
  listBorrowed: (page = 1, pageSize = DEFAULT_PAGE_SIZE) =>
    api.get<PaginatedResponse<LendingRecord>>(API_ENDPOINTS.lending.borrowed, {
      params: { page, page_size: clampPageSize(pageSize) },
    }),
  listByMember: (memberId: string, page = 1, pageSize = DEFAULT_PAGE_SIZE) =>
    api.get<PaginatedResponse<LendingRecord>>(
      API_ENDPOINTS.lending.byMember(memberId),
      { params: { page, page_size: clampPageSize(pageSize) } },
    ),
  bookHistory: (bookId: string, page = 1, pageSize = DEFAULT_PAGE_SIZE) =>
    api.get<PaginatedResponse<LendingRecord>>(
      API_ENDPOINTS.lending.bookHistory(bookId),
      { params: { page, page_size: clampPageSize(pageSize) } },
    ),
  overdue: (page = 1, pageSize = DEFAULT_PAGE_SIZE) =>
    api.get<PaginatedResponse<LendingRecord>>(API_ENDPOINTS.lending.overdue, {
      params: { page, page_size: clampPageSize(pageSize) },
    }),
};

export const dashboardApi = {
  stats: () => api.get<DashboardStats>(API_ENDPOINTS.dashboard),
};

export const healthApi = {
  check: () => api.get(API_ENDPOINTS.health),
};
