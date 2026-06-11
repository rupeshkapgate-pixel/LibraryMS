"""gRPC handlers for Lending Service."""
import logging
import math
import os
from datetime import datetime

import grpc

from app.database import AsyncSessionLocal
from app.repositories.lending_repository import LendingRepository
from app.models.lending import LendingStatus
from app.observability.logging import get_grpc_correlation_id, log_event
from app.telemetry.setup import make_grpc_metadata_with_trace
from app.proto_generated import lending_pb2, lending_pb2_grpc, common_pb2
from app.proto_generated import book_pb2, book_pb2_grpc, member_pb2, member_pb2_grpc

logger = logging.getLogger(__name__)

_SERVICE = "lending-service"


def _log_error(operation: str, context, exc: Exception) -> None:
    log_event(
        logger,
        logging.ERROR,
        service=_SERVICE,
        operation=operation,
        correlation_id=get_grpc_correlation_id(context),
        message=f"{operation} failed",
        error=exc,
    )


def _log_info(operation: str, context, message: str, **extra) -> None:
    log_event(
        logger,
        logging.INFO,
        service=_SERVICE,
        operation=operation,
        correlation_id=get_grpc_correlation_id(context),
        message=message,
        **extra,
    )


def downstream_metadata(context) -> list[tuple[str, str]]:
    correlation_id = get_grpc_correlation_id(context)
    base = [("x-correlation-id", correlation_id)] if correlation_id and correlation_id != "-" else []
    return make_grpc_metadata_with_trace(base)


BOOK_SERVICE_HOST = os.getenv("BOOK_SERVICE_HOST", "localhost")
BOOK_SERVICE_PORT = os.getenv("BOOK_SERVICE_PORT", "50051")
MEMBER_SERVICE_HOST = os.getenv("MEMBER_SERVICE_HOST", "localhost")
MEMBER_SERVICE_PORT = os.getenv("MEMBER_SERVICE_PORT", "50052")


def _record_to_proto(record, book_title="", book_isbn="", member_name="", member_email="") -> lending_pb2.LendingRecord:
    status_map = {
        LendingStatus.BORROWED: lending_pb2.LendingStatus.BORROWED,
        LendingStatus.RETURNED: lending_pb2.LendingStatus.RETURNED,
        LendingStatus.OVERDUE: lending_pb2.LendingStatus.OVERDUE,
    }
    return lending_pb2.LendingRecord(
        id=str(record.id),
        member_id=str(record.member_id),
        book_id=str(record.book_id),
        borrowed_at=record.borrowed_at.isoformat() if record.borrowed_at else "",
        due_date=record.due_date.isoformat() if record.due_date else "",
        returned_at=record.returned_at.isoformat() if record.returned_at else "",
        status=status_map.get(record.status, lending_pb2.LendingStatus.BORROWED),
        fine_amount=record.fine_amount or 0.0,
        created_at=record.created_at.isoformat() if record.created_at else "",
        updated_at=record.updated_at.isoformat() if record.updated_at else "",
        book_title=book_title,
        book_isbn=book_isbn,
        member_name=member_name,
        member_email=member_email,
    )


def get_book_stub():
    channel = grpc.aio.insecure_channel(f"{BOOK_SERVICE_HOST}:{BOOK_SERVICE_PORT}")
    return book_pb2_grpc.BookServiceStub(channel)


def get_member_stub():
    channel = grpc.aio.insecure_channel(f"{MEMBER_SERVICE_HOST}:{MEMBER_SERVICE_PORT}")
    return member_pb2_grpc.MemberServiceStub(channel)


async def _safe_get_book_details(book_stub, book_id: str) -> tuple[str, str]:
    """Return (title, isbn) for display enrichment. Never fail lending list flows."""
    try:
        book = await book_stub.GetBook(book_pb2.GetBookRequest(id=book_id), timeout=10)
        return book.title or "", book.isbn or ""
    except grpc.RpcError as exc:
        logger.warning("Could not enrich book details for book_id=%s: %s", book_id, exc)
        return "", ""
    except Exception as exc:
        logger.warning("Unexpected book enrichment error for book_id=%s: %s", book_id, exc)
        return "", ""


async def _safe_get_member_details(member_stub, member_id: str) -> tuple[str, str]:
    """Return (full_name, email) for display enrichment. Never fail lending list flows."""
    try:
        member = await member_stub.GetMember(member_pb2.GetMemberRequest(id=member_id), timeout=10)
        return member.full_name or "", member.email or ""
    except grpc.RpcError as exc:
        logger.warning("Could not enrich member details for member_id=%s: %s", member_id, exc)
        return "", ""
    except Exception as exc:
        logger.warning("Unexpected member enrichment error for member_id=%s: %s", member_id, exc)
        return "", ""


async def _enrich_records(records) -> list[lending_pb2.LendingRecord]:
    """Convert records to protobuf and enrich with book/member display fields.

    Lending DB intentionally stores only foreign IDs. For UI-friendly list and
    return-dropdown screens, the lending service enriches the response by reading
    Book and Member services over gRPC. Failed enrichment falls back to IDs.
    """
    if not records:
        return []

    book_channel = grpc.aio.insecure_channel(f"{BOOK_SERVICE_HOST}:{BOOK_SERVICE_PORT}")
    member_channel = grpc.aio.insecure_channel(f"{MEMBER_SERVICE_HOST}:{MEMBER_SERVICE_PORT}")
    book_stub = book_pb2_grpc.BookServiceStub(book_channel)
    member_stub = member_pb2_grpc.MemberServiceStub(member_channel)

    book_cache: dict[str, tuple[str, str]] = {}
    member_cache: dict[str, tuple[str, str]] = {}
    enriched: list[lending_pb2.LendingRecord] = []

    try:
        for record in records:
            book_id = str(record.book_id)
            member_id = str(record.member_id)

            if book_id not in book_cache:
                book_cache[book_id] = await _safe_get_book_details(book_stub, book_id)
            if member_id not in member_cache:
                member_cache[member_id] = await _safe_get_member_details(member_stub, member_id)

            book_title, book_isbn = book_cache[book_id]
            member_name, member_email = member_cache[member_id]
            enriched.append(
                _record_to_proto(
                    record,
                    book_title=book_title,
                    book_isbn=book_isbn,
                    member_name=member_name,
                    member_email=member_email,
                )
            )
        return enriched
    finally:
        await book_channel.close()
        await member_channel.close()


class LendingServiceHandler(lending_pb2_grpc.LendingServiceServicer):

    async def BorrowBook(self, request, context):
        try:
            # 1. Validate member
            member_channel = grpc.aio.insecure_channel(f"{MEMBER_SERVICE_HOST}:{MEMBER_SERVICE_PORT}")
            member_stub = member_pb2_grpc.MemberServiceStub(member_channel)
            member_resp = await member_stub.ValidateActiveMember(
                member_pb2.ValidateActiveMemberRequest(member_id=request.member_id),
                timeout=10,
                metadata=downstream_metadata(context),
            )
            if not member_resp.is_active:
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details(member_resp.message or "Member is not active")
                return lending_pb2.LendingRecord()

            # 2. Validate book and check availability
            book_channel = grpc.aio.insecure_channel(f"{BOOK_SERVICE_HOST}:{BOOK_SERVICE_PORT}")
            book_stub = book_pb2_grpc.BookServiceStub(book_channel)
            avail_resp = await book_stub.CheckAvailability(
                book_pb2.CheckAvailabilityRequest(book_id=request.book_id),
                timeout=10,
                metadata=downstream_metadata(context),
            )
            if not avail_resp.available:
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details("No available copies of the book")
                return lending_pb2.LendingRecord()

            book_title, book_isbn = await _safe_get_book_details(book_stub, request.book_id)

            # 3. Create lending record
            async with AsyncSessionLocal() as session:
                repo = LendingRepository(session)
                record = await repo.create(
                    member_id=request.member_id,
                    book_id=request.book_id,
                    due_days=request.due_days or 14,
                )

                # 4. Decrease available copies
                decrease_resp = await book_stub.DecreaseAvailableCopies(
                    book_pb2.UpdateCopiesRequest(book_id=request.book_id, count=1),
                    timeout=10,
                    metadata=downstream_metadata(context),
                )
                if not decrease_resp.success:
                    # Rollback: delete the lending record
                    await session.delete(record)
                    await session.commit()
                    context.set_code(grpc.StatusCode.INTERNAL)
                    context.set_details("Failed to decrease available copies")
                    return lending_pb2.LendingRecord()

                _log_info("BorrowBook", context, "Book borrowed", member_id=request.member_id, book_id=request.book_id, lending_id=str(record.id))
                return _record_to_proto(
                    record,
                    book_title=book_title,
                    book_isbn=book_isbn,
                    member_name=member_resp.member.full_name,
                    member_email=member_resp.member.email,
                )
        except grpc.RpcError as exc:
            _log_error("BorrowBook", context, exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return lending_pb2.LendingRecord()
        except Exception as exc:
            _log_error("BorrowBook", context, exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return lending_pb2.LendingRecord()

    async def ReturnBook(self, request, context):
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

                returned_record = await repo.return_book(request.lending_id)
                book_id = str(returned_record.book_id)

                # Increase available copies
                book_channel = grpc.aio.insecure_channel(f"{BOOK_SERVICE_HOST}:{BOOK_SERVICE_PORT}")
                book_stub = book_pb2_grpc.BookServiceStub(book_channel)
                await book_stub.IncreaseAvailableCopies(
                    book_pb2.UpdateCopiesRequest(book_id=book_id, count=1),
                    timeout=10,
                    metadata=downstream_metadata(context),
                )

                now = datetime.utcnow()
                is_overdue = returned_record.fine_amount > 0
                overdue_days = 0
                if is_overdue and returned_record.due_date:
                    overdue_days = max(0, (now - returned_record.due_date).days)

                book_title, book_isbn = await _safe_get_book_details(book_stub, book_id)
                member_channel = grpc.aio.insecure_channel(f"{MEMBER_SERVICE_HOST}:{MEMBER_SERVICE_PORT}")
                member_stub = member_pb2_grpc.MemberServiceStub(member_channel)
                try:
                    member_name, member_email = await _safe_get_member_details(member_stub, str(returned_record.member_id))
                finally:
                    await member_channel.close()

                _log_info("ReturnBook", context, "Book returned", lending_id=request.lending_id, fine=returned_record.fine_amount)
                return lending_pb2.ReturnBookResponse(
                    record=_record_to_proto(
                        returned_record,
                        book_title=book_title,
                        book_isbn=book_isbn,
                        member_name=member_name,
                        member_email=member_email,
                    ),
                    fine_amount=returned_record.fine_amount,
                    is_overdue=is_overdue,
                    overdue_days=overdue_days,
                )
        except Exception as exc:
            _log_error("ReturnBook", context, exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return lending_pb2.ReturnBookResponse()

    async def ListBorrowedBooks(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = LendingRepository(session)
                page = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                records, total = await repo.list_borrowed_books(
                    page=page,
                    page_size=page_size,
                    sort_by=request.sort_by or "borrowed_at",
                    sort_order=request.sort_order or "desc",
                )
                total_pages = math.ceil(total / page_size) if page_size > 0 else 0
                return lending_pb2.ListBorrowedBooksResponse(
                    records=await _enrich_records(records),
                    pagination=common_pb2.PaginationResponse(
                        page=page,
                        page_size=page_size,
                        total_count=total,
                        total_pages=total_pages,
                    ),
                )
        except Exception as exc:
            _log_error("ListBorrowedBooks", context, exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return lending_pb2.ListBorrowedBooksResponse()

    async def ListBorrowedBooksByMember(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = LendingRepository(session)
                page = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                records, total = await repo.list_by_member(
                    member_id=request.member_id,
                    page=page,
                    page_size=page_size,
                )
                total_pages = math.ceil(total / page_size) if page_size > 0 else 0
                return lending_pb2.ListBorrowedBooksResponse(
                    records=await _enrich_records(records),
                    pagination=common_pb2.PaginationResponse(
                        page=page,
                        page_size=page_size,
                        total_count=total,
                        total_pages=total_pages,
                    ),
                )
        except Exception as exc:
            _log_error("ListBorrowedBooksByMember", context, exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return lending_pb2.ListBorrowedBooksResponse()

    async def ListBookBorrowHistory(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = LendingRepository(session)
                page = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                records, total = await repo.list_by_book(
                    book_id=request.book_id,
                    page=page,
                    page_size=page_size,
                )
                total_pages = math.ceil(total / page_size) if page_size > 0 else 0
                return lending_pb2.ListBorrowedBooksResponse(
                    records=await _enrich_records(records),
                    pagination=common_pb2.PaginationResponse(
                        page=page,
                        page_size=page_size,
                        total_count=total,
                        total_pages=total_pages,
                    ),
                )
        except Exception as exc:
            _log_error("ListBookBorrowHistory", context, exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return lending_pb2.ListBorrowedBooksResponse()

    async def ListOverdueBooks(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = LendingRepository(session)
                page = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                records, total = await repo.list_overdue(page=page, page_size=page_size)
                total_pages = math.ceil(total / page_size) if page_size > 0 else 0
                return lending_pb2.ListBorrowedBooksResponse(
                    records=await _enrich_records(records),
                    pagination=common_pb2.PaginationResponse(
                        page=page,
                        page_size=page_size,
                        total_count=total,
                        total_pages=total_pages,
                    ),
                )
        except Exception as exc:
            _log_error("ListOverdueBooks", context, exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return lending_pb2.ListBorrowedBooksResponse()
