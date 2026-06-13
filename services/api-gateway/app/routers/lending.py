"""Lending router for API Gateway."""
from __future__ import annotations

import logging
from typing import Optional

import grpc
from fastapi import APIRouter, HTTPException, Query, Request, status

from app.grpc_clients import GRPC_TIMEOUT, get_lending_channel
from app.grpc_clients.proto_generated import common_pb2, lending_pb2, lending_pb2_grpc
from app.schemas import BorrowRequest, LendingRecordResponse, PaginatedResponse, PaginationMeta, ReturnRequest, ReturnResponse
from app.telemetry.setup import make_grpc_metadata_with_trace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/lending", tags=["Lending"])

STATUS_TEXT = {0: "BORROWED", 1: "RETURNED", 2: "OVERDUE"}
STATUS_ENUM = {
    "BORROWED": lending_pb2.LendingStatus.BORROWED,
    "RETURNED": lending_pb2.LendingStatus.RETURNED,
    "OVERDUE": lending_pb2.LendingStatus.OVERDUE,
}
STATUS_MAP = {
    grpc.StatusCode.NOT_FOUND: (404, "Not Found"),
    grpc.StatusCode.ALREADY_EXISTS: (409, "Already Exists"),
    grpc.StatusCode.FAILED_PRECONDITION: (400, "Bad Request"),
    grpc.StatusCode.INVALID_ARGUMENT: (422, "Validation Error"),
    grpc.StatusCode.UNAVAILABLE: (503, "Service Unavailable"),
}


def grpc_metadata(request: Request) -> list[tuple[str, str]]:
    correlation_id = getattr(request.state, "correlation_id", "-")
    base = [("x-correlation-id", correlation_id)] if correlation_id and correlation_id != "-" else []
    return make_grpc_metadata_with_trace(base)


def grpc_error_to_http(e: grpc.RpcError):
    code, default_msg = STATUS_MAP.get(e.code(), (500, "Internal Server Error"))
    logger.error(
        "Downstream gRPC call failed",
        extra={
            "grpc_code": e.code().name if e.code() else "UNKNOWN",
            "grpc_details": e.details(),
            "http_status": code,
        },
    )
    raise HTTPException(status_code=code, detail=e.details() or default_msg)


def _proto_to_record(r) -> LendingRecordResponse:
    return LendingRecordResponse(
        id=r.id,
        member_id=r.member_id,
        book_id=r.book_id,
        borrowed_at=r.borrowed_at or None,
        due_date=r.due_date or None,
        returned_at=r.returned_at or None,
        status=STATUS_TEXT.get(r.status, "BORROWED"),
        fine_amount=r.fine_amount,
        book_title=r.book_title or None,
        book_isbn=r.book_isbn or None,
        member_name=r.member_name or None,
        member_email=r.member_email or None,
        created_at=r.created_at or None,
        updated_at=r.updated_at or None,
    )


def _pagination(page: int, page_size: int) -> common_pb2.PaginationRequest:
    return common_pb2.PaginationRequest(page=page, page_size=page_size)


def _page_response(resp) -> PaginatedResponse[LendingRecordResponse]:
    return PaginatedResponse(
        data=[_proto_to_record(r) for r in resp.records],
        pagination=PaginationMeta(
            page=resp.pagination.page,
            page_size=resp.pagination.page_size,
            total_count=resp.pagination.total_count,
            total_pages=resp.pagination.total_pages,
        ),
    )


@router.post("/borrow", response_model=LendingRecordResponse, status_code=status.HTTP_201_CREATED)
async def borrow_book(body: BorrowRequest, request: Request):
    try:
        stub = lending_pb2_grpc.LendingServiceStub(get_lending_channel())
        resp = await stub.BorrowBook(
            lending_pb2.BorrowBookRequest(member_id=body.member_id, book_id=body.book_id, due_days=body.due_days),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _proto_to_record(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.post("/return", response_model=ReturnResponse)
async def return_book(body: ReturnRequest, request: Request):
    try:
        stub = lending_pb2_grpc.LendingServiceStub(get_lending_channel())
        resp = await stub.ReturnBook(
            lending_pb2.ReturnBookRequest(lending_id=body.lending_id),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return ReturnResponse(
            record=_proto_to_record(resp.record),
            fine_amount=resp.fine_amount,
            is_overdue=resp.is_overdue,
            overdue_days=resp.overdue_days,
        )
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/borrowed", response_model=PaginatedResponse[LendingRecordResponse])
async def list_borrowed_books(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search lending id, book id or member id"),
    member_id: Optional[str] = None,
    book_id: Optional[str] = None,
    lending_status: Optional[str] = Query(None, pattern="^(BORROWED|RETURNED|OVERDUE)$"),
    due_from: Optional[str] = Query(None, description="Inclusive ISO date/datetime lower bound"),
    due_to: Optional[str] = Query(None, description="Inclusive ISO date/datetime upper bound"),
    sort_by: str = "borrowed_at",
    sort_order: str = "desc",
):
    try:
        stub = lending_pb2_grpc.LendingServiceStub(get_lending_channel())
        resp = await stub.ListBorrowedBooks(
            lending_pb2.ListBorrowedBooksRequest(
                pagination=_pagination(page, page_size),
                sort_by=sort_by,
                sort_order=sort_order,
                query=q or "",
                member_id=member_id or "",
                book_id=book_id or "",
                status=STATUS_ENUM.get(lending_status or "BORROWED", lending_pb2.LendingStatus.BORROWED),
                filter_by_status=lending_status is not None,
                due_from=due_from or "",
                due_to=due_to or "",
            ),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _page_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/member/{member_id}", response_model=PaginatedResponse[LendingRecordResponse])
async def list_borrowed_by_member(
    member_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        stub = lending_pb2_grpc.LendingServiceStub(get_lending_channel())
        resp = await stub.ListBorrowedBooksByMember(
            lending_pb2.ListBorrowedBooksByMemberRequest(
                member_id=member_id,
                pagination=_pagination(page, page_size),
            ),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _page_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/book/{book_id}/history", response_model=PaginatedResponse[LendingRecordResponse])
async def list_book_borrow_history(
    book_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        stub = lending_pb2_grpc.LendingServiceStub(get_lending_channel())
        resp = await stub.ListBookBorrowHistory(
            lending_pb2.ListBookBorrowHistoryRequest(
                book_id=book_id,
                pagination=_pagination(page, page_size),
            ),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _page_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/overdue", response_model=PaginatedResponse[LendingRecordResponse])
async def list_overdue_books(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search lending id, book id or member id"),
    member_id: Optional[str] = None,
    book_id: Optional[str] = None,
    due_from: Optional[str] = Query(None, description="Inclusive ISO date/datetime lower bound"),
    due_to: Optional[str] = Query(None, description="Inclusive ISO date/datetime upper bound"),
):
    try:
        stub = lending_pb2_grpc.LendingServiceStub(get_lending_channel())
        resp = await stub.ListOverdueBooks(
            lending_pb2.ListOverdueBooksRequest(
                pagination=_pagination(page, page_size),
                query=q or "",
                member_id=member_id or "",
                book_id=book_id or "",
                due_from=due_from or "",
                due_to=due_to or "",
            ),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _page_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)
