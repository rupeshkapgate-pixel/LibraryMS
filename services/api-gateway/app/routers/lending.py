"""Lending router — REST ↔ gRPC with standardised error responses."""
from __future__ import annotations
import logging
import grpc
from fastapi import APIRouter, HTTPException, Query, status
from app.grpc_clients import get_lending_channel, GRPC_TIMEOUT
from app.grpc_clients.proto_generated import lending_pb2, lending_pb2_grpc, common_pb2
from app.schemas import (
    BorrowRequest, ReturnRequest, LendingRecordResponse,
    ReturnResponse, PaginatedResponse, PaginationMeta,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/lending", tags=["Lending"])

_GRPC_STATUS_MAP = {
    grpc.StatusCode.NOT_FOUND:           (404, "NOT_FOUND"),
    grpc.StatusCode.ALREADY_EXISTS:      (409, "ALREADY_EXISTS"),
    grpc.StatusCode.FAILED_PRECONDITION: (409, "PRECONDITION_FAILED"),
    grpc.StatusCode.UNAVAILABLE:         (503, "SERVICE_UNAVAILABLE"),
    grpc.StatusCode.INTERNAL:            (500, "INTERNAL_ERROR"),
}
_STATUS_TEXT = {0: "BORROWED", 1: "RETURNED", 2: "OVERDUE"}


def grpc_error_to_http(e: grpc.RpcError) -> None:
    http_status, error_code = _GRPC_STATUS_MAP.get(e.code(), (500, "INTERNAL_ERROR"))
    raise HTTPException(
        status_code=http_status,
        detail={"error": error_code, "message": e.details() or e.code().name, "details": {}},
    )


def _to_record(r) -> LendingRecordResponse:
    return LendingRecordResponse(
        id=r.id, member_id=r.member_id, book_id=r.book_id,
        borrowed_at=r.borrowed_at or None, due_date=r.due_date or None,
        returned_at=r.returned_at or None,
        status=_STATUS_TEXT.get(r.status, "BORROWED"),
        fine_amount=r.fine_amount,
        book_title=r.book_title or None, book_isbn=r.book_isbn or None,
        member_name=r.member_name or None, member_email=r.member_email or None,
        created_at=r.created_at or None, updated_at=r.updated_at or None,
    )

def _pag(p) -> PaginationMeta:
    return PaginationMeta(page=p.page, page_size=p.page_size, total_count=p.total_count, total_pages=p.total_pages)


@router.post("/borrow", response_model=LendingRecordResponse, status_code=status.HTTP_201_CREATED,
             summary="Borrow a book",
             responses={409: {"description": "Member inactive or no copies available"}})
async def borrow_book(body: BorrowRequest):
    try:
        async with get_lending_channel() as ch:
            resp = await lending_pb2_grpc.LendingServiceStub(ch).BorrowBook(
                lending_pb2.BorrowBookRequest(
                    member_id=body.member_id, book_id=body.book_id, due_days=body.due_days,
                ),
                timeout=GRPC_TIMEOUT,
            )
        return _to_record(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.post("/return", response_model=ReturnResponse,
             summary="Return a borrowed book",
             responses={409: {"description": "Already returned"}})
async def return_book(body: ReturnRequest):
    try:
        async with get_lending_channel() as ch:
            resp = await lending_pb2_grpc.LendingServiceStub(ch).ReturnBook(
                lending_pb2.ReturnBookRequest(lending_id=body.lending_id),
                timeout=GRPC_TIMEOUT,
            )
        return ReturnResponse(
            record=_to_record(resp.record),
            fine_amount=resp.fine_amount,
            is_overdue=resp.is_overdue,
            overdue_days=resp.overdue_days,
        )
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/borrowed", response_model=PaginatedResponse[LendingRecordResponse],
            summary="Currently borrowed books")
async def list_borrowed_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = "borrowed_at",
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    try:
        async with get_lending_channel() as ch:
            resp = await lending_pb2_grpc.LendingServiceStub(ch).ListBorrowedBooks(
                lending_pb2.ListBorrowedBooksRequest(
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                    sort_by=sort_by, sort_order=sort_order,
                ),
                timeout=GRPC_TIMEOUT,
            )
        return PaginatedResponse(data=[_to_record(r) for r in resp.records], pagination=_pag(resp.pagination))
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/member/{member_id}", response_model=PaginatedResponse[LendingRecordResponse],
            summary="Borrowing history for a member")
async def list_borrowed_by_member(member_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    try:
        async with get_lending_channel() as ch:
            resp = await lending_pb2_grpc.LendingServiceStub(ch).ListBorrowedBooksByMember(
                lending_pb2.ListBorrowedBooksByMemberRequest(
                    member_id=member_id,
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                ),
                timeout=GRPC_TIMEOUT,
            )
        return PaginatedResponse(data=[_to_record(r) for r in resp.records], pagination=_pag(resp.pagination))
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/book/{book_id}/history", response_model=PaginatedResponse[LendingRecordResponse],
            summary="Borrow history for a book")
async def list_book_borrow_history(book_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    try:
        async with get_lending_channel() as ch:
            resp = await lending_pb2_grpc.LendingServiceStub(ch).ListBookBorrowHistory(
                lending_pb2.ListBookBorrowHistoryRequest(
                    book_id=book_id,
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                ),
                timeout=GRPC_TIMEOUT,
            )
        return PaginatedResponse(data=[_to_record(r) for r in resp.records], pagination=_pag(resp.pagination))
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/overdue", response_model=PaginatedResponse[LendingRecordResponse],
            summary="All overdue records")
async def list_overdue_books(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    try:
        async with get_lending_channel() as ch:
            resp = await lending_pb2_grpc.LendingServiceStub(ch).ListOverdueBooks(
                lending_pb2.ListOverdueBooksRequest(
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                ),
                timeout=GRPC_TIMEOUT,
            )
        return PaginatedResponse(data=[_to_record(r) for r in resp.records], pagination=_pag(resp.pagination))
    except grpc.RpcError as e:
        grpc_error_to_http(e)
