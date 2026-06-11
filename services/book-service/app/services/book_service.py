"""Book Service — service layer."""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.repositories.book_repository import BookRepository
from app.telemetry.setup import DB_QUERY_COUNTER, DB_QUERY_LATENCY

logger = logging.getLogger(__name__)
_SVC = "book-service"


class BookService:
    """Business logic for books; owns explicit commit/rollback boundaries."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = BookRepository(session)

    async def create_book(self, data: dict) -> Book:
        t0 = time.perf_counter()
        try:
            existing = await self._repo.get_by_isbn_no_commit(data["isbn"])
            if existing:
                raise ValueError(f"Book with ISBN {data['isbn']} already exists")

            book = await self._repo.create_no_commit(data)
            await self._session.commit()
            await self._session.refresh(book)

            DB_QUERY_COUNTER.labels(service=_SVC, operation="create_book", status="ok").inc()
            return book
        except Exception:
            await self._session.rollback()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="create_book", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="create_book").observe(
                time.perf_counter() - t0
            )

    async def update_book(self, book_id: str, data: dict) -> Optional[Book]:
        t0 = time.perf_counter()
        try:
            book = await self._repo.get_by_id_for_update(book_id)
            if not book:
                await self._session.rollback()
                return None
            for key, value in data.items():
                if value is not None and hasattr(book, key):
                    setattr(book, key, value)
            book.updated_at = datetime.utcnow()

            await self._session.commit()
            await self._session.refresh(book)

            DB_QUERY_COUNTER.labels(service=_SVC, operation="update_book", status="ok").inc()
            return book
        except Exception:
            await self._session.rollback()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="update_book", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="update_book").observe(
                time.perf_counter() - t0
            )

    async def get_book(self, book_id: str) -> Optional[Book]:
        return await self._repo.get_by_id(book_id)

    async def list_books(
        self,
        page: int,
        page_size: int,
        category: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Book], int]:
        return await self._repo.list_books(
            page=page,
            page_size=page_size,
            category=category,
            sort_by=sort_by,
            sort_order=sort_order,
        )

    async def search_books(
        self,
        query: str,
        search_by: str,
        page: int,
        page_size: int,
    ) -> Tuple[List[Book], int]:
        return await self._repo.search(
            query=query,
            search_by=search_by,
            page=page,
            page_size=page_size,
        )

    async def check_availability(self, book_id: str) -> Tuple[bool, int]:
        book = await self._repo.get_by_id(book_id)
        if not book:
            raise LookupError(f"Book {book_id} not found")
        return book.available_copies > 0, book.available_copies

    async def decrease_copies(self, book_id: str, count: int = 1) -> int:
        t0 = time.perf_counter()
        try:
            if count <= 0:
                raise ValueError("count must be greater than zero")

            book = await self._repo.get_by_id_for_update(book_id)
            if not book:
                raise LookupError(f"Book {book_id} not found")
            if book.available_copies < count:
                raise ValueError(
                    f"Insufficient copies: requested {count}, available {book.available_copies}"
                )

            book.available_copies -= count
            book.updated_at = datetime.utcnow()
            new_available_copies = book.available_copies

            await self._session.commit()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="decrease_copies", status="ok").inc()
            return new_available_copies
        except Exception:
            await self._session.rollback()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="decrease_copies", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="decrease_copies").observe(
                time.perf_counter() - t0
            )

    async def increase_copies(self, book_id: str, count: int = 1) -> int:
        t0 = time.perf_counter()
        try:
            if count <= 0:
                raise ValueError("count must be greater than zero")

            book = await self._repo.get_by_id_for_update(book_id)
            if not book:
                raise LookupError(f"Book {book_id} not found")

            book.available_copies = min(book.available_copies + count, book.total_copies)
            book.updated_at = datetime.utcnow()
            new_available_copies = book.available_copies

            await self._session.commit()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="increase_copies", status="ok").inc()
            return new_available_copies
        except Exception:
            await self._session.rollback()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="increase_copies", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="increase_copies").observe(
                time.perf_counter() - t0
            )

    async def soft_delete(self, book_id: str) -> bool:
        try:
            book = await self._repo.get_by_id_for_update(book_id)
            if not book:
                await self._session.rollback()
                return False
            book.deleted_at = datetime.utcnow()
            await self._session.commit()
            return True
        except Exception:
            await self._session.rollback()
            raise
