"use client";
import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { lendingApi, booksApi, membersApi } from "@/lib/api";
import { PageHeader} from "@/components/ui";
import { formatDate } from "@/lib/utils";
import type { BorrowRequest, Book, Member, LendingRecord } from "@/types";
import { getErrorMessage } from "@/lib/error";

export default function BorrowBookPage() {
  const qc = useQueryClient();
  const [form, setForm] = useState<BorrowRequest>({ member_id: "", book_id: "", due_days: 14 });
  const [success, setSuccess] = useState<LendingRecord | null>(null);

  const { data: booksData } = useQuery({
    queryKey: ["books-available"],
    queryFn: () => booksApi.list(1, 100).then((r) => r.data),
  });
  const { data: membersData } = useQuery({
    queryKey: ["members-active"],
    queryFn: () => membersApi.list(1, 100).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: (data: BorrowRequest) => lendingApi.borrow(data),
    onSuccess: (res) => {
      setSuccess(res.data);
      toast.success("Book borrowed successfully!");
      qc.invalidateQueries({ queryKey: ["books"] });
      qc.invalidateQueries({ queryKey: ["lending"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e: unknown) => toast.error(getErrorMessage(e, "Borrow failed")),
  });

  const availableBooks = (booksData?.data ?? []).filter((b: Book) => b.available_copies > 0);
  const activeMembers = (membersData?.data ?? []).filter((m: Member) => m.membership_status === "ACTIVE");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.member_id) return toast.error("Select a member");
    if (!form.book_id) return toast.error("Select a book");
    mutation.mutate(form);
  }

  if (success) {
    return (
      <div>
        <PageHeader title="Borrow Book" />
        <div className="card p-6 max-w-md">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center">
              <span className="text-emerald-600 text-xl">✓</span>
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">Borrowed Successfully!</h3>
              <p className="text-sm text-gray-500">Record ID: {success.id?.slice(0, 8)}…</p>
            </div>
          </div>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-gray-500">Due Date</dt><dd className="font-medium">{formatDate(success.due_date)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-500">Status</dt><dd className="badge badge-blue">{success.status}</dd></div>
          </dl>
          <button className="btn-primary w-full mt-6" onClick={() => setSuccess(null)}>Borrow Another Book</button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Borrow Book" description="Issue a book to a member" />
      <div className="card p-6 max-w-md">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="label">Member <span className="text-red-500">*</span></label>
            <select
              className="input"
              value={form.member_id}
              onChange={(e) => setForm((f) => ({ ...f, member_id: e.target.value }))}
            >
              <option value="">Select member…</option>
              {activeMembers.map((m: Member) => (
                <option key={m.id} value={m.id}>{m.full_name} — {m.email}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Book <span className="text-red-500">*</span></label>
            <select
              className="input"
              value={form.book_id}
              onChange={(e) => setForm((f) => ({ ...f, book_id: e.target.value }))}
            >
              <option value="">Select book…</option>
              {availableBooks.map((b: Book) => (
                <option key={b.id} value={b.id}>{b.title} — {b.author} ({b.available_copies} left)</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Due in (days)</label>
            <input
              className="input"
              type="number"
              min={1}
              max={365}
              value={form.due_days}
              onChange={(e) => setForm((f) => ({ ...f, due_days: parseInt(e.target.value) || 14 }))}
            />
          </div>
          <button type="submit" className="btn-primary w-full" disabled={mutation.isPending}>
            {mutation.isPending ? "Processing…" : "Borrow Book"}
          </button>
        </form>
      </div>
    </div>
  );
}
