"use client";
import { useState } from "react";
import type { BookCreate } from "@/types";

interface BookFormProps {
  initialData?: Partial<BookCreate>;
  onSubmit: (data: BookCreate) => Promise<void>;
  submitLabel?: string;
  loading?: boolean;
}

const CATEGORIES = [
  "Fiction", "Non-Fiction", "Science", "Technology", "History",
  "Biography", "Children", "Mystery", "Romance", "Self-Help", "Other",
];

export default function BookForm({ initialData, onSubmit, submitLabel = "Save", loading }: BookFormProps) {
  const [form, setForm] = useState<BookCreate>({
    title: initialData?.title ?? "",
    author: initialData?.author ?? "",
    isbn: initialData?.isbn ?? "",
    publisher: initialData?.publisher ?? "",
    category: initialData?.category ?? "",
    description: initialData?.description ?? "",
    published_year: initialData?.published_year ?? undefined,
    total_copies: initialData?.total_copies ?? 1,
    shelf_location: initialData?.shelf_location ?? "",
  });
  const [errors, setErrors] = useState<Partial<Record<keyof BookCreate, string>>>({});

  function validate(): boolean {
    const e: typeof errors = {};
    if (!form.title.trim()) e.title = "Title is required";
    if (!form.author.trim()) e.author = "Author is required";
    if (!form.isbn.trim() || form.isbn.length < 10) e.isbn = "Valid ISBN required (min 10 chars)";
    if (form.total_copies < 1) e.total_copies = "At least 1 copy required";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;
    await onSubmit(form);
  }

  function set(field: keyof BookCreate, value: string | number | undefined) {
    setForm((f) => ({ ...f, [field]: value }));
    setErrors((er) => ({ ...er, [field]: undefined }));
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div>
          <label className="label">Title <span className="text-red-500">*</span></label>
          <input className="input" value={form.title} onChange={(e) => set("title", e.target.value)} placeholder="Book title" />
          {errors.title && <p className="text-xs text-red-500 mt-1">{errors.title}</p>}
        </div>
        <div>
          <label className="label">Author <span className="text-red-500">*</span></label>
          <input className="input" value={form.author} onChange={(e) => set("author", e.target.value)} placeholder="Author name" />
          {errors.author && <p className="text-xs text-red-500 mt-1">{errors.author}</p>}
        </div>
        <div>
          <label className="label">ISBN <span className="text-red-500">*</span></label>
          <input className="input font-mono" value={form.isbn} onChange={(e) => set("isbn", e.target.value)} placeholder="978-..." />
          {errors.isbn && <p className="text-xs text-red-500 mt-1">{errors.isbn}</p>}
        </div>
        <div>
          <label className="label">Publisher</label>
          <input className="input" value={form.publisher} onChange={(e) => set("publisher", e.target.value)} placeholder="Publisher name" />
        </div>
        <div>
          <label className="label">Category</label>
          <select className="input" value={form.category} onChange={(e) => set("category", e.target.value)}>
            <option value="">Select category</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Published Year</label>
          <input
            className="input"
            type="number"
            min={1000}
            max={2100}
            value={form.published_year ?? ""}
            onChange={(e) => set("published_year", e.target.value ? parseInt(e.target.value) : undefined)}
            placeholder="e.g. 2020"
          />
        </div>
        <div>
          <label className="label">Total Copies <span className="text-red-500">*</span></label>
          <input
            className="input"
            type="number"
            min={1}
            value={form.total_copies}
            onChange={(e) => set("total_copies", parseInt(e.target.value) || 1)}
          />
          {errors.total_copies && <p className="text-xs text-red-500 mt-1">{errors.total_copies}</p>}
        </div>
        <div>
          <label className="label">Shelf Location</label>
          <input className="input" value={form.shelf_location} onChange={(e) => set("shelf_location", e.target.value)} placeholder="e.g. A3-12" />
        </div>
      </div>
      <div>
        <label className="label">Description</label>
        <textarea
          className="input h-24 resize-none"
          value={form.description}
          onChange={(e) => set("description", e.target.value)}
          placeholder="Brief description of the book"
        />
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
