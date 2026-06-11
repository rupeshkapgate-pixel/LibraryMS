"use client";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { booksApi, lendingApi, membersApi } from "@/lib/api";
import { PageHeader, Spinner, EmptyState, Pagination } from "@/components/ui";
import { formatDate, formatCurrency, cn } from "@/lib/utils";
import type { Book, LendingRecord, Member } from "@/types";

const badge: Record<string, string> = {
  BORROWED: "badge-blue",
  RETURNED: "badge-green",
  OVERDUE:  "badge-red",
};

function shortId(id: string) {
  return `${id.slice(0, 8)}…`;
}

export default function BorrowedBooksPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ["lending", "borrowed", page],
    queryFn: () => lendingApi.listBorrowed(page, 20).then((r) => r.data),
  });

  const { data: booksData } = useQuery({
    queryKey: ["books", "lookup", 1, 500],
    queryFn: () => booksApi.list(1, 500).then((r) => r.data),
  });

  const { data: membersData } = useQuery({
    queryKey: ["members", "lookup", 1, 500],
    queryFn: () => membersApi.list(1, 500).then((r) => r.data),
  });

  const bookById = useMemo(() => {
    return new Map((booksData?.data ?? []).map((book: Book) => [book.id, book]));
  }, [booksData]);

  const memberById = useMemo(() => {
    return new Map((membersData?.data ?? []).map((member: Member) => [member.id, member]));
  }, [membersData]);

  function getBookLabel(record: LendingRecord) {
    const book = bookById.get(record.book_id);
    return record.book_title ?? book?.title ?? shortId(record.book_id);
  }

  function getMemberLabel(record: LendingRecord) {
    const member = memberById.get(record.member_id);
    return record.member_name ?? member?.full_name ?? shortId(record.member_id);
  }

  return (
    <div>
      <PageHeader title="Borrowed Books" description="All currently borrowed books" />
      <div className="card">
        {isLoading ? (
          <Spinner />
        ) : !data?.data?.length ? (
          <EmptyState message="No books currently borrowed." />
        ) : (
          <>
            <div className="table-container rounded-none border-0">
              <table>
                <thead>
                  <tr>
                    <th>Book</th>
                    <th>Member</th>
                    <th>Borrowed</th>
                    <th>Due Date</th>
                    <th>Status</th>
                    <th>Fine</th>
                  </tr>
                </thead>
                <tbody>
                  {data.data.map((record: LendingRecord) => (
                    <tr key={record.id}>
                      <td>
                        <div className="font-medium text-gray-900">{getBookLabel(record)}</div>
                        <div className="font-mono text-xs text-gray-400">{shortId(record.book_id)}</div>
                      </td>
                      <td>
                        <div className="font-medium text-gray-900">{getMemberLabel(record)}</div>
                        <div className="font-mono text-xs text-gray-400">{shortId(record.member_id)}</div>
                      </td>
                      <td>{formatDate(record.borrowed_at)}</td>
                      <td className={record.status === "OVERDUE" ? "text-red-600 font-semibold" : ""}>{formatDate(record.due_date)}</td>
                      <td><span className={cn("badge", badge[record.status] ?? "badge-gray")}>{record.status}</span></td>
                      <td>{record.fine_amount > 0 ? <span className="text-red-600 font-medium">{formatCurrency(record.fine_amount)}</span> : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination page={data.pagination.page} totalPages={data.pagination.total_pages} totalCount={data.pagination.total_count} pageSize={data.pagination.page_size} onPage={setPage} />
          </>
        )}
      </div>
    </div>
  );
}
