"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ArrowLeft, Edit } from "lucide-react";
import { membersApi } from "@/lib/api";
import { PageHeader, Spinner } from "@/components/ui";
import { formatDate, cn } from "@/lib/utils";

export default function MemberDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { data: member, isLoading } = useQuery({
    queryKey: ["members", params.id],
    queryFn: () => membersApi.get(params.id).then((r) => r.data),
  });
  if (isLoading) return <Spinner />;
  if (!member) return <p className="text-red-500 p-6">Member not found.</p>;
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
      <div className="card p-6 max-w-xl">
        <div className="flex items-center gap-4 mb-6">
          <div className="w-14 h-14 rounded-full bg-brand-100 flex items-center justify-center text-brand-700 font-bold text-xl">
            {member.full_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <h2 className="text-xl font-bold text-gray-900">{member.full_name}</h2>
            <p className="text-sm text-gray-500">{member.email}</p>
          </div>
        </div>
        <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
          {[
            ["Phone",   member.phone],
            ["Address", member.address],
            ["Status",  member.membership_status],
            ["Joined",  formatDate(member.created_at)],
          ].map(([label, val]) => (
            <div key={label as string}>
              <dt className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{label}</dt>
              <dd className="mt-0.5 text-sm font-medium text-gray-900">
                {label === "Status" ? (
                  <span className={cn("badge", val === "ACTIVE" ? "badge-green" : "badge-gray")}>{val}</span>
                ) : (val ?? "—")}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </div>
  );
}
