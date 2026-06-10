"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { Plus, Search, Edit, Trash2, Eye } from "lucide-react";
import { booksApi } from "@/lib/api";
import { PageHeader, Spinner, EmptyState, Pagination, ConfirmDialog } from "@/components/ui";
import type { Book } from "@/types";

export default function BooksPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["books", page, search],
    queryFn: () =>
      search
        ? booksApi.search(search, "all", page, 20).then((r) => r.data)
        : booksApi.list(page, 20).then((r) => r.data),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => booksApi.delete(id),
    onSuccess: () => {
      toast.success("Book deleted");
      qc.invalidateQueries({ queryKey: ["books"] });
      setDeleteId(null);
    },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? "Delete failed"),
  });

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  }

  return (
    <div>
      <PageHeader
        title="Books"
        description="Manage the library book catalogue"
        action={
          <button className="btn-primary" onClick={() => router.push("/books/add")}>
            <Plus size={16} /> Add Book
          </button>
        }
      />

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-5">
        <input
          className="input max-w-sm"
          placeholder="Search title, author, ISBN…"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />
        <button type="submit" className="btn-secondary">
          <Search size={16} /> Search
        </button>
        {search && (
          <button
            type="button"
            className="btn-secondary"
            onClick={() => { setSearch(""); setSearchInput(""); setPage(1); }}
          >
            Clear
          </button>
        )}
      </form>

      <div className="card">
        {isLoading ? (
          <Spinner />
        ) : !data?.data?.length ? (
          <EmptyState message="No books found. Add your first book!" />
        ) : (
          <>
            <div className="table-container rounded-none border-0">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Author</th>
                    <th>ISBN</th>
                    <th>Category</th>
                    <th>Available</th>
                    <th>Total</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.data.map((b: Book) => (
                    <tr key={b.id}>
                      <td className="font-medium max-w-[200px] truncate">{b.title}</td>
                      <td>{b.author}</td>
                      <td className="font-mono text-xs">{b.isbn}</td>
                      <td>{b.category ?? "—"}</td>
                      <td>
                        <span className={b.available_copies > 0 ? "text-emerald-600 font-medium" : "text-red-500 font-medium"}>
                          {b.available_copies}
                        </span>
                      </td>
                      <td>{b.total_copies}</td>
                      <td className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            className="p-1.5 rounded hover:bg-gray-100 text-gray-500 hover:text-gray-700"
                            onClick={() => router.push(`/books/${b.id}`)}
                            title="View"
                          >
                            <Eye size={15} />
                          </button>
                          <button
                            className="p-1.5 rounded hover:bg-blue-50 text-gray-500 hover:text-blue-600"
                            onClick={() => router.push(`/books/${b.id}/edit`)}
                            title="Edit"
                          >
                            <Edit size={15} />
                          </button>
                          <button
                            className="p-1.5 rounded hover:bg-red-50 text-gray-500 hover:text-red-600"
                            onClick={() => setDeleteId(b.id)}
                            title="Delete"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={data.pagination.page}
              totalPages={data.pagination.total_pages}
              totalCount={data.pagination.total_count}
              pageSize={data.pagination.page_size}
              onPage={setPage}
            />
          </>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteId}
        title="Delete Book"
        message="Are you sure you want to delete this book? This action cannot be undone."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={() => deleteId && deleteMutation.mutate(deleteId)}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
}
