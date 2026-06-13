"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, IndianRupee, Mail, RotateCcw } from "lucide-react";
import { lendingApi } from "@/lib/api";
import { DataTable, PageHeader, StatCard } from "@/components/ui";
import type { Column } from "@/components/ui";
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
    () => (q.data?.data ?? []).filter((r: LendingRecord) => isOverdue(r.due_date)),
    [q.data],
  );

  const totalFine = useMemo(
    () => overdueRows.reduce((sum, r) => sum + calculateFine(r.due_date), 0),
    [overdueRows],
  );

  const columns: Column<LendingRecord>[] = [
    {
      header: "Book",
      cell: (r) => (
        <>
          <div className="font-semibold text-slate-950 dark:text-white">
            {r.book_title ?? shortId(r.book_id)}
          </div>
          <div className="font-mono text-xs text-slate-400">{shortId(r.id)}</div>
        </>
      ),
    },
    { header: "Member", cell: (r) => r.member_name ?? shortId(r.member_id) },
    {
      header: "Due Date",
      cell: (r) => formatDate(r.due_date),
      cellClassName: "font-semibold text-red-700",
    },
    {
      header: "Days Overdue",
      cell: (r) => <span className="badge-red">{getDaysOverdue(r.due_date)} days</span>,
    },
    {
      header: "Estimated Fine",
      cell: (r) => formatCurrency(calculateFine(r.due_date)),
      cellClassName: "font-bold text-red-700",
    },
    {
      header: "Contact",
      cell: (r) =>
        r.member_email ? (
          <a
            className="font-medium text-brand-600 hover:underline"
            href={`mailto:${r.member_email}`}
          >
            {r.member_email}
          </a>
        ) : (
          "—"
        ),
    },
    {
      header: "Action",
      align: "right",
      cell: () => (
        <Link href="/lending/return" className="btn-danger px-3 py-2">
          <RotateCcw size={15} />
          Return
        </Link>
      ),
    },
  ];

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

      <DataTable<LendingRecord>
        columns={columns}
        data={overdueRows}
        rowKey={(r) => r.id}
        isLoading={q.isLoading}
        isError={q.isError}
        errorMessage={getErrorMessage(q.error, "Unable to load overdue books")}
        emptyTitle="No overdue books"
        emptyMessage="Great job. There are no overdue lending records right now."
        className="border-red-100"
        theadClassName="bg-red-50"
        rowClassName={() => "bg-red-50/20"}
        pagination={
          q.data
            ? {
                page: q.data.pagination.page,
                totalPages: q.data.pagination.total_pages,
                totalCount: q.data.pagination.total_count,
                pageSize: q.data.pagination.page_size,
                onPageChange: setPage,
              }
            : undefined
        }
      />
    </div>
  );
}
