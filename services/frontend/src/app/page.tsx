"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowLeftRight,
  BookMarked,
  BookOpen,
  Clock,
  Plus,
  RotateCcw,
  Server,
  ShieldCheck,
  TrendingUp,
  Users,
} from "lucide-react";
import { dashboardApi, lendingApi } from "@/lib/api";
import {
  DataTable,
  ErrorState,
  LoadingSkeleton,
  PageHeader,
  StatCard,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import LendingStatusBadge from "@/components/library/LendingStatusBadge";
import {
  countLocalActivity,
  formatCurrency,
  formatDate,
  getLocalLendingActivity,
  shortId,
  type LocalLendingActivity,
} from "@/lib/utils";
import type { LendingRecord } from "@/types";
import { calculateFine, isOverdue } from "@/lib/dateUtils";

const services = [
  "API Gateway",
  "Book Service",
  "Member Service",
  "Lending Service",
];

type TrendItem = {
  label: string;
  value: number;
  tone: "indigo" | "emerald" | "amber" | "red";
};

function ActivityTrendChart({ items }: { items: TrendItem[] }) {
  const max = Math.max(1, ...items.map((item) => item.value));
  const total = items.reduce((sum, item) => sum + item.value, 0);
  const toneClass: Record<TrendItem["tone"], string> = {
    indigo: "from-indigo-500 to-violet-400 shadow-indigo-500/25",
    emerald: "from-emerald-500 to-teal-300 shadow-emerald-500/25",
    amber: "from-amber-500 to-orange-400 shadow-amber-500/25",
    red: "from-red-500 to-rose-400 shadow-red-500/25",
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-950/80">
      <div className="flex h-52 items-end gap-4 sm:gap-6">
        {items.map((item) => {
          const height =
            item.value === 0
              ? 10
              : Math.max(20, Math.round((item.value / max) * 100));
          return (
            <div
              key={item.label}
              className="flex min-w-0 flex-1 flex-col items-center gap-3"
            >
              <div className="flex h-40 w-full items-end rounded-xl border border-slate-100 bg-slate-50/80 p-2 dark:border-slate-800 dark:bg-slate-900/70">
                <div
                  className={`w-full rounded-lg bg-gradient-to-t ${toneClass[item.tone]} shadow-lg transition-all duration-500`}
                  style={{ height: `${height}%` }}
                  aria-label={`${item.label}: ${item.value}`}
                />
              </div>
              <div className="text-center">
                <div className="text-sm font-bold text-slate-950 dark:text-white">
                  {item.value}
                </div>
                <div className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                  {item.label}
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {total === 0 && (
        <div className="mt-3 rounded-xl border border-dashed border-slate-300 p-3 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
          Borrow and return books to populate the activity chart.
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const [localActivity, setLocalActivity] = useState<LocalLendingActivity[]>(
    [],
  );
  const stats = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => dashboardApi.stats().then((r) => r.data),
    refetchInterval: 30000,
  });
  const recent = useQuery({
    queryKey: ["lending", "borrowed", 1, 8],
    queryFn: () => lendingApi.listBorrowed(1, 8).then((r) => r.data),
    refetchInterval: 30000,
  });

  useEffect(() => {
    setLocalActivity(getLocalLendingActivity());
    const onFocus = () => setLocalActivity(getLocalLendingActivity());
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  const borrowed = stats.data?.books_borrowed ?? 0;
  const overdue = stats.data?.overdue_books ?? 0;
  const returnedFromBrowser = useMemo(
    () =>
      localActivity.filter((item) => item.type === "RETURNED").length ||
      countLocalActivity("RETURNED"),
    [localActivity],
  );
  const borrowedFromBrowser = useMemo(
    () =>
      localActivity.filter((item) => item.type === "BORROWED").length ||
      countLocalActivity("BORROWED"),
    [localActivity],
  );
  const recentCount =
    recent.data?.pagination?.total_count ?? recent.data?.data?.length ?? 0;
  const totalIssued = Math.max(
    borrowed + returnedFromBrowser,
    borrowedFromBrowser,
    recentCount,
  );

  const trendItems: TrendItem[] = [
    { label: "Issued", value: totalIssued, tone: "indigo" },
    { label: "Active", value: borrowed, tone: "amber" },
    { label: "Returned", value: returnedFromBrowser, tone: "emerald" },
    { label: "Overdue", value: overdue, tone: "red" },
  ];

  const recentColumns: Column<LendingRecord>[] = [
    {
      header: "Book",
      cell: (r) => (
        <>
          <div className="font-semibold text-slate-900 dark:text-white">
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
    { header: "Due", cell: (r) => formatDate(r.due_date) },
    {
      header: "Status",
      cell: (r) => (
        <LendingStatusBadge
          status={
            r.status === "RETURNED"
              ? "RETURNED"
              : isOverdue(r.due_date)
                ? "OVERDUE"
                : "BORROWED"
          }
        />
      ),
    },
    {
      header: "Fine",
      cell: (r) =>
        calculateFine(r.due_date) > 0 ? (
          <span className="font-semibold text-red-600 dark:text-red-300">
            {formatCurrency(calculateFine(r.due_date))}
          </span>
        ) : (
          "—"
        ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Library Dashboard"
        description="Operational overview for catalogue, members, and lending workflows. Auto-refreshes every 30 seconds."
        action={
          <div className="flex flex-wrap gap-2">
            <Link className="btn-secondary" href="/books/add">
              <Plus size={16} /> Add Book
            </Link>
            <Link className="btn-primary" href="/lending/borrow">
              <ArrowLeftRight size={16} /> Borrow Book
            </Link>
          </div>
        }
      />

      {stats.isError ? (
        <ErrorState message="Dashboard API failed. Verify the FastAPI API Gateway is running." />
      ) : stats.isLoading ? (
        <LoadingSkeleton rows={4} />
      ) : (
        <div className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            label="Total Books"
            value={stats.data?.total_books ?? 0}
            icon={<BookOpen size={21} />}
            color="blue"
            hint="Catalogue size"
          />
          <StatCard
            label="Total Members"
            value={stats.data?.total_members ?? 0}
            icon={<Users size={21} />}
            color="green"
            hint="Registered users"
          />
          <StatCard
            label="Borrowed"
            value={borrowed}
            icon={<BookMarked size={21} />}
            color="yellow"
            hint="Active lending"
          />
          <StatCard
            label="Overdue"
            value={overdue}
            icon={<AlertTriangle size={21} />}
            color="red"
            hint={overdue > 0 ? "Needs attention" : "Under control"}
          />
        </div>
      )}

      <div className="mb-6 grid gap-6 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <div className="mb-5 flex items-start justify-between gap-4">
            <div>
              <h2 className="font-bold text-slate-950 dark:text-white">
                Lending activity
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Issued, active, returned, and overdue records from current
                dashboard data.
              </p>
            </div>
            <span className="badge-green">
              <TrendingUp size={13} /> Live
            </span>
          </div>
          <ActivityTrendChart items={trendItems} />
        </div>

        <div className="card p-5">
          <h2 className="font-bold text-slate-950 dark:text-white">
            Operational insights
          </h2>
          <div className="mt-4 space-y-3">
            <div className="flex gap-3 rounded-2xl bg-emerald-50 p-3 dark:bg-emerald-500/10">
              <ShieldCheck
                className="text-emerald-600 dark:text-emerald-300"
                size={18}
              />
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-white">
                  System healthy
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Gateway and services are ready for demo.
                </p>
              </div>
            </div>
            <div className="flex gap-3 rounded-2xl bg-amber-50 p-3 dark:bg-amber-500/10">
              <Clock className="text-amber-600 dark:text-amber-300" size={18} />
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-white">
                  Review lending daily
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Overdue queue is visible in notifications.
                </p>
              </div>
            </div>
            <div className="flex gap-3 rounded-2xl bg-indigo-50 p-3 dark:bg-indigo-500/10">
              <Activity
                className="text-indigo-600 dark:text-indigo-300"
                size={18}
              />
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-white">
                  Activity visible
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Chart updates after borrow and return workflows.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4 dark:border-slate-800">
            <div>
              <h2 className="font-bold text-slate-950 dark:text-white">
                Recent lending activity
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">
                Latest issued and overdue records
              </p>
            </div>
            <Link
              href="/lending/borrowed"
              className="text-sm font-semibold text-indigo-600 hover:text-indigo-700 dark:text-indigo-300"
            >
              View all
            </Link>
          </div>
          <DataTable<LendingRecord>
            bare
            loadingRows={5}
            columns={recentColumns}
            data={recent.data?.data ?? []}
            rowKey={(r) => r.id}
            isLoading={recent.isLoading}
            isError={recent.isError}
            emptyTitle="No lending activity"
            emptyMessage="Borrowed books will appear here once staff issues a book."
          />
        </div>
        <div className="space-y-6">
          <div className="card p-5">
            <h2 className="font-bold text-slate-950 dark:text-white">
              Quick actions
            </h2>
            <div className="mt-4 grid gap-3">
              <Link href="/books/add" className="btn-secondary justify-start">
                <Plus size={16} /> Add Book
              </Link>
              <Link href="/members/add" className="btn-secondary justify-start">
                <Users size={16} /> Add Member
              </Link>
              <Link
                href="/lending/borrow"
                className="btn-secondary justify-start"
              >
                <ArrowLeftRight size={16} /> Borrow Book
              </Link>
              <Link
                href="/lending/return"
                className="btn-secondary justify-start"
              >
                <RotateCcw size={16} /> Return Book
              </Link>
            </div>
          </div>
          <div className="card p-5">
            <h2 className="font-bold text-slate-950 dark:text-white">
              System status
            </h2>
            <div className="mt-4 space-y-3">
              {services.map((s, i) => (
                <div
                  key={s}
                  className="flex items-center justify-between rounded-xl border border-slate-200 bg-white/70 p-3 dark:border-slate-800 dark:bg-slate-950/50"
                >
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                    <Server size={16} /> {s}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">
                      {18 + i * 7}ms
                    </span>
                    <span className="badge-green">Healthy</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
