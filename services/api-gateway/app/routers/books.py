"""Books router for API Gateway."""
import logging
from typing import Optional

import grpc
from fastapi import APIRouter, HTTPException, Query, status

from app.grpc_clients import get_book_channel, GRPC_TIMEOUT
from app.schemas import BookCreate, BookUpdate, BookResponse, PaginatedResponse, PaginationMeta
from app.grpc_clients.proto_generated import book_pb2, book_pb2_grpc, common_pb2

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/books", tags=["Books"])

STATUS_MAP = {
    grpc.StatusCode.NOT_FOUND: (404, "Not Found"),
    grpc.StatusCode.ALREADY_EXISTS: (409, "Already Exists"),
    grpc.StatusCode.FAILED_PRECONDITION: (400, "Bad Request"),
    grpc.StatusCode.INVALID_ARGUMENT: (422, "Validation Error"),
}


def grpc_error_to_http(e: grpc.RpcError):
    code, default_msg = STATUS_MAP.get(e.code(), (500, "Internal Server Error"))
    detail = e.details() or default_msg
    raise HTTPException(status_code=code, detail=detail)


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


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(body: BookCreate):
    try:
        async with get_book_channel() as channel:
            stub = book_pb2_grpc.BookServiceStub(channel)
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
            )
            return _proto_to_book(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("", response_model=PaginatedResponse[BookResponse])
async def list_books(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
):
    try:
        async with get_book_channel() as channel:
            stub = book_pb2_grpc.BookServiceStub(channel)
            resp = await stub.ListBooks(
                book_pb2.ListBooksRequest(
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                    category=category or "",
                    sort_by=sort_by,
                    sort_order=sort_order,
                ),
                timeout=GRPC_TIMEOUT,
            )
            return PaginatedResponse(
                data=[_proto_to_book(b) for b in resp.books],
                pagination=PaginationMeta(
                    page=resp.pagination.page,
                    page_size=resp.pagination.page_size,
                    total_count=resp.pagination.total_count,
                    total_pages=resp.pagination.total_pages,
                ),
            )
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/search", response_model=PaginatedResponse[BookResponse])
async def search_books(
    q: str = Query(..., min_length=1),
    search_by: str = Query("all", pattern="^(title|author|category|isbn|all)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    try:
        async with get_book_channel() as channel:
            stub = book_pb2_grpc.BookServiceStub(channel)
            resp = await stub.SearchBooks(
                book_pb2.SearchBooksRequest(
                    query=q,
                    search_by=search_by,
                    pagination=common_pb2.PaginationRequest(page=page, page_size=page_size),
                ),
                timeout=GRPC_TIMEOUT,
            )
            return PaginatedResponse(
                data=[_proto_to_book(b) for b in resp.books],
                pagination=PaginationMeta(
                    page=resp.pagination.page,
                    page_size=resp.pagination.page_size,
                    total_count=resp.pagination.total_count,
                    total_pages=resp.pagination.total_pages,
                ),
            )
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: str):
    try:
        async with get_book_channel() as channel:
            stub = book_pb2_grpc.BookServiceStub(channel)
            resp = await stub.GetBook(
                book_pb2.GetBookRequest(id=book_id),
                timeout=GRPC_TIMEOUT,
            )
            return _proto_to_book(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(book_id: str, body: BookUpdate):
    try:
        async with get_book_channel() as channel:
            stub = book_pb2_grpc.BookServiceStub(channel)
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
            )
            return _proto_to_book(resp)
    except grpc.RpcError as e:
        grpc_error_to_http(e)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: str):
    try:
        async with get_book_channel() as channel:
            stub = book_pb2_grpc.BookServiceStub(channel)
            await stub.DeleteBook(
                book_pb2.DeleteBookRequest(id=book_id),
                timeout=GRPC_TIMEOUT,
            )
    except grpc.RpcError as e:
        grpc_error_to_http(e)
