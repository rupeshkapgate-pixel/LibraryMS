"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { membersApi } from "@/lib/api";
import { PageHeader } from "@/components/ui";
import MemberForm from "@/components/forms/MemberForm";
import type { MemberCreate } from "@/types";
import { getErrorMessage } from "@/lib/error";

export default function AddMemberPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: (data: MemberCreate) => membersApi.create(data),
    onSuccess: () => {
      toast.success("Member registered!");
      qc.invalidateQueries({ queryKey: ["members"] });
      router.push("/members");
    },
    onError: (e: unknown) => toast.error(getErrorMessage(e, "Failed to add member")),
  });
  return (
    <div>
      <PageHeader title="Add Member" description="Register a new library member" />
      <div className="card p-6 max-w-2xl">
        <MemberForm onSubmit={(d) => mutation.mutateAsync(d)} loading={mutation.isPending} submitLabel="Register Member" />
      </div>
    </div>
  );
}
