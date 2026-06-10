"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { lendingApi } from "@/lib/api";
import { PageHeader, Spinner, EmptyState, Pagination } from "@/components/ui";
import { formatDate, formatCurrency, daysOverdue } from "@/lib/utils";
import type { LendingRecord } from "@/types";

export default function OverdueBooksPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["lending", "overdue", page],
    queryFn: () => lendingApi.overdue(page, 20).then((r) => r.data),
  });

  return (
    <div>
      <PageHeader title="Overdue Books" description="Books not returned by their due date" />
      <div className="card">
        {isLoading ? (
          <Spinner />
        ) : !data?.data?.length ? (
          <EmptyState message="No overdue books. Great job!" />
        ) : (
          <>
            <div className="table-container rounded-none border-0">
              <table>
                <thead>
                  <tr>
                    <th>Record ID</th>
                    <th>Book ID</th>
                    <th>Member ID</th>
                    <th>Due Date</th>
                    <th>Days Overdue</th>
                    <th>Est. Fine</th>
                  </tr>
                </thead>
                <tbody>
                  {data.data.map((r: LendingRecord) => {
                    const days = daysOverdue(r.due_date);
                    return (
                      <tr key={r.id} className="bg-red-50/30">
                        <td className="font-mono text-xs">{r.id.slice(0, 8)}…</td>
                        <td className="font-mono text-xs">{r.book_id.slice(0, 8)}…</td>
                        <td className="font-mono text-xs">{r.member_id.slice(0, 8)}…</td>
                        <td className="text-red-600 font-medium">{formatDate(r.due_date)}</td>
                        <td className="font-bold text-red-700">{days} days</td>
                        <td className="font-bold text-red-700">{formatCurrency(days * 10)}</td>
                      </tr>
                    );
                  })}
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
