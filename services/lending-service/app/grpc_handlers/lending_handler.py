"""
Lending Service gRPC handler.

Borrow Saga (correct order):
  1. Validate member  (read-only gRPC)
  2. Check book availability  (read-only gRPC)
  3. Decrease available copies via book-service  (book-service commit)
  4. Create lending record locally  (local DB commit)
  5. COMPENSATE: if step 4 fails → increase copies back (saga rollback)

Return Saga:
  1. Fetch lending record and validate (SELECT for idempotency)
  2. Mark returned + calculate fine  (local DB commit — point of no return)
  3. Increase available copies via book-service
  4. If step 3 fails → rollback step 2 by re-opening the record
     (prefer explicit rollback over silent inconsistency)
"""
from __future__ import annotations

import logging
import math
import os
from datetime import datetime

import grpc

from app.database import AsyncSessionLocal
from app.repositories.lending_repository import LendingRepository
from app.models.lending import LendingStatus
from app.proto_generated import lending_pb2, lending_pb2_grpc, common_pb2
from app.proto_generated import book_pb2, book_pb2_grpc, member_pb2, member_pb2_grpc

logger = logging.getLogger(__name__)

BOOK_SERVICE_HOST   = os.getenv("BOOK_SERVICE_HOST",   "localhost")
BOOK_SERVICE_PORT   = os.getenv("BOOK_SERVICE_PORT",   "50051")
MEMBER_SERVICE_HOST = os.getenv("MEMBER_SERVICE_HOST", "localhost")
MEMBER_SERVICE_PORT = os.getenv("MEMBER_SERVICE_PORT", "50052")


def _record_to_proto(
    record,
    book_title: str = "",
    book_isbn:  str = "",
    member_name:  str = "",
    member_email: str = "",
) -> lending_pb2.LendingRecord:
    status_map = {
        LendingStatus.BORROWED: lending_pb2.LendingStatus.BORROWED,
        LendingStatus.RETURNED: lending_pb2.LendingStatus.RETURNED,
        LendingStatus.OVERDUE:  lending_pb2.LendingStatus.OVERDUE,
    }
    return lending_pb2.LendingRecord(
        id=str(record.id),
        member_id=str(record.member_id),
        book_id=str(record.book_id),
        borrowed_at=record.borrowed_at.isoformat()  if record.borrowed_at  else "",
        due_date=record.due_date.isoformat()         if record.due_date     else "",
        returned_at=record.returned_at.isoformat()   if record.returned_at  else "",
        status=status_map.get(record.status, lending_pb2.LendingStatus.BORROWED),
        fine_amount=record.fine_amount or 0.0,
        created_at=record.created_at.isoformat()     if record.created_at   else "",
        updated_at=record.updated_at.isoformat()     if record.updated_at   else "",
        book_title=book_title,
        book_isbn=book_isbn,
        member_name=member_name,
        member_email=member_email,
    )


def _pagination(page: int, page_size: int, total: int) -> common_pb2.PaginationResponse:
    return common_pb2.PaginationResponse(
        page=page,
        page_size=page_size,
        total_count=total,
        total_pages=math.ceil(total / page_size) if page_size > 0 else 0,
    )


class LendingServiceHandler(lending_pb2_grpc.LendingServiceServicer):

    # ── BorrowBook ─────────────────────────────────────────────────────────

    async def BorrowBook(self, request, context):
        """
        Saga steps:
          1. Validate member (gRPC – read only)
          2. Check book availability (gRPC – read only)
          3. Decrease copies in book-service (gRPC – remote commit)
          4. Create lending record locally (local commit)
          5. If 4 fails → compensate by increasing copies (saga rollback)
        """
        try:
            # ── Step 1: validate member ───────────────────────────────────
            member_channel = grpc.aio.insecure_channel(
                f"{MEMBER_SERVICE_HOST}:{MEMBER_SERVICE_PORT}"
            )
            member_stub = member_pb2_grpc.MemberServiceStub(member_channel)
            member_resp = await member_stub.ValidateActiveMember(
                member_pb2.ValidateActiveMemberRequest(member_id=request.member_id),
                timeout=10,
            )
            if not member_resp.is_active:
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details(member_resp.message or "Member is not active")
                return lending_pb2.LendingRecord()

            # ── Step 2: check book availability ───────────────────────────
            book_channel = grpc.aio.insecure_channel(
                f"{BOOK_SERVICE_HOST}:{BOOK_SERVICE_PORT}"
            )
            book_stub = book_pb2_grpc.BookServiceStub(book_channel)
            avail_resp = await book_stub.CheckAvailability(
                book_pb2.CheckAvailabilityRequest(book_id=request.book_id),
                timeout=10,
            )
            if not avail_resp.available:
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details("No available copies of this book")
                return lending_pb2.LendingRecord()

            # ── Step 3: decrease copies (remote commit — point of no return) ──
            decrease_resp = await book_stub.DecreaseAvailableCopies(
                book_pb2.UpdateCopiesRequest(book_id=request.book_id, count=1),
                timeout=10,
            )
            if not decrease_resp.success:
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details("Failed to reserve book copy — no copies available")
                return lending_pb2.LendingRecord()

            # ── Step 4: create lending record (local commit) ───────────────
            try:
                async with AsyncSessionLocal() as session:
                    repo = LendingRepository(session)
                    record = await repo.create(
                        member_id=request.member_id,
                        book_id=request.book_id,
                        due_days=request.due_days or 14,
                    )
            except Exception as create_err:
                # ── Step 5: COMPENSATE — return the copy we just reserved ──
                logger.error(
                    "Lending record creation failed after copy decrease. "
                    "Compensating: increasing copies back. error=%s", create_err,
                )
                try:
                    await book_stub.IncreaseAvailableCopies(
                        book_pb2.UpdateCopiesRequest(book_id=request.book_id, count=1),
                        timeout=10,
                    )
                    logger.info("Saga compensation successful: copy restored for book=%s", request.book_id)
                except Exception as comp_err:
                    logger.critical(
                        "Saga compensation FAILED — manual reconciliation needed. "
                        "book_id=%s error=%s", request.book_id, comp_err,
                    )
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Borrow failed and was compensated. Please retry.")
                return lending_pb2.LendingRecord()

            logger.info(
                "BorrowBook success: record=%s member=%s book=%s",
                record.id, request.member_id, request.book_id,
            )
            return _record_to_proto(
                record,
                member_name=member_resp.member.full_name,
                member_email=member_resp.member.email,
            )

        except grpc.RpcError as e:
            logger.error("BorrowBook gRPC error: code=%s details=%s", e.code(), e.details())
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Upstream service error: {e.details()}")
            return lending_pb2.LendingRecord()
        except Exception as e:
            logger.exception("BorrowBook unexpected error")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return lending_pb2.LendingRecord()

    # ── ReturnBook ─────────────────────────────────────────────────────────

    async def ReturnBook(self, request, context):
        """
        Return saga:
          1. Mark lending record returned + calculate fine (local commit)
          2. Increase copies in book-service (remote)
          3. If step 2 fails → rollback step 1 (re-open the record)
        """
        try:
            async with AsyncSessionLocal() as session:
                repo = LendingRepository(session)
                record = await repo.get_by_id(request.lending_id)

                if not record:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Lending record {request.lending_id} not found")
                    return lending_pb2.ReturnBookResponse()

                if record.status == LendingStatus.RETURNED:
                    context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                    context.set_details("Book already returned")
                    return lending_pb2.ReturnBookResponse()

                # Step 1: mark returned locally
                returned_record = await repo.return_book(request.lending_id)
                book_id = str(returned_record.book_id)

            # Step 2: increase copies in book-service
            book_channel = grpc.aio.insecure_channel(
                f"{BOOK_SERVICE_HOST}:{BOOK_SERVICE_PORT}"
            )
            book_stub = book_pb2_grpc.BookServiceStub(book_channel)
            try:
                await book_stub.IncreaseAvailableCopies(
                    book_pb2.UpdateCopiesRequest(book_id=book_id, count=1),
                    timeout=10,
                )
            except Exception as inc_err:
                # Step 3: book-service call failed → rollback local return
                logger.error(
                    "IncreaseAvailableCopies failed after return commit. "
                    "Rolling back: re-opening lending record. error=%s", inc_err,
                )
                try:
                    async with AsyncSessionLocal() as rollback_session:
                        rollback_repo = LendingRepository(rollback_session)
                        rec = await rollback_repo.get_by_id(request.lending_id)
                        if rec:
                            rec.status      = LendingStatus.BORROWED
                            rec.returned_at = None
                            rec.fine_amount = 0.0
                            rec.updated_at  = datetime.utcnow()
                            await rollback_session.commit()
                            logger.info("Return rollback successful: record=%s", request.lending_id)
                except Exception as rb_err:
                    logger.critical(
                        "Return rollback FAILED — manual reconciliation needed. "
                        "lending_id=%s error=%s", request.lending_id, rb_err,
                    )
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Return failed and was rolled back. Please retry.")
                return lending_pb2.ReturnBookResponse()

            now = datetime.utcnow()
            is_overdue  = returned_record.fine_amount > 0
            overdue_days = max(0, (now - returned_record.due_date).days) if is_overdue else 0

            logger.info(
                "ReturnBook success: record=%s fine=%.2f overdue=%s",
                request.lending_id, returned_record.fine_amount, is_overdue,
            )
            return lending_pb2.ReturnBookResponse(
                record=_record_to_proto(returned_record),
                fine_amount=returned_record.fine_amount,
                is_overdue=is_overdue,
                overdue_days=overdue_days,
            )

        except Exception as e:
            logger.exception("ReturnBook unexpected error")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return lending_pb2.ReturnBookResponse()

    # ── List handlers ──────────────────────────────────────────────────────

    async def ListBorrowedBooks(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = LendingRepository(session)
                page      = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                records, total = await repo.list_borrowed_books(
                    page=page, page_size=page_size,
                    sort_by=request.sort_by or "borrowed_at",
                    sort_order=request.sort_order or "desc",
                )
                return lending_pb2.ListBorrowedBooksResponse(
                    records=[_record_to_proto(r) for r in records],
                    pagination=_pagination(page, page_size, total),
                )
        except Exception as e:
            logger.exception("ListBorrowedBooks error")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return lending_pb2.ListBorrowedBooksResponse()

    async def ListBorrowedBooksByMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = LendingRepository(session)
                page      = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                records, total = await repo.list_by_member(
                    member_id=request.member_id, page=page, page_size=page_size,
                )
                return lending_pb2.ListBorrowedBooksResponse(
                    records=[_record_to_proto(r) for r in records],
                    pagination=_pagination(page, page_size, total),
                )
        except Exception as e:
            logger.exception("ListBorrowedBooksByMember error")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return lending_pb2.ListBorrowedBooksResponse()

    async def ListBookBorrowHistory(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = LendingRepository(session)
                page      = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                records, total = await repo.list_by_book(
                    book_id=request.book_id, page=page, page_size=page_size,
                )
                return lending_pb2.ListBorrowedBooksResponse(
                    records=[_record_to_proto(r) for r in records],
                    pagination=_pagination(page, page_size, total),
                )
        except Exception as e:
            logger.exception("ListBookBorrowHistory error")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return lending_pb2.ListBorrowedBooksResponse()

    async def ListOverdueBooks(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = LendingRepository(session)
                page      = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                records, total = await repo.list_overdue(page=page, page_size=page_size)
                return lending_pb2.ListBorrowedBooksResponse(
                    records=[_record_to_proto(r) for r in records],
                    pagination=_pagination(page, page_size, total),
                )
        except Exception as e:
            logger.exception("ListOverdueBooks error")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return lending_pb2.ListBorrowedBooksResponse()
