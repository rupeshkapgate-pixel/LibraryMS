"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RotateCcw, Search } from "lucide-react";
import { lendingApi } from "@/lib/api";
import { DataTable, PageHeader, Select } from "@/components/ui";
import type { Column } from "@/components/ui";
import LendingStatusBadge from "@/components/library/LendingStatusBadge";
import { formatCurrency, formatDate, shortId } from "@/lib/utils";
import { getDaysOverdue, getDueStatusLabel, isOverdue } from "@/lib/dateUtils";
import type { LendingRecord } from "@/types";
import { getErrorMessage } from "@/lib/error";

export default function BorrowedBooksPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");

  const q = useQuery({
    queryKey: ["lending", "borrowed", page],
    queryFn: () => lendingApi.listBorrowed(page, 20).then((r) => r.data),
  });

  const rows = useMemo(() => {
    let list = q.data?.data ?? [];
    const s = search.toLowerCase();
    if (s)
      list = list.filter((r) =>
        [r.book_title, r.member_name, r.member_email, r.id].some((v) =>
          v?.toLowerCase().includes(s),
        ),
      );
    if (filter === "overdue") list = list.filter((r) => isOverdue(r.due_date));
    if (filter === "current") list = list.filter((r) => !isOverdue(r.due_date));
    return list;
  }, [q.data, search, filter]);

  function timeLabel(r: LendingRecord) {
    if (r.status === "RETURNED") return "Returned";
    return getDueStatusLabel(r.due_date);
  }

  const columns: Column<LendingRecord>[] = [
    {
      header: "Book",
      cell: (r) => (
        <>
          <div className="font-semibold text-slate-950 dark:text-white">
            {r.book_title ?? shortId(r.book_id)}
          </div>
          <div className="font-mono text-xs text-slate-400">{shortId(r.book_id)}</div>
        </>
      ),
    },
    {
      header: "Member",
      cell: (r) => (
        <>
          <div>{r.member_name ?? shortId(r.member_id)}</div>
          <div className="text-xs text-slate-400">{r.member_email ?? "—"}</div>
        </>
      ),
    },
    { header: "Borrowed Date", cell: (r) => formatDate(r.borrowed_at) },
    { header: "Due Date", cell: (r) => formatDate(r.due_date) },
    {
      header: "Days Remaining / Overdue",
      cell: (r) => (
        <span
          className={
            isOverdue(r.due_date)
              ? "font-semibold text-red-600 dark:text-red-300"
              : "font-medium text-slate-700 dark:text-slate-200"
          }
        >
          {timeLabel(r)}
        </span>
      ),
    },
    {
      header: "Status",
      cell: (r) => (
        <>
          <LendingStatusBadge status={isOverdue(r.due_date) ? "OVERDUE" : "BORROWED"} />
          {isOverdue(r.due_date) && getDaysOverdue(r.due_date) > 0 && (
            <div className="mt-1 text-xs font-semibold text-red-600 dark:text-red-300">
              {formatCurrency(getDaysOverdue(r.due_date) * 10)}
            </div>
          )}
        </>
      ),
    },
    {
      header: "Actions",
      align: "right",
      cell: () => (
        <Link href="/lending/return" className="btn-secondary px-3 py-2">
          <RotateCcw size={15} />
          Return
        </Link>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Borrowed Books"
        description="Track current and overdue lending records."
      />
      <div className="card mb-5 grid gap-3 p-4 md:grid-cols-[1fr_220px]">
        <div className="relative">
          <Search className="absolute left-3 top-3 text-slate-400" size={17} />
          <input
            className="input pl-10"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search book, member, email, record…"
            aria-label="Search borrowed records"
          />
        </div>
        <Select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter records">
          <option value="all">All records</option>
          <option value="current">Current</option>
          <option value="overdue">Overdue</option>
        </Select>
      </div>

      <DataTable<LendingRecord>
        columns={columns}
        data={rows}
        rowKey={(r) => r.id}
        isLoading={q.isLoading}
        isError={q.isError}
        errorMessage={getErrorMessage(q.error, "Unable to load borrowed records")}
        emptyTitle="No borrowed books"
        emptyMessage="Active lending records will appear here."
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
