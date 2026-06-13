"""gRPC handlers for Book Service.

Handlers are intentionally thin: they translate protobuf messages and gRPC
status codes while all business rules and transaction boundaries live in
BookService.
"""
from __future__ import annotations

import logging
import math

import grpc
from sqlalchemy.exc import IntegrityError

from app.database import AsyncSessionLocal
from app.models.book import Book
from app.observability.logging import get_grpc_correlation_id, log_event
from app.proto_generated import book_pb2, book_pb2_grpc, common_pb2
from app.services.book_service import BookService

logger = logging.getLogger(__name__)
_SERVICE = "book-service"


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


def _book_to_proto(book: Book) -> book_pb2.Book:
    return book_pb2.Book(
        id=str(book.id),
        title=book.title or "",
        author=book.author or "",
        isbn=book.isbn or "",
        publisher=book.publisher or "",
        category=book.category or "",
        description=book.description or "",
        published_year=book.published_year or 0,
        total_copies=book.total_copies or 0,
        available_copies=book.available_copies or 0,
        shelf_location=book.shelf_location or "",
        created_at=book.created_at.isoformat() if book.created_at else "",
        updated_at=book.updated_at.isoformat() if book.updated_at else "",
        deleted_at=book.deleted_at.isoformat() if book.deleted_at else "",
    )


def _set_error(context, exc: Exception) -> None:
    if isinstance(exc, LookupError):
        context.set_code(grpc.StatusCode.NOT_FOUND)
    elif isinstance(exc, IntegrityError):
        context.set_code(grpc.StatusCode.ALREADY_EXISTS)
    elif isinstance(exc, ValueError):
        msg = str(exc).lower()
        context.set_code(grpc.StatusCode.ALREADY_EXISTS if "already exists" in msg else grpc.StatusCode.INVALID_ARGUMENT)
    else:
        context.set_code(grpc.StatusCode.INTERNAL)
    context.set_details(str(exc))


class BookServiceHandler(book_pb2_grpc.BookServiceServicer):
    async def CreateBook(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = BookService(session)
                book = await service.create_book(
                    {
                        "title": request.title,
                        "author": request.author,
                        "isbn": request.isbn,
                        "publisher": request.publisher or None,
                        "category": request.category or None,
                        "description": request.description or None,
                        "published_year": request.published_year or None,
                        "total_copies": request.total_copies or 1,
                        "shelf_location": request.shelf_location or None,
                    }
                )
                _log_info("CreateBook", context, "Book created", book_id=str(book.id), isbn=book.isbn)
                return _book_to_proto(book)
        except Exception as exc:
            _log_error("CreateBook", context, exc)
            _set_error(context, exc)
            return book_pb2.Book()

    async def UpdateBook(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = BookService(session)
                data = {}
                if request.title:
                    data["title"] = request.title
                if request.author:
                    data["author"] = request.author
                if request.isbn:
                    data["isbn"] = request.isbn
                if request.publisher:
                    data["publisher"] = request.publisher
                if request.category:
                    data["category"] = request.category
                if request.description:
                    data["description"] = request.description
                if request.published_year:
                    data["published_year"] = request.published_year
                if request.total_copies:
                    data["total_copies"] = request.total_copies
                if request.shelf_location:
                    data["shelf_location"] = request.shelf_location

                book = await service.update_book(request.id, data)
                if not book:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Book {request.id} not found")
                    return book_pb2.Book()
                return _book_to_proto(book)
        except Exception as exc:
            _log_error("UpdateBook", context, exc)
            _set_error(context, exc)
            return book_pb2.Book()

    async def GetBook(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = BookService(session)
                book = await service.get_book(request.id)
                if not book:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Book {request.id} not found")
                    return book_pb2.Book()
                return _book_to_proto(book)
        except Exception as exc:
            _log_error("GetBook", context, exc)
            _set_error(context, exc)
            return book_pb2.Book()

    async def ListBooks(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = BookService(session)
                page = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                books, total = await service.list_books(
                    page=page,
                    page_size=page_size,
                    category=request.category or None,
                    sort_by=request.sort_by or "created_at",
                    sort_order=request.sort_order or "desc",
                    query=request.query or None,
                    search_by=request.search_by or "all",
                    author=request.author or None,
                    publisher=request.publisher or None,
                    available_only=request.available_only,
                )
                total_pages = math.ceil(total / page_size) if page_size > 0 else 0
                return book_pb2.ListBooksResponse(
                    books=[_book_to_proto(b) for b in books],
                    pagination=common_pb2.PaginationResponse(
                        page=page,
                        page_size=page_size,
                        total_count=total,
                        total_pages=total_pages,
                    ),
                )
        except Exception as exc:
            _log_error("ListBooks", context, exc)
            _set_error(context, exc)
            return book_pb2.ListBooksResponse()

    async def SearchBooks(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = BookService(session)
                page = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                books, total = await service.search_books(
                    query=request.query,
                    search_by=request.search_by or "all",
                    page=page,
                    page_size=page_size,
                )
                total_pages = math.ceil(total / page_size) if page_size > 0 else 0
                return book_pb2.SearchBooksResponse(
                    books=[_book_to_proto(b) for b in books],
                    pagination=common_pb2.PaginationResponse(
                        page=page,
                        page_size=page_size,
                        total_count=total,
                        total_pages=total_pages,
                    ),
                )
        except Exception as exc:
            _log_error("SearchBooks", context, exc)
            _set_error(context, exc)
            return book_pb2.SearchBooksResponse()

    async def CheckAvailability(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = BookService(session)
                available, available_copies = await service.check_availability(request.book_id)
                return book_pb2.CheckAvailabilityResponse(available=available, available_copies=available_copies)
        except Exception as exc:
            _log_error("CheckAvailability", context, exc)
            _set_error(context, exc)
            return book_pb2.CheckAvailabilityResponse()

    async def DecreaseAvailableCopies(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = BookService(session)
                available_copies = await service.decrease_copies(request.book_id, request.count or 1)
                return book_pb2.UpdateCopiesResponse(success=True, available_copies=available_copies)
        except ValueError as exc:
            _log_error("DecreaseAvailableCopies", context, exc)
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details(str(exc))
            return book_pb2.UpdateCopiesResponse(success=False)
        except Exception as exc:
            _log_error("DecreaseAvailableCopies", context, exc)
            _set_error(context, exc)
            return book_pb2.UpdateCopiesResponse(success=False)

    async def IncreaseAvailableCopies(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = BookService(session)
                available_copies = await service.increase_copies(request.book_id, request.count or 1)
                return book_pb2.UpdateCopiesResponse(success=True, available_copies=available_copies)
        except Exception as exc:
            _log_error("IncreaseAvailableCopies", context, exc)
            _set_error(context, exc)
            return book_pb2.UpdateCopiesResponse(success=False)

    async def DeleteBook(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                service = BookService(session)
                deleted = await service.soft_delete(request.id)
                if not deleted:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Book {request.id} not found")
                    return common_pb2.StatusResponse(success=False, message="Book not found")
                return common_pb2.StatusResponse(success=True, message="Book deleted")
        except Exception as exc:
            _log_error("DeleteBook", context, exc)
            _set_error(context, exc)
            return common_pb2.StatusResponse(success=False, message=str(exc))
