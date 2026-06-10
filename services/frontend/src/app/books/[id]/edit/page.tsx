"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { booksApi } from "@/lib/api";
import { PageHeader, Spinner } from "@/components/ui";
import BookForm from "@/components/forms/BookForm";
import type { BookCreate } from "@/types";

export default function EditBookPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: book, isLoading } = useQuery({
    queryKey: ["books", params.id],
    queryFn: () => booksApi.get(params.id).then((r) => r.data),
  });

  const mutation = useMutation({
    mutationFn: (data: BookCreate) => booksApi.update(params.id, data),
    onSuccess: () => {
      toast.success("Book updated successfully!");
      qc.invalidateQueries({ queryKey: ["books"] });
      router.push("/books");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? "Update failed"),
  });

  if (isLoading) return <Spinner />;
  if (!book) return <p className="text-red-500 p-6">Book not found.</p>;

  return (
    <div>
      <PageHeader title="Edit Book" description={`Editing: ${book.title}`} />
      <div className="card p-6 max-w-3xl">
        <BookForm
          initialData={book}
          onSubmit={(data) => mutation.mutateAsync(data)}
          loading={mutation.isPending}
          submitLabel="Save Changes"
        />
      </div>
    </div>
  );
}
