"use client";
import { useState } from "react";
import type { MemberCreate } from "@/types";

interface MemberFormProps {
  initialData?: Partial<MemberCreate>;
  onSubmit: (data: MemberCreate) => Promise<unknown>;
  submitLabel?: string;
  loading?: boolean;
}

export default function MemberForm({ initialData, onSubmit, submitLabel = "Save", loading }: MemberFormProps) {
  const [form, setForm] = useState<MemberCreate>({
    full_name: initialData?.full_name ?? "",
    email: initialData?.email ?? "",
    phone: initialData?.phone ?? "",
    address: initialData?.address ?? "",
  });
  const [errors, setErrors] = useState<Partial<Record<keyof MemberCreate, string>>>({});

  function validate(): boolean {
    const e: typeof errors = {};
    if (!form.full_name.trim()) e.full_name = "Full name is required";
    if (!form.email.trim() || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email))
      e.email = "Valid email is required";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    await onSubmit(form);
  }

  function set(field: keyof MemberCreate, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((er) => ({ ...er, [field]: undefined }));
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div>
          <label className="label">Full Name <span className="text-red-500">*</span></label>
          <input className="input" value={form.full_name} onChange={(e) => set("full_name", e.target.value)} placeholder="John Doe" />
          {errors.full_name && <p className="text-xs text-red-500 mt-1">{errors.full_name}</p>}
        </div>
        <div>
          <label className="label">Email <span className="text-red-500">*</span></label>
          <input className="input" type="email" value={form.email} onChange={(e) => set("email", e.target.value)} placeholder="john@example.com" />
          {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email}</p>}
        </div>
        <div>
          <label className="label">Phone</label>
          <input className="input" type="tel" value={form.phone} onChange={(e) => set("phone", e.target.value)} placeholder="+91 98765 43210" />
        </div>
        <div>
          <label className="label">Address</label>
          <input className="input" value={form.address} onChange={(e) => set("address", e.target.value)} placeholder="123 Main St, City" />
        </div>
      </div>
      <div className="flex gap-3 pt-2">
        <button type="submit" className="btn-primary" disabled={loading}>
          {loading ? "Saving…" : submitLabel}
        </button>
        <button type="button" className="btn-secondary" onClick={() => history.back()}>
          Cancel
        </button>
      </div>
    </form>
  );
}
