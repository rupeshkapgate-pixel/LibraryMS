"""gRPC handlers for Lending Service.

Handlers are thin protobuf/gRPC adapters. Borrow, return, locking and cross-service
orchestration live in LendingService.
"""
from __future__ import annotations

import logging
import math

import grpc
from sqlalchemy.exc import IntegrityError

from app.database import AsyncSessionLocal
from app.grpc_clients import get_book_stub, get_member_stub
from app.models.lending import LendingRecord, LendingStatus
from app.observability.logging import get_grpc_correlation_id, log_event
from app.proto_generated import book_pb2, common_pb2, lending_pb2, lending_pb2_grpc, member_pb2
from app.services.lending_service import LendingService
from app.telemetry.setup import make_grpc_metadata_with_trace

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


def _record_to_proto(
    record: LendingRecord,
    book_title: str = "",
    book_isbn: str = "",
    member_name: str = "",
    member_email: str = "",
) -> lending_pb2.LendingRecord:
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


async def _safe_get_book_details(book_stub, book_id: str, metadata=None) -> tuple[str, str]:
    """Return (title, isbn) for display enrichment. Never fail list flows."""
    try:
        book = await book_stub.GetBook(book_pb2.GetBookRequest(id=book_id), timeout=10, metadata=metadata)
        return book.title or "", book.isbn or ""
    except grpc.RpcError as exc:
        logger.warning("Could not enrich book details for book_id=%s: %s", book_id, exc)
        return "", ""
    except Exception as exc:
        logger.warning("Unexpected book enrichment error for book_id=%s: %s", book_id, exc)
        return "", ""


async def _safe_get_member_details(member_stub, member_id: str, metadata=None) -> tuple[str, str]:
    """Return (full_name, email) for display enrichment. Never fail list flows."""
    try:
        member = await member_stub.GetMember(member_pb2.GetMemberRequest(id=member_id), timeout=10, metadata=metadata)
        return member.full_name or "", member.email or ""
    except grpc.RpcError as exc:
        logger.warning("Could not enrich member details for member_id=%s: %s", member_id, exc)
        return "", ""
    except Exception as exc:
        logger.warning("Unexpected member enrichment error for member_id=%s: %s", member_id, exc)
        return "", ""


async def _enrich_records(records, metadata=None) -> list[lending_pb2.LendingRecord]:
    """Convert records to protobuf and enrich with book/member display fields."""
    if not records:
        return []

    book_stub = get_book_stub()
    member_stub = get_member_stub()
    book_cache: dict[str, tuple[str, str]] = {}
    member_cache: dict[str, tuple[str, str]] = {}
    enriched: list[lending_pb2.LendingRecord] = []

    for record in records:
        book_id = str(record.book_id)
        member_id = str(record.member_id)

        if book_id not in book_cache:
            book_cache[book_id] = await _safe_get_book_details(book_stub, book_id, metadata=metadata)
        if member_id not in member_cache:
            member_cache[member_id] = await _safe_get_member_details(member_stub, member_id, metadata=metadata)

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


def _grpc_status_for(exc: Exception):
    if isinstance(exc, LookupError):
        return grpc.StatusCode.NOT_FOUND
    if isinstance(exc, PermissionError):
        return grpc.StatusCode.FAILED_PRECONDITION
    if isinstance(exc, IntegrityError):
        return grpc.StatusCode.ALREADY_EXISTS
    if isinstance(exc, ValueError):
        message = str(exc).lower()
        if "already returned" in message or "no available" in message:
            return grpc.StatusCode.FAILED_PRECONDITION
        return grpc.StatusCode.INVALID_ARGUMENT
    return grpc.StatusCode.INTERNAL


def _set_error(context, exc: Exception) -> None:
    context.set_code(_grpc_status_for(exc))
    context.set_details(str(exc))


def _status_from_request(request) -> LendingStatus | None:
    if not getattr(request, "filter_by_status", False):
        return None
    if request.status == lending_pb2.LendingStatus.RETURNED:
        return LendingStatus.RETURNED
    if request.status == lending_pb2.LendingStatus.OVERDUE:
        return LendingStatus.OVERDUE
    return LendingStatus.BORROWED


class LendingServiceHandler(lending_pb2_grpc.LendingServiceServicer):
    async def BorrowBook(self, request, context):
        try:
            metadata = downstream_metadata(context)
            async with AsyncSessionLocal() as session:
                service = LendingService(session)
                record = await service.borrow_book(
                    member_id=request.member_id,
                    book_id=request.book_id,
                    due_days=request.due_days or 14,
                )
                book_title, book_isbn = await _safe_get_book_details(get_book_stub(), str(record.book_id), metadata=metadata)
                member_name, member_email = await _safe_get_member_details(
                    get_member_stub(),
                    str(record.member_id),
                    metadata=metadata,
                )
                _log_info(
                    "BorrowBook",
                    context,
                    "Book borrowed",
                    member_id=request.member_id,
                    book_id=request.book_id,
                    lending_id=str(record.id),
                )
                return _record_to_proto(
                    record,
                    book_title=book_title,
                    book_isbn=book_isbn,
                    member_name=member_name,
                    member_email=member_email,
                )
        except Exception as exc:
            _log_error("BorrowBook", context, exc)
            _set_error(context, exc)
            return lending_pb2.LendingRecord()

    async def ReturnBook(self, request, context):
        try:
            metadata = downstream_metadata(context)
            async with AsyncSessionLocal() as session:
                service = LendingService(session)
                returned_record, fine_amount, is_overdue, overdue_days = await service.return_book(request.lending_id)
                book_title, book_isbn = await _safe_get_book_details(
                    get_book_stub(),
                    str(returned_record.book_id),
                    metadata=metadata,
                )
                member_name, member_email = await _safe_get_member_details(
                    get_member_stub(),
                    str(returned_record.member_id),
                    metadata=metadata,
                )
                _log_info("ReturnBook", context, "Book returned", lending_id=request.lending_id, fine=fine_amount)
                return lending_pb2.ReturnBookResponse(
                    record=_record_to_proto(
                        returned_record,
                        book_title=book_title,
                        book_isbn=book_isbn,
                        member_name=member_name,
                        member_email=member_email,
                    ),
                    fine_amount=fine_amount,
                    is_overdue=is_overdue,
                    overdue_days=overdue_days,
                )
        except Exception as exc:
            _log_error("ReturnBook", context, exc)
            _set_error(context, exc)
            return lending_pb2.ReturnBookResponse()

    async def ListBorrowedBooks(self, request, context):
        try:
            page = request.pagination.page or 1
            page_size = request.pagination.page_size or 20
            async with AsyncSessionLocal() as session:
                service = LendingService(session)
                records, total = await service.list_borrowed(
                    page=page,
                    page_size=page_size,
                    sort_by=request.sort_by or "borrowed_at",
                    sort_order=request.sort_order or "desc",
                    query=request.query or None,
                    member_id=request.member_id or None,
                    book_id=request.book_id or None,
                    status=_status_from_request(request),
                    due_from=request.due_from or None,
                    due_to=request.due_to or None,
                )
                total_pages = math.ceil(total / page_size) if page_size > 0 else 0
                return lending_pb2.ListBorrowedBooksResponse(
                    records=await _enrich_records(records, metadata=downstream_metadata(context)),
                    pagination=common_pb2.PaginationResponse(
                        page=page,
                        page_size=page_size,
                        total_count=total,
                        total_pages=total_pages,
                    ),
                )
        except Exception as exc:
            _log_error("ListBorrowedBooks", context, exc)
            _set_error(context, exc)
            return lending_pb2.ListBorrowedBooksResponse()

    async def ListBorrowedBooksByMember(self, request, context):
        try:
            page = request.pagination.page or 1
            page_size = request.pagination.page_size or 20
            async with AsyncSessionLocal() as session:
                service = LendingService(session)
                records, total = await service.list_by_member(member_id=request.member_id, page=page, page_size=page_size)
                total_pages = math.ceil(total / page_size) if page_size > 0 else 0
                return lending_pb2.ListBorrowedBooksResponse(
                    records=await _enrich_records(records, metadata=downstream_metadata(context)),
                    pagination=common_pb2.PaginationResponse(
                        page=page,
                        page_size=page_size,
                        total_count=total,
                        total_pages=total_pages,
                    ),
                )
        except Exception as exc:
            _log_error("ListBorrowedBooksByMember", context, exc)
            _set_error(context, exc)
            return lending_pb2.ListBorrowedBooksResponse()

    async def ListBookBorrowHistory(self, request, context):
        try:
            page = request.pagination.page or 1
            page_size = request.pagination.page_size or 20
            async with AsyncSessionLocal() as session:
                service = LendingService(session)
                records, total = await service.list_by_book(book_id=request.book_id, page=page, page_size=page_size)
                total_pages = math.ceil(total / page_size) if page_size > 0 else 0
                return lending_pb2.ListBorrowedBooksResponse(
                    records=await _enrich_records(records, metadata=downstream_metadata(context)),
                    pagination=common_pb2.PaginationResponse(
                        page=page,
                        page_size=page_size,
                        total_count=total,
                        total_pages=total_pages,
                    ),
                )
        except Exception as exc:
            _log_error("ListBookBorrowHistory", context, exc)
            _set_error(context, exc)
            return lending_pb2.ListBorrowedBooksResponse()

    async def ListOverdueBooks(self, request, context):
        try:
            page = request.pagination.page or 1
            page_size = request.pagination.page_size or 20
            async with AsyncSessionLocal() as session:
                service = LendingService(session)
                records, total = await service.list_overdue(
                    page=page,
                    page_size=page_size,
                    query=request.query or None,
                    member_id=request.member_id or None,
                    book_id=request.book_id or None,
                    due_from=request.due_from or None,
                    due_to=request.due_to or None,
                )
                total_pages = math.ceil(total / page_size) if page_size > 0 else 0
                return lending_pb2.ListBorrowedBooksResponse(
                    records=await _enrich_records(records, metadata=downstream_metadata(context)),
                    pagination=common_pb2.PaginationResponse(
                        page=page,
                        page_size=page_size,
                        total_count=total,
                        total_pages=total_pages,
                    ),
                )
        except Exception as exc:
            _log_error("ListOverdueBooks", context, exc)
            _set_error(context, exc)
            return lending_pb2.ListBorrowedBooksResponse()
