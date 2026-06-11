"use client";
import { useState } from "react";
import { useMutation, useQueryClient, useQuery } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { lendingApi } from "@/lib/api";
import { PageHeader } from "@/components/ui";
import { formatDate, formatCurrency } from "@/lib/utils";
import type { ReturnResponse, LendingRecord } from "@/types";
import { getErrorMessage } from "@/lib/error";

export default function ReturnBookPage() {
  const qc = useQueryClient();
  const [lendingId, setLendingId] = useState("");
  const [result, setResult] = useState<ReturnResponse | null>(null);

  const { data: borrowedData } = useQuery({
    queryKey: ["lending", "borrowed", 1, 100],
    queryFn: () => lendingApi.listBorrowed(1, 100).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: () => lendingApi.return({ lending_id: lendingId }),
    onSuccess: (res) => {
      setResult(res.data);
      toast.success("Book returned!");
      qc.invalidateQueries({ queryKey: ["lending"] });
      qc.invalidateQueries({ queryKey: ["books"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e: unknown) => toast.error(getErrorMessage(e, "Return failed")),
  });

  const activeBorrows = (borrowedData?.data ?? []).filter(
    (r: LendingRecord) => r.status === "BORROWED" || r.status === "OVERDUE"
  );

  if (result) {
    return (
      <div>
        <PageHeader title="Return Book" />
        <div className="card p-6 max-w-md">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-600 text-xl">✓</div>
            <div>
              <h3 className="font-semibold text-gray-900">Book Returned Successfully!</h3>
            </div>
          </div>
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-gray-500">Returned</dt>
              <dd className="font-medium">{formatDate(result.record.returned_at)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Overdue</dt>
              <dd>{result.is_overdue ? <span className="badge badge-red">Yes — {result.overdue_days} days</span> : <span className="badge badge-green">No</span>}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500">Fine</dt>
              <dd className={result.fine_amount > 0 ? "font-bold text-red-600" : "text-gray-500"}>
                {result.fine_amount > 0 ? formatCurrency(result.fine_amount) : "None"}
              </dd>
            </div>
          </dl>
          <button className="btn-primary w-full mt-6" onClick={() => { setResult(null); setLendingId(""); }}>Return Another Book</button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Return Book" description="Process a book return" />
      <div className="card p-6 max-w-md">
        <div className="space-y-5">
          <div>
            <label className="label">Select Lending Record <span className="text-red-500">*</span></label>
            <select
              className="input"
              value={lendingId}
              onChange={(e) => setLendingId(e.target.value)}
            >
              <option value="">Select a borrowed record…</option>
              {activeBorrows.map((r: LendingRecord) => (
                <option key={r.id} value={r.id}>
                  [{r.status}] Book: {r.book_id.slice(0, 8)}… | Member: {r.member_id.slice(0, 8)}… | Due: {formatDate(r.due_date)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="label">Or enter Lending ID manually</label>
            <input
              className="input font-mono text-sm"
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              value={lendingId}
              onChange={(e) => setLendingId(e.target.value)}
            />
          </div>
          <button
            className="btn-primary w-full"
            onClick={() => {
              if (!lendingId) return toast.error("Select or enter a lending record ID");
              mutation.mutate();
            }}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Processing…" : "Process Return"}
          </button>
        </div>
      </div>
    </div>
  );
}
