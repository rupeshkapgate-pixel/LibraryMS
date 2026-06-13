"""Books router for API Gateway."""
from __future__ import annotations

import logging
from typing import Optional

import grpc
from fastapi import APIRouter, HTTPException, Query, Request, status

from app.grpc_clients import GRPC_TIMEOUT, get_book_channel
from app.grpc_clients.proto_generated import book_pb2, book_pb2_grpc, common_pb2
from app.schemas import BookCreate, BookResponse, BookUpdate, PaginatedResponse, PaginationMeta
from app.telemetry.setup import make_grpc_metadata_with_trace

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/books", tags=["Books"])

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


def _proto_to_book(b) -> BookResponse:
    return BookResponse(
        id=b.id,
        title=b.title,
        author=b.author,
        isbn=b.isbn,
        publisher=b.publisher or None,
        category=b.category or None,
        description=b.description or None,
        published_year=b.published_year or None,
        total_copies=b.total_copies,
        available_copies=b.available_copies,
        shelf_location=b.shelf_location or None,
        created_at=b.created_at or None,
        updated_at=b.updated_at or None,
    )


def _pagination(page: int, page_size: int) -> common_pb2.PaginationRequest:
    return common_pb2.PaginationRequest(page=page, page_size=page_size)


def _page_response(resp) -> PaginatedResponse[BookResponse]:
    return PaginatedResponse(
        data=[_proto_to_book(b) for b in resp.books],
        pagination=PaginationMeta(
            page=resp.pagination.page,
            page_size=resp.pagination.page_size,
            total_count=resp.pagination.total_count,
            total_pages=resp.pagination.total_pages,
        ),
    )


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(body: BookCreate, request: Request):
    try:
        stub = book_pb2_grpc.BookServiceStub(get_book_channel())
        resp = await stub.CreateBook(
            book_pb2.CreateBookRequest(
                title=body.title,
                author=body.author,
                isbn=body.isbn,
                publisher=body.publisher or "",
                category=body.category or "",
                description=body.description or "",
                published_year=body.published_year or 0,
                total_copies=body.total_copies,
                shelf_location=body.shelf_location or "",
            ),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _proto_to_book(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("", response_model=PaginatedResponse[BookResponse])
async def list_books(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: Optional[str] = Query(None, description="Search title, author, ISBN, category, publisher or shelf location"),
    search_by: str = Query("all", pattern="^(title|author|category|isbn|publisher|shelf_location|all)$"),
    category: Optional[str] = None,
    author: Optional[str] = None,
    publisher: Optional[str] = None,
    available_only: bool = False,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    try:
        stub = book_pb2_grpc.BookServiceStub(get_book_channel())
        resp = await stub.ListBooks(
            book_pb2.ListBooksRequest(
                pagination=_pagination(page, page_size),
                category=category or "",
                sort_by=sort_by,
                sort_order=sort_order,
                query=q or "",
                search_by=search_by,
                author=author or "",
                publisher=publisher or "",
                available_only=available_only,
            ),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _page_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/search", response_model=PaginatedResponse[BookResponse])
async def search_books(
    request: Request,
    q: str = Query(..., min_length=1),
    search_by: str = Query("all", pattern="^(title|author|category|isbn|publisher|shelf_location|all)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        stub = book_pb2_grpc.BookServiceStub(get_book_channel())
        resp = await stub.SearchBooks(
            book_pb2.SearchBooksRequest(
                query=q,
                search_by=search_by,
                pagination=_pagination(page, page_size),
            ),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _page_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: str, request: Request):
    try:
        stub = book_pb2_grpc.BookServiceStub(get_book_channel())
        resp = await stub.GetBook(
            book_pb2.GetBookRequest(id=book_id),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _proto_to_book(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(book_id: str, body: BookUpdate, request: Request):
    try:
        stub = book_pb2_grpc.BookServiceStub(get_book_channel())
        resp = await stub.UpdateBook(
            book_pb2.UpdateBookRequest(
                id=book_id,
                title=body.title or "",
                author=body.author or "",
                isbn=body.isbn or "",
                publisher=body.publisher or "",
                category=body.category or "",
                description=body.description or "",
                published_year=body.published_year or 0,
                total_copies=body.total_copies or 0,
                shelf_location=body.shelf_location or "",
            ),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
        return _proto_to_book(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: str, request: Request):
    try:
        stub = book_pb2_grpc.BookServiceStub(get_book_channel())
        await stub.DeleteBook(
            book_pb2.DeleteBookRequest(id=book_id),
            timeout=GRPC_TIMEOUT,
            metadata=grpc_metadata(request),
        )
    except grpc.RpcError as e:
        grpc_error_to_http(e)
