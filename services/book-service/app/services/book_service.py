"""
Book Service — service layer.

Sits between the gRPC handler (presentation) and the repository (data access).
Owns:
  - Business rule enforcement (duplicate ISBN check)
  - Transaction boundaries: the service layer starts/commits transactions;
    repositories are purely query/mutation helpers that do NOT commit.
  - Optimistic/pessimistic locking for copy-count mutations
"""
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Optional, Tuple, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.repositories.book_repository import BookRepository
from app.telemetry.setup import DB_QUERY_COUNTER, DB_QUERY_LATENCY

logger = logging.getLogger(__name__)
_SVC = "book-service"


class BookService:
    """
    Stateless service object – instantiated per-request with an injected session.
    All public methods manage the transaction lifecycle; repositories never commit.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = BookRepository(session)

    # ── Create ────────────────────────────────────────────────────────────────

    async def create_book(self, data: dict) -> Book:
        t0 = time.perf_counter()
        try:
            async with self._session.begin():
                existing = await self._repo.get_by_isbn_no_commit(data["isbn"])
                if existing:
                    raise ValueError(f"Book with ISBN {data['isbn']} already exists")
                book = await self._repo.create_no_commit(data)
            DB_QUERY_COUNTER.labels(service=_SVC, operation="create_book", status="ok").inc()
            return book
        except Exception:
            DB_QUERY_COUNTER.labels(service=_SVC, operation="create_book", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="create_book").observe(
                time.perf_counter() - t0
            )

    # ── Update ────────────────────────────────────────────────────────────────

    async def update_book(self, book_id: str, data: dict) -> Optional[Book]:
        t0 = time.perf_counter()
        try:
            async with self._session.begin():
                book = await self._repo.get_by_id_for_update(book_id)
                if not book:
                    return None
                for key, value in data.items():
                    if value is not None and hasattr(book, key):
                        setattr(book, key, value)
                book.updated_at = datetime.utcnow()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="update_book", status="ok").inc()
            return book
        except Exception:
            DB_QUERY_COUNTER.labels(service=_SVC, operation="update_book", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="update_book").observe(
                time.perf_counter() - t0
            )

    # ── Get ───────────────────────────────────────────────────────────────────

    async def get_book(self, book_id: str) -> Optional[Book]:
        return await self._repo.get_by_id(book_id)

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_books(
        self,
        page: int,
        page_size: int,
        category: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Book], int]:
        return await self._repo.list_books(
            page=page, page_size=page_size,
            category=category, sort_by=sort_by, sort_order=sort_order,
        )

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_books(
        self, query: str, search_by: str, page: int, page_size: int
    ) -> Tuple[List[Book], int]:
        return await self._repo.search(
            query=query, search_by=search_by, page=page, page_size=page_size
        )

    # ── Availability ──────────────────────────────────────────────────────────

    async def check_availability(self, book_id: str) -> Tuple[bool, int]:
        book = await self._repo.get_by_id(book_id)
        if not book:
            raise LookupError(f"Book {book_id} not found")
        return book.available_copies > 0, book.available_copies

    # ── Copy mutations with row-level locking ─────────────────────────────────

    async def decrease_copies(self, book_id: str, count: int = 1) -> int:
        """
        Decrease available_copies by *count* using SELECT … FOR UPDATE (row-level lock).
        This prevents lost-update races when multiple concurrent borrow requests
        hit the same book simultaneously.

        Returns the new available_copies value.
        Raises ValueError if there are insufficient copies.
        """
        t0 = time.perf_counter()
        try:
            async with self._session.begin():
                # Acquire a row-level exclusive lock before reading
                book = await self._repo.get_by_id_for_update(book_id)
                if not book:
                    raise LookupError(f"Book {book_id} not found")
                if book.available_copies < count:
                    raise ValueError(
                        f"Insufficient copies: requested {count}, "
                        f"available {book.available_copies}"
                    )
                book.available_copies -= count
                book.updated_at = datetime.utcnow()
                # Transaction commits automatically on context-manager exit
            DB_QUERY_COUNTER.labels(service=_SVC, operation="decrease_copies", status="ok").inc()
            return book.available_copies
        except Exception:
            DB_QUERY_COUNTER.labels(service=_SVC, operation="decrease_copies", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="decrease_copies").observe(
                time.perf_counter() - t0
            )

    async def increase_copies(self, book_id: str, count: int = 1) -> int:
        """
        Increase available_copies by *count* using SELECT … FOR UPDATE.
        Caps at total_copies.
        """
        t0 = time.perf_counter()
        try:
            async with self._session.begin():
                book = await self._repo.get_by_id_for_update(book_id)
                if not book:
                    raise LookupError(f"Book {book_id} not found")
                book.available_copies = min(
                    book.available_copies + count, book.total_copies
                )
                book.updated_at = datetime.utcnow()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="increase_copies", status="ok").inc()
            return book.available_copies
        except Exception:
            DB_QUERY_COUNTER.labels(service=_SVC, operation="increase_copies", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="increase_copies").observe(
                time.perf_counter() - t0
            )

    # ── Delete ────────────────────────────────────────────────────────────────

    async def soft_delete(self, book_id: str) -> bool:
        async with self._session.begin():
            book = await self._repo.get_by_id_for_update(book_id)
            if not book:
                return False
            book.deleted_at = datetime.utcnow()
        return True
