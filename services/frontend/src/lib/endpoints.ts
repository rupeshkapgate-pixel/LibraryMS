/**
 * Centralized API endpoint paths.
 *
 * Every REST path the frontend talks to is declared here exactly once. Routes
 * with path parameters are exposed as builder functions so callers never
 * hand-concatenate URLs. This removes hardcoded endpoint strings from the data
 * layer and makes API surface changes a single-file edit.
 */

/** Shared versioned prefix for all gateway resources. */
export const API_PREFIX = "/api/v1";

export const API_ENDPOINTS = {
  /** Gateway health probe. */
  health: "/health",

  /** Aggregate dashboard statistics. */
  dashboard: `${API_PREFIX}/dashboard`,

  books: {
    root: `${API_PREFIX}/books`,
    search: `${API_PREFIX}/books/search`,
    byId: (id: string) => `${API_PREFIX}/books/${id}`,
  },

  members: {
    root: `${API_PREFIX}/members`,
    byId: (id: string) => `${API_PREFIX}/members/${id}`,
  },

  lending: {
    borrow: `${API_PREFIX}/lending/borrow`,
    return: `${API_PREFIX}/lending/return`,
    borrowed: `${API_PREFIX}/lending/borrowed`,
    overdue: `${API_PREFIX}/lending/overdue`,
    byMember: (memberId: string) => `${API_PREFIX}/lending/member/${memberId}`,
    bookHistory: (bookId: string) =>
      `${API_PREFIX}/lending/book/${bookId}/history`,
  },
} as const;

export type ApiEndpoints = typeof API_ENDPOINTS;
