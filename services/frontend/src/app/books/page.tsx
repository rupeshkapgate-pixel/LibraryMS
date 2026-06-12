"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { Edit, Eye, Plus, Search, Trash2 } from "lucide-react";
import { booksApi } from "@/lib/api";
import {
  Button,
  ConfirmDialog,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
  PageHeader,
  Pagination,
  Select,
} from "@/components/ui";
import BookAvailabilityBadge from "@/components/library/BookAvailabilityBadge";
import type { Book } from "@/types";
import { getErrorMessage } from "@/lib/error";

const PAGE_SIZE = 20;

export default function BooksPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const [page, setPage] = useState(1);
  const [searchInput, setSearchInput] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [category, setCategory] = useState("");
  const [availability, setAvailability] = useState("all");
  const [sort, setSort] = useState("created_at:desc");
  const [deleteId, setDeleteId] = useState<string | null>(null);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchInput.trim());
      setPage(1);
    }, 300);

    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const q = useQuery({
    queryKey: ["books", page, debouncedSearch, category],
    queryFn: () =>
      debouncedSearch
        ? booksApi.search(debouncedSearch, "all", page, PAGE_SIZE).then((r) => r.data)
        : booksApi.list(page, PAGE_SIZE, category || undefined).then((r) => r.data),
  });

  const del = useMutation({
    mutationFn: (id: string) => booksApi.delete(id),
    onSuccess: () => {
      toast.success("Book deleted");
      qc.invalidateQueries({ queryKey: ["books"] });
      setDeleteId(null);
    },
    onError: (e) => toast.error(getErrorMessage(e, "Delete failed")),
  });

  const rows = useMemo(() => {
    let list = [...(q.data?.data ?? [])];

    if (category && debouncedSearch) {
      list = list.filter((b) => (b.category ?? "") === category);
    }

    if (availability === "available") {
      list = list.filter((b) => b.available_copies > 0);
    }
    if (availability === "low") {
      list = list.filter(
        (b) =>
          b.available_copies > 0 &&
          b.available_copies <= Math.max(1, Math.ceil(b.total_copies * 0.25)),
      );
    }
    if (availability === "unavailable") {
      list = list.filter((b) => b.available_copies <= 0);
    }

    if (sort === "title:asc") {
      list.sort((a, b) => a.title.localeCompare(b.title));
    }
    if (sort === "author:asc") {
      list.sort((a, b) => a.author.localeCompare(b.author));
    }
    if (sort === "available:asc") {
      list.sort((a, b) => a.available_copies - b.available_copies);
    }

    return list;
  }, [q.data, availability, sort, category, debouncedSearch]);

  return (
    <div>
      <PageHeader
        title="Books"
        description="Search, filter, and manage the complete library catalogue."
        action={
          <Button onClick={() => router.push("/books/add")}>
            <Plus size={16} />
            Add Book
          </Button>
        }
      />

      <div className="card mb-5 p-4">
        <div className="grid gap-3 lg:grid-cols-[1fr_180px_180px_180px]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3 text-slate-400" size={17} />
            <input
              className="input pl-10"
              placeholder="Search by title, author, ISBN…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              aria-label="Search books"
            />
          </div>
          <Select
            value={category}
            onChange={(e) => {
              setCategory(e.target.value);
              setPage(1);
            }}
            aria-label="Filter by category"
          >
            <option value="">All categories</option>
            {[
              "Fiction",
              "Non-Fiction",
              "Science",
              "Technology",
              "History",
              "Biography",
              "Children",
              "Mystery",
              "Romance",
              "Self-Help",
              "Other",
            ].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </Select>
          <Select
            value={availability}
            onChange={(e) => {
              setAvailability(e.target.value);
              setPage(1);
            }}
            aria-label="Filter by availability"
          >
            <option value="all">All availability</option>
            <option value="available">Available</option>
            <option value="low">Low Stock</option>
            <option value="unavailable">Unavailable</option>
          </Select>
          <Select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort books">
            <option value="created_at:desc">Newest first</option>
            <option value="title:asc">Title A-Z</option>
            <option value="author:asc">Author A-Z</option>
            <option value="available:asc">Lowest availability</option>
          </Select>
        </div>
      </div>

      <div className="card overflow-hidden">
        {q.isLoading ? (
          <LoadingSkeleton rows={7} />
        ) : q.isError ? (
          <ErrorState message={getErrorMessage(q.error, "Unable to load books")} />
        ) : !rows.length ? (
          <EmptyState
            title="No books found"
            message="Try a different search/filter or add a new catalogue item."
            action={<Button onClick={() => router.push("/books/add")}>Add Book</Button>}
          />
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
                    <th>Available / Total Copies</th>
                    <th>Shelf</th>
                    <th>Status</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((b: Book) => (
                    <tr key={b.id}>
                      <td>
                        <div className="max-w-[260px] truncate font-semibold text-slate-950 dark:text-white">{b.title}</div>
                        <div className="text-xs text-slate-400">{b.publisher ?? "—"}</div>
                      </td>
                      <td>{b.author}</td>
                      <td className="font-mono text-xs">{b.isbn}</td>
                      <td>{b.category ?? "—"}</td>
                      <td>
                        <span className="font-semibold text-slate-900 dark:text-white">{typeof b.available_copies === "number" ? b.available_copies : "—"}</span>
                        <span className="text-slate-400 dark:text-slate-400"> / {typeof b.total_copies === "number" ? b.total_copies : "—"}</span>
                      </td>
                      <td>{b.shelf_location ?? "—"}</td>
                      <td>
                        <BookAvailabilityBadge available={b.available_copies} total={b.total_copies} />
                      </td>
                      <td>
                        <div className="flex justify-end gap-1">
                          <button
                            className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white"
                            onClick={() => router.push(`/books/${b.id}`)}
                            title="View"
                            type="button"
                          >
                            <Eye size={16} />
                          </button>
                          <button
                            className="rounded-lg p-2 text-slate-500 hover:bg-blue-50 hover:text-blue-600 dark:text-slate-400 dark:hover:bg-blue-500/10 dark:hover:text-blue-300"
                            onClick={() => router.push(`/books/${b.id}/edit`)}
                            title="Edit"
                            type="button"
                          >
                            <Edit size={16} />
                          </button>
                          <button
                            className="rounded-lg p-2 text-slate-500 hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-500/10 dark:hover:text-red-300"
                            onClick={() => setDeleteId(b.id)}
                            title="Delete"
                            type="button"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination
              page={q.data!.pagination.page}
              totalPages={q.data!.pagination.total_pages}
              totalCount={q.data!.pagination.total_count}
              pageSize={q.data!.pagination.page_size}
              onPage={setPage}
            />
          </>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteId}
        title="Delete book"
        message="This will remove the book from the catalogue. Existing lending history may still reference this record."
        confirmLabel="Delete"
        loading={del.isPending}
        onConfirm={() => deleteId && del.mutate(deleteId)}
        onCancel={() => setDeleteId(null)}
      />
    </div>
  );
}
