"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ArrowLeft, Edit } from "lucide-react";
import { booksApi } from "@/lib/api";
import { PageHeader, Spinner } from "@/components/ui";
import { formatDate } from "@/lib/utils";
import BookAvailabilityBadge from "@/components/library/BookAvailabilityBadge";

export default function BookDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { data: book, isLoading } = useQuery({
    queryKey: ["books", params.id],
    queryFn: () => booksApi.get(params.id).then((r) => r.data),
  });

  if (isLoading) return <Spinner />;
  if (!book) return <p className="p-6 text-red-600 dark:text-red-300">Book not found.</p>;

  const fields: [string, string | number | undefined | null][] = [
    ["Title", book.title],
    ["Author", book.author],
    ["ISBN", book.isbn],
    ["Publisher", book.publisher],
    ["Category", book.category],
    ["Year", book.published_year],
    ["Total Copies", book.total_copies],
    ["Available", book.available_copies],
    ["Shelf", book.shelf_location],
    ["Added", formatDate(book.created_at)],
    ["Updated", formatDate(book.updated_at)],
  ];

  return (
    <div>
      <PageHeader
        title="Book Detail"
        action={
          <div className="flex gap-2">
            <button className="btn-secondary" onClick={() => router.back()}>
              <ArrowLeft size={16} /> Back
            </button>
            <button className="btn-primary" onClick={() => router.push(`/books/${params.id}/edit`)}>
              <Edit size={16} /> Edit
            </button>
          </div>
        }
      />
      <div className="card max-w-2xl p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="mb-1 text-xl font-bold text-slate-950 dark:text-slate-50">{book.title}</h2>
            <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">by {book.author}</p>
          </div>
          <BookAvailabilityBadge available={book.available_copies} total={book.total_copies} />
        </div>
        {book.description && (
          <p className="mb-6 rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-700 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-200">
            {book.description}
          </p>
        )}
        <dl className="grid grid-cols-1 gap-x-6 gap-y-4 sm:grid-cols-2">
          {fields.map(([label, val]) => (
            <div key={label} className="rounded-xl border border-slate-100 bg-white/50 p-3 dark:border-slate-800 dark:bg-slate-950/35">
              <dt className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">{label}</dt>
              <dd className="mt-1 text-sm font-semibold text-slate-900 dark:text-slate-100">{val ?? "—"}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 dark:border-emerald-500/25 dark:bg-emerald-500/10">
          <p className="text-sm font-semibold text-emerald-700 dark:text-emerald-300">
            {book.available_copies} of {book.total_copies} copies available
          </p>
        </div>
      </div>
    </div>
  );
}
