# Frontend Review Fixes

This document summarizes the changes made to address the frontend code review
feedback. All changes are confined to `services/frontend`.

## Review comment 1 — Centralize hardcoded API endpoint paths

**Before:** every REST path (`/api/v1/books`, `/api/v1/members/{id}`,
`/api/v1/lending/borrow`, …) and the base-URL/client config were inlined as
string literals throughout `src/lib/api.ts`.

**After:** all paths and client configuration live in dedicated modules and are
consumed via typed constants.

- **`src/lib/endpoints.ts` (new)** — single source of truth for every endpoint.
  A shared `API_PREFIX` plus an `API_ENDPOINTS` object; parameterized routes are
  builder functions (`books.byId(id)`, `lending.byMember(memberId)`,
  `lending.bookHistory(bookId)`), so URLs are never hand-concatenated.
- **`src/lib/config.ts` (new)** — `API_CONFIG` (base URL, timeout, default/max
  page size, default headers) and `getApiBaseUrl()`. Base-URL resolution now
  honors **both** `NEXT_PUBLIC_API_BASE_URL` and the documented
  `NEXT_PUBLIC_API_URL` (the latter previously had no effect — latent bug fixed),
  with a same-host browser fallback.
- **`src/lib/api.ts`** — refactored to import from the two modules above. No
  hardcoded paths remain; page-size clamping uses `API_CONFIG.maxPageSize`. All
  previously exported names (`api`, `booksApi`, `membersApi`, `lendingApi`,
  `dashboardApi`, `healthApi`, `normalizeApiError`, `API_BASE`,
  `getApiBaseUrl`) are preserved, so no call sites needed changing.

Verification: `grep -rn "/api/v1" src` returns matches only in `endpoints.ts`.

## Review comment 2 — Application-level error boundaries + reusable DataTable

### Error boundaries

- **`src/components/layout/ErrorBoundary.tsx` (new)** — a reusable React class
  error boundary with a recoverable fallback (uses `ErrorState` + a "Try again"
  reset) and an optional custom `fallback` render prop. Wired into `AppShell`
  around all page content, so a render error in any page degrades gracefully
  instead of unmounting the app.
- **`src/app/error.tsx` (new)** — Next.js App Router route-segment error
  boundary with a `reset()` recovery action.
- **`src/app/global-error.tsx` (new)** — root-level error boundary that catches
  errors in the layout itself (renders its own `<html>/<body>` with inline
  styles, as required by Next.js).

### Reusable DataTable

- **`src/components/ui/DataTable.tsx`** — replaced the previous one-line
  `<table>` wrapper with a generic, column-driven component:
  - Declarative `Column<T>` API (`header`, `cell`, `align`, class hooks).
  - Built-in loading / error / empty states and an optional pagination footer.
  - Styling hooks (`className`, `theadClassName`, `rowClassName`) and a `bare`
    mode for embedding inside existing cards.
- **`src/components/ui/Pagination.tsx` (new)** — `Pagination` was extracted from
  the `ui` barrel into its own file (avoids a circular import with `DataTable`
  and is cleaner). Re-exported from the barrel, so existing imports still work.
- **`src/components/ui/index.tsx`** — exports `Pagination` from its new file and
  re-exports the `DataTable` types (`Column`, `DataTableProps`, etc.).

### List views migrated to DataTable

The repeated loading/error/empty/table/pagination boilerplate was removed from
every list view, which now declares columns and delegates to `DataTable`:

- `src/app/books/page.tsx`
- `src/app/members/page.tsx`
- `src/app/lending/borrowed/page.tsx`
- `src/app/lending/overdue/page.tsx`
- `src/app/page.tsx` (dashboard "Recent lending activity", using `bare` mode)

## Validation performed

All run inside `services/frontend`:

- `npx tsc --noEmit` — passes with 0 type errors.
- `npm run lint` (`next lint`) — no ESLint warnings or errors.
- `npm run build` (`next build`) — compiles successfully; all 12 routes build.

No backend, proto, or infrastructure files were modified.
