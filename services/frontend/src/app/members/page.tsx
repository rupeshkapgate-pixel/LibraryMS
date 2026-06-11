"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { Plus, Edit, UserX, Eye } from "lucide-react";
import { membersApi } from "@/lib/api";
import { PageHeader, Spinner, EmptyState, Pagination, ConfirmDialog } from "@/components/ui";
import { cn } from "@/lib/utils";
import type { Member } from "@/types";
import { getErrorMessage } from "@/lib/error";

export default function MembersPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [deactivateId, setDeactivateId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["members", page],
    queryFn: () => membersApi.list(page, 20).then((r) => r.data),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: string) => membersApi.deactivate(id),
    onSuccess: () => {
      toast.success("Member deactivated");
      qc.invalidateQueries({ queryKey: ["members"] });
      setDeactivateId(null);
    },
    onError: (e: unknown) => toast.error(getErrorMessage(e, "Failed to deactivate")),
  });

  return (
    <div>
      <PageHeader
        title="Members"
        description="Manage library members"
        action={
          <button className="btn-primary" onClick={() => router.push("/members/add")}>
            <Plus size={16} /> Add Member
          </button>
        }
      />

      <div className="card">
        {isLoading ? (
          <Spinner />
        ) : !data?.data?.length ? (
          <EmptyState message="No members yet. Add your first member!" />
        ) : (
          <>
            <div className="table-container rounded-none border-0">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>Status</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.data.map((m: Member) => (
                    <tr key={m.id}>
                      <td className="font-medium">{m.full_name}</td>
                      <td className="text-gray-500">{m.email}</td>
                      <td>{m.phone ?? "—"}</td>
                      <td>
                        <span className={cn("badge", m.membership_status === "ACTIVE" ? "badge-green" : "badge-gray")}>
                          {m.membership_status}
                        </span>
                      </td>
                      <td className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button className="p-1.5 rounded hover:bg-gray-100 text-gray-500" onClick={() => router.push(`/members/${m.id}`)} title="View">
                            <Eye size={15} />
                          </button>
                          <button className="p-1.5 rounded hover:bg-blue-50 text-gray-500 hover:text-blue-600" onClick={() => router.push(`/members/${m.id}/edit`)} title="Edit">
                            <Edit size={15} />
                          </button>
                          {m.membership_status === "ACTIVE" && (
                            <button className="p-1.5 rounded hover:bg-amber-50 text-gray-500 hover:text-amber-600" onClick={() => setDeactivateId(m.id)} title="Deactivate">
                              <UserX size={15} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={data.pagination.page}
              totalPages={data.pagination.total_pages}
              totalCount={data.pagination.total_count}
              pageSize={data.pagination.page_size}
              onPage={setPage}
            />
          </>
        )}
      </div>

      <ConfirmDialog
        open={!!deactivateId}
        title="Deactivate Member"
        message="This member will lose borrowing privileges. They will not be deleted."
        confirmLabel="Deactivate"
        variant="danger"
        onConfirm={() => deactivateId && deactivateMutation.mutate(deactivateId)}
        onCancel={() => setDeactivateId(null)}
      />
    </div>
  );
}
