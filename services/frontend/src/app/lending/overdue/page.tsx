"use client";
import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, IndianRupee, Mail, RotateCcw } from "lucide-react";
import { lendingApi } from "@/lib/api";
import {
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  PageHeader,
  Pagination,
  StatCard,
} from "@/components/ui";
import { formatCurrency, formatDate, shortId } from "@/lib/utils";
import { calculateFine, getDaysOverdue, isOverdue } from "@/lib/dateUtils";
import type { LendingRecord } from "@/types";
import { getErrorMessage } from "@/lib/error";
export default function OverdueBooksPage() {
  const [page, setPage] = useState(1);
  const q = useQuery({
    queryKey: ["lending", "overdue", page],
    queryFn: () => lendingApi.overdue(page, 20).then((r) => r.data),
  });
  const overdueRows = useMemo(
    () =>
      (q.data?.data ?? []).filter((r: LendingRecord) => isOverdue(r.due_date)),
    [q.data],
  );
  const totalFine = useMemo(
    () => overdueRows.reduce((sum, r) => sum + calculateFine(r.due_date), 0),
    [overdueRows],
  );
  return (
    <div>
      <PageHeader
        title="Overdue Books"
        description="Priority queue for follow-up, fines, and return actions."
      />
      <div className="mb-6 grid gap-5 sm:grid-cols-3">
        <StatCard
          label="Total Overdue"
          value={overdueRows.length}
          icon={<AlertTriangle size={21} />}
          color="red"
          hint="Requires follow-up"
        />
        <StatCard
          label="Estimated Fine"
          value={formatCurrency(totalFine)}
          icon={<IndianRupee size={21} />}
          color="yellow"
          hint="Based on ₹10/day"
        />
        <StatCard
          label="Escalation"
          value="High"
          icon={<Mail size={21} />}
          color="red"
          hint="Contact members"
        />
      </div>
      <div className="card overflow-hidden border-red-100">
        {q.isLoading ? (
          <LoadingSkeleton rows={7} />
        ) : q.isError ? (
          <ErrorState
            message={getErrorMessage(q.error, "Unable to load overdue books")}
          />
        ) : !overdueRows.length ? (
          <EmptyState
            title="No overdue books"
            message="Great job. There are no overdue lending records right now."
          />
        ) : (
          <>
            <div className="table-container rounded-none border-0">
              <table>
                <thead className="bg-red-50">
                  <tr>
                    <th>Book</th>
                    <th>Member</th>
                    <th>Due Date</th>
                    <th>Days Overdue</th>
                    <th>Estimated Fine</th>
                    <th>Contact</th>
                    <th className="text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {overdueRows.map((r: LendingRecord) => {
                    const d = getDaysOverdue(r.due_date);
                    return (
                      <tr key={r.id} className="bg-red-50/20">
                        <td>
                          <div className="font-semibold text-slate-950 dark:text-white">
                            {r.book_title ?? shortId(r.book_id)}
                          </div>
                          <div className="font-mono text-xs text-slate-400">
                            {shortId(r.id)}
                          </div>
                        </td>
                        <td>{r.member_name ?? shortId(r.member_id)}</td>
                        <td className="font-semibold text-red-700">
                          {formatDate(r.due_date)}
                        </td>
                        <td>
                          <span className="badge-red">{d} days</span>
                        </td>
                        <td className="font-bold text-red-700">
                          {formatCurrency(calculateFine(r.due_date))}
                        </td>
                        <td>
                          {r.member_email ? (
                            <a
                              className="font-medium text-brand-600 hover:underline"
                              href={`mailto:${r.member_email}`}
                            >
                              {r.member_email}
                            </a>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="text-right">
                          <Link
                            href="/lending/return"
                            className="btn-danger px-3 py-2"
                          >
                            <RotateCcw size={15} />
                            Return
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <Pagination
              page={q.data!.pagination.page}
              totalPages={q.data!.pagination.total_pages}
              totalCount={q.data!.pagination.total_count}
              pageSize={q.data!.pagination.page_size}
              onPage={setPage}
            />
          </>
        )}
      </div>
    </div>
  );
}
