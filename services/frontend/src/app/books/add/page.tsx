"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { booksApi } from "@/lib/api";
import { PageHeader } from "@/components/ui";
import BookForm from "@/components/forms/BookForm";
import type { BookCreate } from "@/types";

export default function AddBookPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: (data: BookCreate) => booksApi.create(data),
    onSuccess: () => {
      toast.success("Book added successfully!");
      qc.invalidateQueries({ queryKey: ["books"] });
      router.push("/books");
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? "Failed to add book"),
  });

  return (
    <div>
      <PageHeader title="Add Book" description="Add a new book to the catalogue" />
      <div className="card p-6 max-w-3xl">
        <BookForm
          onSubmit={(data) => mutation.mutateAsync(data)}
          loading={mutation.isPending}
          submitLabel="Add Book"
        />
      </div>
    </div>
  );
}
