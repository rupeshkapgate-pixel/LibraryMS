"""Lending router for API Gateway."""
import logging

import grpc
from fastapi import APIRouter, HTTPException, Query, status

from app.grpc_clients import get_lending_channel, GRPC_TIMEOUT
from app.schemas import (
    BorrowRequest, ReturnRequest, LendingRecordResponse,
    ReturnResponse, PaginatedResponse, PaginationMeta,
)
from app.grpc_clients.proto_generated import lending_pb2, lending_pb2_grpc, common_pb2

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/lending", tags=["Lending"])

STATUS_TEXT = {0: "BORROWED", 1: "RETURNED", 2: "OVERDUE"}

STATUS_MAP = {
    grpc.StatusCode.NOT_FOUND: (404, "Not Found"),
    grpc.StatusCode.ALREADY_EXISTS: (409, "Already Exists"),
    grpc.StatusCode.FAILED_PRECONDITION: (400, "Bad Request"),
}


def grpc_error_to_http(e: grpc.RpcError):
    code, default_msg = STATUS_MAP.get(e.code(), (500, "Internal Server Error"))
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


@router.post("/borrow", response_model=LendingRecordResponse, status_code=status.HTTP_201_CREATED)
async def borrow_book(body: BorrowRequest):
    try:
        async with get_lending_channel() as channel:
            stub = lending_pb2_grpc.LendingServiceStub(channel)
            resp = await stub.BorrowBook(
                lending_pb2.BorrowBookRequest(
                    member_id=body.member_id,
                    book_id=body.book_id,
                    due_days=body.due_days,
                ),
                timeout=GRPC_TIMEOUT,
            )
            return _proto_to_record(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.post("/return", response_model=ReturnResponse)
async def return_book(body: ReturnRequest):
    try:
        async with get_lending_channel() as channel:
            stub = lending_pb2_grpc.LendingServiceStub(channel)
            resp = await stub.ReturnBook(
                lending_pb2.ReturnBookRequest(lending_id=body.lending_id),
                timeout=GRPC_TIMEOUT,
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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "borrowed_at",
    sort_order: str = "desc",
):
    try:
        async with get_lending_channel() as channel:
            stub = lending_pb2_grpc.LendingServiceStub(channel)
            resp = await stub.ListBorrowedBooks(
                lending_pb2.ListBorrowedBooksRequest(
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                    sort_by=sort_by,
                    sort_order=sort_order,
                ),
                timeout=GRPC_TIMEOUT,
            )
            return PaginatedResponse(
                data=[_proto_to_record(r) for r in resp.records],
                pagination=PaginationMeta(
                    page=resp.pagination.page,
                    page_size=resp.pagination.page_size,
                    total_count=resp.pagination.total_count,
                    total_pages=resp.pagination.total_pages,
                ),
            )
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/member/{member_id}", response_model=PaginatedResponse[LendingRecordResponse])
async def list_borrowed_by_member(
    member_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        async with get_lending_channel() as channel:
            stub = lending_pb2_grpc.LendingServiceStub(channel)
            resp = await stub.ListBorrowedBooksByMember(
                lending_pb2.ListBorrowedBooksByMemberRequest(
                    member_id=member_id,
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                ),
                timeout=GRPC_TIMEOUT,
            )
            return PaginatedResponse(
                data=[_proto_to_record(r) for r in resp.records],
                pagination=PaginationMeta(
                    page=resp.pagination.page,
                    page_size=resp.pagination.page_size,
                    total_count=resp.pagination.total_count,
                    total_pages=resp.pagination.total_pages,
                ),
            )
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/book/{book_id}/history", response_model=PaginatedResponse[LendingRecordResponse])
async def list_book_borrow_history(
    book_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        async with get_lending_channel() as channel:
            stub = lending_pb2_grpc.LendingServiceStub(channel)
            resp = await stub.ListBookBorrowHistory(
                lending_pb2.ListBookBorrowHistoryRequest(
                    book_id=book_id,
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                ),
                timeout=GRPC_TIMEOUT,
            )
            return PaginatedResponse(
                data=[_proto_to_record(r) for r in resp.records],
                pagination=PaginationMeta(
                    page=resp.pagination.page,
                    page_size=resp.pagination.page_size,
                    total_count=resp.pagination.total_count,
                    total_pages=resp.pagination.total_pages,
                ),
            )
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/overdue", response_model=PaginatedResponse[LendingRecordResponse])
async def list_overdue_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        async with get_lending_channel() as channel:
            stub = lending_pb2_grpc.LendingServiceStub(channel)
            resp = await stub.ListOverdueBooks(
                lending_pb2.ListOverdueBooksRequest(
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                ),
                timeout=GRPC_TIMEOUT,
            )
            return PaginatedResponse(
                data=[_proto_to_record(r) for r in resp.records],
                pagination=PaginationMeta(
                    page=resp.pagination.page,
                    page_size=resp.pagination.page_size,
                    total_count=resp.pagination.total_count,
                    total_pages=resp.pagination.total_pages,
                ),
            )
    except grpc.RpcError as e:
        grpc_error_to_http(e)
