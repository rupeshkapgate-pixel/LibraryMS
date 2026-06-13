/**
 * Centralized client-side API configuration.
 *
 * Single source of truth for the API gateway base URL and shared HTTP client
 * settings. Keeping these here (instead of scattering literals across the
 * codebase) means a deployment only has to change one place, and the rest of
 * the app consumes typed constants.
 */

/**
 * Resolve the API gateway base URL.
 *
 * Resolution order:
 *   1. NEXT_PUBLIC_API_BASE_URL  (explicit override, highest priority)
 *   2. NEXT_PUBLIC_API_URL       (the variable wired in next.config.js /
 *                                 docker-compose / .env.example)
 *   3. Same-host fallback in the browser (`<protocol>//<hostname>:8000`)
 *   4. http://localhost:8000     (SSR / build-time default)
 *
 * Supporting both env var names keeps backward compatibility while making the
 * documented `NEXT_PUBLIC_API_URL` actually take effect.
 */
export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }

  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  return "http://localhost:8000";
}

export const API_CONFIG = {
  /** Resolved API gateway base URL. */
  baseUrl: getApiBaseUrl(),
  /** Request timeout in milliseconds. */
  timeoutMs: 30_000,
  /** Default page size for paginated list requests. */
  defaultPageSize: 20,
  /** Hard upper bound on page size (mirrors the gateway's own cap). */
  maxPageSize: 100,
  /** Default JSON headers applied to every request. */
  defaultHeaders: { "Content-Type": "application/json" } as const,
} as const;

/** Convenience alias kept for backward compatibility with existing imports. */
export const API_BASE = API_CONFIG.baseUrl;
