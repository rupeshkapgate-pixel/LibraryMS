"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ArrowLeft, Edit } from "lucide-react";
import { membersApi } from "@/lib/api";
import { PageHeader, Spinner } from "@/components/ui";
import { formatDate } from "@/lib/utils";
import MemberStatusBadge from "@/components/library/MemberStatusBadge";

export default function MemberDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { data: member, isLoading } = useQuery({
    queryKey: ["members", params.id],
    queryFn: () => membersApi.get(params.id).then((r) => r.data),
  });
  if (isLoading) return <Spinner />;
  if (!member) return <p className="p-6 text-red-600 dark:text-red-300">Member not found.</p>;

  const rows: [string, string | null | undefined][] = [
    ["Phone", member.phone],
    ["Address", member.address],
    ["Joined", formatDate(member.created_at)],
  ];

  return (
    <div>
      <PageHeader
        title="Member Detail"
        action={
          <div className="flex gap-2">
            <button className="btn-secondary" onClick={() => router.back()}><ArrowLeft size={16} /> Back</button>
            <button className="btn-primary" onClick={() => router.push(`/members/${params.id}/edit`)}><Edit size={16} /> Edit</button>
          </div>
        }
      />
      <div className="card max-w-xl p-6">
        <div className="mb-6 flex items-center gap-4">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-indigo-100 text-xl font-bold text-indigo-700 ring-1 ring-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-200 dark:ring-indigo-500/25">
            {member.full_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-950 dark:text-slate-50">{member.full_name}</h2>
            <p className="text-sm text-slate-500 dark:text-slate-400">{member.email}</p>
          </div>
        </div>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
          {rows.map(([label, val]) => (
            <div key={label} className="rounded-xl border border-slate-100 bg-white/50 p-3 dark:border-slate-800 dark:bg-slate-950/35">
              <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{label}</dt>
              <dd className="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-100">{val ?? "—"}</dd>
            </div>
          ))}
          <div className="rounded-xl border border-slate-100 bg-white/50 p-3 dark:border-slate-800 dark:bg-slate-950/35">
            <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Status</dt>
            <dd className="mt-2"><MemberStatusBadge status={member.membership_status} /></dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
