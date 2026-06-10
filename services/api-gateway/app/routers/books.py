"""Books router — REST ↔ gRPC with standardised error responses."""
from __future__ import annotations

import logging
from typing import Optional

import grpc
from fastapi import APIRouter, HTTPException, Query, status

from app.grpc_clients import get_book_channel, GRPC_TIMEOUT
from app.grpc_clients.proto_generated import book_pb2, book_pb2_grpc, common_pb2
from app.schemas import BookCreate, BookUpdate, BookResponse, PaginatedResponse, PaginationMeta

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/books", tags=["Books"])

# gRPC status → (HTTP status, error_code)
_GRPC_STATUS_MAP: dict[grpc.StatusCode, tuple[int, str]] = {
    grpc.StatusCode.NOT_FOUND:           (404, "NOT_FOUND"),
    grpc.StatusCode.ALREADY_EXISTS:      (409, "ALREADY_EXISTS"),
    grpc.StatusCode.FAILED_PRECONDITION: (409, "PRECONDITION_FAILED"),
    grpc.StatusCode.INVALID_ARGUMENT:    (422, "INVALID_ARGUMENT"),
    grpc.StatusCode.PERMISSION_DENIED:   (403, "PERMISSION_DENIED"),
    grpc.StatusCode.UNAUTHENTICATED:     (401, "UNAUTHENTICATED"),
    grpc.StatusCode.UNAVAILABLE:         (503, "SERVICE_UNAVAILABLE"),
    grpc.StatusCode.DEADLINE_EXCEEDED:   (504, "GATEWAY_TIMEOUT"),
    grpc.StatusCode.INTERNAL:            (500, "INTERNAL_ERROR"),
}


def grpc_error_to_http(e: grpc.RpcError) -> None:
    """Translate a gRPC RpcError into a FastAPI HTTPException with a standard body."""
    http_status, error_code = _GRPC_STATUS_MAP.get(e.code(), (500, "INTERNAL_ERROR"))
    raise HTTPException(
        status_code=http_status,
        detail={
            "error":   error_code,
            "message": e.details() or e.code().name,
            "details": {},
        },
    )


def _to_response(b) -> BookResponse:
    return BookResponse(
        id=b.id,
        title=b.title,
        author=b.author,
        isbn=b.isbn,
        publisher=b.publisher      or None,
        category=b.category        or None,
        description=b.description  or None,
        published_year=b.published_year or None,
        total_copies=b.total_copies,
        available_copies=b.available_copies,
        shelf_location=b.shelf_location or None,
        created_at=b.created_at    or None,
        updated_at=b.updated_at    or None,
    )


def _pag(p) -> PaginationMeta:
    return PaginationMeta(
        page=p.page, page_size=p.page_size,
        total_count=p.total_count, total_pages=p.total_pages,
    )


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED,
             summary="Add a book to the catalogue",
             responses={409: {"description": "ISBN already exists"}})
async def create_book(body: BookCreate):
    try:
        async with get_book_channel() as ch:
            resp = await book_pb2_grpc.BookServiceStub(ch).CreateBook(
                book_pb2.CreateBookRequest(
                    title=body.title, author=body.author, isbn=body.isbn,
                    publisher=body.publisher or "", category=body.category or "",
                    description=body.description or "",
                    published_year=body.published_year or 0,
                    total_copies=body.total_copies,
                    shelf_location=body.shelf_location or "",
                ),
                timeout=GRPC_TIMEOUT,
            )
        return _to_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("", response_model=PaginatedResponse[BookResponse], summary="List books")
async def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    try:
        async with get_book_channel() as ch:
            resp = await book_pb2_grpc.BookServiceStub(ch).ListBooks(
                book_pb2.ListBooksRequest(
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                    category=category or "", sort_by=sort_by, sort_order=sort_order,
                ),
                timeout=GRPC_TIMEOUT,
            )
        return PaginatedResponse(data=[_to_response(b) for b in resp.books], pagination=_pag(resp.pagination))
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/search", response_model=PaginatedResponse[BookResponse], summary="Search books")
async def search_books(
    q: str = Query(..., min_length=1),
    search_by: str = Query("all", pattern="^(title|author|category|isbn|all)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        async with get_book_channel() as ch:
            resp = await book_pb2_grpc.BookServiceStub(ch).SearchBooks(
                book_pb2.SearchBooksRequest(
                    query=q, search_by=search_by,
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                ),
                timeout=GRPC_TIMEOUT,
            )
        return PaginatedResponse(data=[_to_response(b) for b in resp.books], pagination=_pag(resp.pagination))
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/{book_id}", response_model=BookResponse, summary="Get book by ID")
async def get_book(book_id: str):
    try:
        async with get_book_channel() as ch:
            resp = await book_pb2_grpc.BookServiceStub(ch).GetBook(
                book_pb2.GetBookRequest(id=book_id), timeout=GRPC_TIMEOUT,
            )
        return _to_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.put("/{book_id}", response_model=BookResponse, summary="Update a book")
async def update_book(book_id: str, body: BookUpdate):
    try:
        async with get_book_channel() as ch:
            resp = await book_pb2_grpc.BookServiceStub(ch).UpdateBook(
                book_pb2.UpdateBookRequest(
                    id=book_id,
                    title=body.title or "", author=body.author or "",
                    isbn=body.isbn or "", publisher=body.publisher or "",
                    category=body.category or "", description=body.description or "",
                    published_year=body.published_year or 0,
                    total_copies=body.total_copies or 0,
                    shelf_location=body.shelf_location or "",
                ),
                timeout=GRPC_TIMEOUT,
            )
        return _to_response(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Soft-delete a book")
async def delete_book(book_id: str):
    try:
        async with get_book_channel() as ch:
            await book_pb2_grpc.BookServiceStub(ch).DeleteBook(
                book_pb2.DeleteBookRequest(id=book_id), timeout=GRPC_TIMEOUT,
            )
    except grpc.RpcError as e:
        grpc_error_to_http(e)
