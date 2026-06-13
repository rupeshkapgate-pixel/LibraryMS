"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { Edit, Eye, Plus, Search, UserX } from "lucide-react";
import { membersApi } from "@/lib/api";
import {
  Button,
  ConfirmDialog,
  DataTable,
  PageHeader,
  Select,
} from "@/components/ui";
import type { Column } from "@/components/ui";
import MemberStatusBadge from "@/components/library/MemberStatusBadge";
import { formatDate } from "@/lib/utils";
import type { Member } from "@/types";
import { getErrorMessage } from "@/lib/error";

export default function MembersPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [deactivateId, setDeactivateId] = useState<string | null>(null);

  const q = useQuery({
    queryKey: ["members", page],
    queryFn: () => membersApi.list(page, 20).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: (id: string) => membersApi.deactivate(id),
    onSuccess: () => {
      toast.success("Member deactivated");
      qc.invalidateQueries({ queryKey: ["members"] });
      setDeactivateId(null);
    },
    onError: (e) => toast.error(getErrorMessage(e, "Deactivate failed")),
  });

  const rows = useMemo(() => {
    let list = q.data?.data ?? [];
    if (search.trim()) {
      const s = search.toLowerCase();
      list = list.filter((m) =>
        [m.full_name, m.email, m.phone].some((v) => v?.toLowerCase().includes(s)),
      );
    }
    if (status !== "all") list = list.filter((m) => m.membership_status === status);
    return list;
  }, [q.data, search, status]);

  const columns: Column<Member>[] = [
    {
      header: "Full Name",
      cell: (m) => m.full_name,
      cellClassName: "font-semibold text-slate-950 dark:text-white",
    },
    { header: "Email", cell: (m) => m.email },
    { header: "Phone", cell: (m) => m.phone ?? "—" },
    { header: "Status", cell: (m) => <MemberStatusBadge status={m.membership_status} /> },
    { header: "Joined On", cell: (m) => formatDate(m.created_at) },
    {
      header: "Actions",
      align: "right",
      cell: (m) => (
        <div className="flex justify-end gap-1">
          <button
            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
            onClick={() => router.push(`/members/${m.id}`)}
            title="View"
            type="button"
          >
            <Eye size={16} />
          </button>
          <button
            className="rounded-lg p-2 text-slate-500 hover:bg-blue-50 hover:text-blue-600 dark:text-slate-400 dark:hover:bg-blue-500/10 dark:hover:text-blue-300"
            onClick={() => router.push(`/members/${m.id}/edit`)}
            title="Edit"
            type="button"
          >
            <Edit size={16} />
          </button>
          <button
            disabled={m.membership_status === "INACTIVE"}
            className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-600 disabled:opacity-30 dark:text-slate-400 dark:hover:bg-red-500/10 dark:hover:text-red-300"
            onClick={() => setDeactivateId(m.id)}
            title="Deactivate"
            type="button"
          >
            <UserX size={16} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Members"
        description="Manage library members and lending eligibility."
        action={
          <Button onClick={() => router.push("/members/add")}>
            <Plus size={16} />
            Add Member
          </Button>
        }
      />
      <div className="card mb-5 grid gap-3 p-4 md:grid-cols-[1fr_200px]">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-3 text-slate-400" size={17} />
          <input
            className="input pl-10"
            placeholder="Search name, email, phone…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search members"
          />
        </div>
        <Select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Filter by status">
          <option value="all">All statuses</option>
          <option value="ACTIVE">ACTIVE</option>
          <option value="INACTIVE">INACTIVE</option>
        </Select>
      </div>

      <DataTable<Member>
        columns={columns}
        data={rows}
        rowKey={(m) => m.id}
        isLoading={q.isLoading}
        isError={q.isError}
        errorMessage={getErrorMessage(q.error, "Unable to load members")}
        emptyTitle="No members found"
        emptyMessage="Try a different search/filter or add a new member."
        emptyAction={<Button onClick={() => router.push("/members/add")}>Add Member</Button>}
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

      <ConfirmDialog
        open={!!deactivateId}
        title="Deactivate member"
        message="Inactive members should not be allowed to borrow new books. Continue?"
        confirmLabel="Deactivate"
        loading={mutation.isPending}
        onConfirm={() => deactivateId && mutation.mutate(deactivateId)}
        onCancel={() => setDeactivateId(null)}
      />
    </div>
  );
}
