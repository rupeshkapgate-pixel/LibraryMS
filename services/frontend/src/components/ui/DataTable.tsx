"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { LoadingSkeleton } from "./LoadingSkeleton";
import { ErrorState } from "./ErrorState";
import { EmptyState } from "./EmptyState";
import { Pagination } from "./Pagination";

export type ColumnAlign = "left" | "right" | "center";

/** Declarative description of a single table column. */
export interface Column<T> {
  /** Header label (string or node). */
  header: ReactNode;
  /** Cell renderer for a given row. */
  cell: (row: T) => ReactNode;
  /** Optional extra classes for the header cell. */
  headerClassName?: string;
  /** Optional extra classes for the body cell. */
  cellClassName?: string;
  /** Horizontal alignment for both header and body cells. */
  align?: ColumnAlign;
}

/** Pagination footer wiring (optional). */
export interface DataTablePagination {
  page: number;
  totalPages: number;
  totalCount: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

export interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  /** Stable unique key for each row. */
  rowKey: (row: T) => string;

  // Async state — DataTable renders the appropriate placeholder itself.
  isLoading?: boolean;
  isError?: boolean;
  errorMessage?: string;

  // Empty-state customization.
  emptyTitle?: string;
  emptyMessage?: string;
  emptyAction?: ReactNode;

  // Optional pagination footer.
  pagination?: DataTablePagination;

  // Styling hooks (preserve per-page look & feel).
  className?: string;
  theadClassName?: string;
  rowClassName?: (row: T) => string | undefined;
  loadingRows?: number;
  /** When true, render without the surrounding `card` wrapper (for embedding). */
  bare?: boolean;
}

const alignClass = (align?: ColumnAlign) =>
  align === "right" ? "text-right" : align === "center" ? "text-center" : undefined;

/**
 * Generic, reusable table for list views.
 *
 * Consolidates the loading / error / empty / table / pagination pattern that
 * was previously duplicated across every list page. Columns are declared
 * declaratively, so a page only describes *what* to render, not the table
 * scaffolding.
 */
export function DataTable<T>({
  columns,
  data,
  rowKey,
  isLoading = false,
  isError = false,
  errorMessage = "Unable to load data",
  emptyTitle = "No records found",
  emptyMessage = "There is nothing to display yet.",
  emptyAction,
  pagination,
  className,
  theadClassName,
  rowClassName,
  loadingRows = 7,
  bare = false,
}: DataTableProps<T>) {
  let body: ReactNode;

  if (isLoading) {
    body = <LoadingSkeleton rows={loadingRows} />;
  } else if (isError) {
    body = <ErrorState message={errorMessage} />;
  } else if (!data.length) {
    body = (
      <EmptyState title={emptyTitle} message={emptyMessage} action={emptyAction} />
    );
  } else {
    body = (
      <>
        <div className="table-container rounded-none border-0">
          <table>
            <thead className={theadClassName}>
              <tr>
                {columns.map((col, i) => (
                  <th
                    key={i}
                    className={cn(alignClass(col.align), col.headerClassName)}
                  >
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={rowKey(row)} className={rowClassName?.(row)}>
                  {columns.map((col, i) => (
                    <td
                      key={i}
                      className={cn(alignClass(col.align), col.cellClassName)}
                    >
                      {col.cell(row)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {pagination && (
          <Pagination
            page={pagination.page}
            totalPages={pagination.totalPages}
            totalCount={pagination.totalCount}
            pageSize={pagination.pageSize}
            onPage={pagination.onPageChange}
          />
        )}
      </>
    );
  }

  if (bare) return <>{body}</>;
  return <div className={cn("card overflow-hidden", className)}>{body}</div>;
}

export default DataTable;
