"""gRPC handlers for Book Service."""
import logging
import math
from datetime import datetime

import grpc

from app.database import AsyncSessionLocal
from app.repositories.book_repository import BookRepository
from app.proto_generated import book_pb2, book_pb2_grpc, common_pb2

logger = logging.getLogger(__name__)


def _book_to_proto(book) -> book_pb2.Book:
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


class BookServiceHandler(book_pb2_grpc.BookServiceServicer):

    async def CreateBook(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = BookRepository(session)
                existing = await repo.get_by_isbn(request.isbn)
                if existing:
                    context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                    context.set_details(f"Book with ISBN {request.isbn} already exists")
                    return book_pb2.Book()

                data = {
                    "title": request.title,
                    "author": request.author,
                    "isbn": request.isbn,
                    "publisher": request.publisher,
                    "category": request.category,
                    "description": request.description,
                    "published_year": request.published_year or None,
                    "total_copies": request.total_copies or 1,
                    "shelf_location": request.shelf_location,
                }
                book = await repo.create(data)
                logger.info(f"Book created: {book.id}")
                return _book_to_proto(book)
        except Exception as e:
            logger.error(f"CreateBook error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return book_pb2.Book()

    async def UpdateBook(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = BookRepository(session)
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

                book = await repo.update(request.id, data)
                if not book:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Book {request.id} not found")
                    return book_pb2.Book()
                return _book_to_proto(book)
        except Exception as e:
            logger.error(f"UpdateBook error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return book_pb2.Book()

    async def GetBook(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = BookRepository(session)
                book = await repo.get_by_id(request.id)
                if not book:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Book {request.id} not found")
                    return book_pb2.Book()
                return _book_to_proto(book)
        except Exception as e:
            logger.error(f"GetBook error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return book_pb2.Book()

    async def ListBooks(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = BookRepository(session)
                page = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                books, total = await repo.list_books(
                    page=page,
                    page_size=page_size,
                    category=request.category or None,
                    sort_by=request.sort_by or "created_at",
                    sort_order=request.sort_order or "desc",
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
        except Exception as e:
            logger.error(f"ListBooks error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return book_pb2.ListBooksResponse()

    async def SearchBooks(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = BookRepository(session)
                page = request.pagination.page or 1
                page_size = request.pagination.page_size or 20
                books, total = await repo.search(
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
        except Exception as e:
            logger.error(f"SearchBooks error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return book_pb2.SearchBooksResponse()

    async def CheckAvailability(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = BookRepository(session)
                book = await repo.get_by_id(request.book_id)
                if not book:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Book {request.book_id} not found")
                    return book_pb2.CheckAvailabilityResponse()
                return book_pb2.CheckAvailabilityResponse(
                    available=book.available_copies > 0,
                    available_copies=book.available_copies,
                )
        except Exception as e:
            logger.error(f"CheckAvailability error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return book_pb2.CheckAvailabilityResponse()

    async def DecreaseAvailableCopies(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = BookRepository(session)
                book = await repo.decrease_available_copies(request.book_id, request.count or 1)
                if not book:
                    context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                    context.set_details("Book not found or insufficient copies")
                    return book_pb2.UpdateCopiesResponse()
                return book_pb2.UpdateCopiesResponse(
                    success=True,
                    available_copies=book.available_copies,
                )
        except Exception as e:
            logger.error(f"DecreaseAvailableCopies error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return book_pb2.UpdateCopiesResponse()

    async def IncreaseAvailableCopies(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = BookRepository(session)
                book = await repo.increase_available_copies(request.book_id, request.count or 1)
                if not book:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Book {request.book_id} not found")
                    return book_pb2.UpdateCopiesResponse()
                return book_pb2.UpdateCopiesResponse(
                    success=True,
                    available_copies=book.available_copies,
                )
        except Exception as e:
            logger.error(f"IncreaseAvailableCopies error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return book_pb2.UpdateCopiesResponse()

    async def DeleteBook(self, request, context):
        try:
            async with AsyncSessionLocal() as session:
                repo = BookRepository(session)
                deleted = await repo.soft_delete(request.id)
                if not deleted:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details(f"Book {request.id} not found")
                    return common_pb2.StatusResponse(success=False, message="Book not found")
                return common_pb2.StatusResponse(success=True, message="Book deleted")
        except Exception as e:
            logger.error(f"DeleteBook error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.StatusResponse(success=False, message=str(e))
