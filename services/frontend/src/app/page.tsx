"use client";
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Users, BookMarked, AlertTriangle } from "lucide-react";
import { dashboardApi, lendingApi } from "@/lib/api";
import { StatCard, Spinner, EmptyState } from "@/components/ui";
import { formatDate, formatCurrency, cn } from "@/lib/utils";
import type { LendingRecord } from "@/types";
import Link from "next/link";

const statusBadge: Record<string, string> = {
  BORROWED: "badge-blue",
  RETURNED: "badge-green",
  OVERDUE:  "badge-red",
};

export default function DashboardPage() {
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => dashboardApi.stats().then((r) => r.data),
  });

  const { data: recentData, isLoading: recentLoading } = useQuery({
    queryKey: ["lending", "borrowed", 1, 10],
    queryFn: () => lendingApi.listBorrowed(1, 10).then((r) => r.data),
  });

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">Overview of the library system</p>
      </div>

      {/* Stat cards */}
      {statsLoading ? (
        <Spinner />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
          <StatCard label="Total Books"    value={stats?.total_books    ?? 0} icon={<BookOpen size={22} />}      color="blue" />
          <StatCard label="Total Members"  value={stats?.total_members  ?? 0} icon={<Users size={22} />}         color="green" />
          <StatCard label="Books Borrowed" value={stats?.books_borrowed ?? 0} icon={<BookMarked size={22} />}   color="yellow" />
          <StatCard label="Overdue Books"  value={stats?.overdue_books  ?? 0} icon={<AlertTriangle size={22} />} color="red" />
        </div>
      )}

      {/* Recent transactions */}
      <div className="card">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="font-semibold text-gray-900">Recent Borrowing Activity</h2>
          <Link href="/lending/borrowed" className="text-sm text-brand-600 hover:underline font-medium">
            View all →
          </Link>
        </div>
        {recentLoading ? (
          <Spinner />
        ) : !recentData?.data?.length ? (
          <EmptyState message="No borrowing activity yet." />
        ) : (
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
                {recentData.data.map((r: LendingRecord) => (
                  <tr key={r.id}>
                    <td className="font-mono text-xs">{r.book_id.slice(0, 8)}…</td>
                    <td className="font-mono text-xs">{r.member_id.slice(0, 8)}…</td>
                    <td>{formatDate(r.borrowed_at)}</td>
                    <td>{formatDate(r.due_date)}</td>
                    <td>
                      <span className={cn("badge", statusBadge[r.status] ?? "badge-gray")}>
                        {r.status}
                      </span>
                    </td>
                    <td>{r.fine_amount > 0 ? formatCurrency(r.fine_amount) : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
