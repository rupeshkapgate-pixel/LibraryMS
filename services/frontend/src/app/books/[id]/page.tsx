"use client";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ArrowLeft, Edit } from "lucide-react";
import { booksApi } from "@/lib/api";
import { PageHeader, Spinner } from "@/components/ui";
import { formatDate } from "@/lib/utils";

export default function BookDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { data: book, isLoading } = useQuery({
    queryKey: ["books", params.id],
    queryFn: () => booksApi.get(params.id).then((r) => r.data),
  });

  if (isLoading) return <Spinner />;
  if (!book) return <p className="text-red-500 p-6">Book not found.</p>;

  const fields: [string, string | number | undefined | null][] = [
    ["Title",        book.title],
    ["Author",       book.author],
    ["ISBN",         book.isbn],
    ["Publisher",    book.publisher],
    ["Category",     book.category],
    ["Year",         book.published_year],
    ["Total Copies", book.total_copies],
    ["Available",    book.available_copies],
    ["Shelf",        book.shelf_location],
    ["Added",        formatDate(book.created_at)],
    ["Updated",      formatDate(book.updated_at)],
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
      <div className="card p-6 max-w-2xl">
        <h2 className="text-xl font-bold text-gray-900 mb-1">{book.title}</h2>
        <p className="text-gray-500 text-sm mb-6">by {book.author}</p>
        {book.description && (
          <p className="text-sm text-gray-700 bg-gray-50 rounded-lg p-4 mb-6">{book.description}</p>
        )}
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
          {fields.map(([label, val]) => (
            <div key={label}>
              <dt className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{label}</dt>
              <dd className="mt-0.5 text-sm font-medium text-gray-900">{val ?? "—"}</dd>
            </div>
          ))}
        </dl>
        <div className="mt-6 p-4 rounded-lg bg-emerald-50 border border-emerald-100">
          <p className="text-sm font-semibold text-emerald-700">
            {book.available_copies} of {book.total_copies} copies available
          </p>
        </div>
      </div>
    </div>
  );
}
