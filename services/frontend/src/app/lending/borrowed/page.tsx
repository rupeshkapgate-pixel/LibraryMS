"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { lendingApi } from "@/lib/api";
import { PageHeader, Spinner, EmptyState, Pagination } from "@/components/ui";
import { formatDate, formatCurrency, cn } from "@/lib/utils";
import type { LendingRecord } from "@/types";

const badge: Record<string, string> = {
  BORROWED: "badge-blue",
  RETURNED: "badge-green",
  OVERDUE:  "badge-red",
};

export default function BorrowedBooksPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["lending", "borrowed", page],
    queryFn: () => lendingApi.listBorrowed(page, 20).then((r) => r.data),
  });

  return (
    <div>
      <PageHeader title="Borrowed Books" description="All currently borrowed books" />
      <div className="card">
        {isLoading ? (
          <Spinner />
        ) : !data?.data?.length ? (
          <EmptyState message="No books currently borrowed." />
        ) : (
          <>
            <div className="table-container rounded-none border-0">
              <table>
                <thead>
                  <tr>
                    <th>Book ID</th>
                    <th>Member ID</th>
                    <th>Borrowed</th>
                    <th>Due Date</th>
                    <th>Status</th>
                    <th>Fine</th>
                  </tr>
                </thead>
                <tbody>
                  {data.data.map((r: LendingRecord) => (
                    <tr key={r.id}>
                      <td className="font-mono text-xs">{r.book_id.slice(0, 8)}…</td>
                      <td className="font-mono text-xs">{r.member_id.slice(0, 8)}…</td>
                      <td>{formatDate(r.borrowed_at)}</td>
                      <td className={r.status === "OVERDUE" ? "text-red-600 font-semibold" : ""}>{formatDate(r.due_date)}</td>
                      <td><span className={cn("badge", badge[r.status] ?? "badge-gray")}>{r.status}</span></td>
                      <td>{r.fine_amount > 0 ? <span className="text-red-600 font-medium">{formatCurrency(r.fine_amount)}</span> : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={data.pagination.page} totalPages={data.pagination.total_pages} totalCount={data.pagination.total_count} pageSize={data.pagination.page_size} onPage={setPage} />
          </>
        )}
      </div>
    </div>
  );
}
