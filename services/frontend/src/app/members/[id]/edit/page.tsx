"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { membersApi } from "@/lib/api";
import { PageHeader, Spinner } from "@/components/ui";
import MemberForm from "@/components/forms/MemberForm";
import type { MemberCreate } from "@/types";

export default function EditMemberPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const qc = useQueryClient();
  const { data: member, isLoading } = useQuery({
    queryKey: ["members", params.id],
    queryFn: () => membersApi.get(params.id).then((r) => r.data),
  });
  const mutation = useMutation({
    mutationFn: (data: MemberCreate) => membersApi.update(params.id, data),
    onSuccess: () => {
      toast.success("Member updated!");
      qc.invalidateQueries({ queryKey: ["members"] });
      router.push("/members");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? "Update failed"),
  });
  if (isLoading) return <Spinner />;
  if (!member) return <p className="text-red-500 p-6">Member not found.</p>;
  return (
    <div>
      <PageHeader title="Edit Member" description={`Editing: ${member.full_name}`} />
      <div className="card p-6 max-w-2xl">
        <MemberForm initialData={member} onSubmit={(d) => mutation.mutateAsync(d)} loading={mutation.isPending} submitLabel="Save Changes" />
      </div>
    </div>
  );
}
