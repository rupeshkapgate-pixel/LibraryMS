"""
Book Repository — pure data-access layer.

Design contract:
  - Methods ending in _no_commit: flush only, used by BookService transaction blocks
  - get_by_id_for_update: issues SELECT ... FOR UPDATE (row-level lock)
  - Public CRUD methods (create/update/soft_delete/etc): manage their own commit,
    compatible with the v1 gRPC handler which calls them directly.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book


class BookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── FOR UPDATE (row-level lock) ───────────────────────────────────────────

    async def get_by_id_for_update(self, book_id: str) -> Optional[Book]:
        """SELECT ... FOR UPDATE — acquires row-level exclusive lock."""
        stmt = (
            select(Book)
            .where(Book.id == uuid.UUID(book_id), Book.deleted_at.is_(None))
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ── no-commit helpers (called inside service-layer transactions) ──────────

    async def create_no_commit(self, data: dict) -> Book:
        """Insert a Book row without committing — caller owns the transaction."""
        book = Book(
            id=uuid.uuid4(),
            title=data["title"],
            author=data["author"],
            isbn=data["isbn"],
            publisher=data.get("publisher"),
            category=data.get("category"),
            description=data.get("description"),
            published_year=data.get("published_year"),
            total_copies=data.get("total_copies", 1),
            available_copies=data.get("total_copies", 1),
            shelf_location=data.get("shelf_location"),
        )
        self.session.add(book)
        await self.session.flush()
        return book

    async def get_by_isbn_no_commit(self, isbn: str) -> Optional[Book]:
        stmt = select(Book).where(Book.isbn == isbn, Book.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Read-only helpers ─────────────────────────────────────────────────────

    async def get_by_id(self, book_id: str) -> Optional[Book]:
        stmt = select(Book).where(
            Book.id == uuid.UUID(book_id),
            Book.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_isbn(self, isbn: str) -> Optional[Book]:
        return await self.get_by_isbn_no_commit(isbn)

    async def list_books(
        self,
        page: int = 1,
        page_size: int = 20,
        category: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Book], int]:
        base_stmt = select(Book).where(Book.deleted_at.is_(None))
        if category:
            base_stmt = base_stmt.where(Book.category == category)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)

        col = getattr(Book, sort_by, Book.created_at)
        base_stmt = base_stmt.order_by(col.desc() if sort_order == "desc" else col.asc())
        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0

    async def search(
        self,
        query: str,
        search_by: str = "all",
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Book], int]:
        base_stmt = select(Book).where(Book.deleted_at.is_(None))
        q = f"%{query}%"

        filter_map = {
            "title":    Book.title.ilike(q),
            "author":   Book.author.ilike(q),
            "category": Book.category.ilike(q),
            "isbn":     Book.isbn.ilike(q),
        }
        if search_by in filter_map:
            base_stmt = base_stmt.where(filter_map[search_by])
        else:
            base_stmt = base_stmt.where(or_(*filter_map.values()))

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)
        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0

    # ── Transactional public methods (safe to call from gRPC handlers) ────────
    # These commit themselves — compatible with both the v1 handler (which calls
    # them directly) and the v2 BookService (which wraps them in its own begin()).
    # They do NOT call session.begin() to avoid conflicts with SQLAlchemy 2.x
    # autobegin when a prior read in the same session has already opened a txn.

    async def create(self, data: dict) -> Book:
        book = Book(
            id=uuid.uuid4(),
            title=data["title"],
            author=data["author"],
            isbn=data["isbn"],
            publisher=data.get("publisher"),
            category=data.get("category"),
            description=data.get("description"),
            published_year=data.get("published_year"),
            total_copies=data.get("total_copies", 1),
            available_copies=data.get("total_copies", 1),
            shelf_location=data.get("shelf_location"),
        )
        self.session.add(book)
        await self.session.commit()
        await self.session.refresh(book)
        return book

    async def update(self, book_id: str, data: dict) -> Optional[Book]:
        book = await self.get_by_id(book_id)
        if not book:
            return None
        for key, value in data.items():
            if value is not None and hasattr(book, key):
                setattr(book, key, value)
        book.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(book)
        return book

    async def soft_delete(self, book_id: str) -> bool:
        book = await self.get_by_id(book_id)
        if not book:
            return False
        book.deleted_at = datetime.utcnow()
        await self.session.commit()
        return True

    async def decrease_available_copies(self, book_id: str, count: int = 1) -> Optional[Book]:
        book = await self.get_by_id(book_id)
        if not book or book.available_copies < count:
            return None
        book.available_copies -= count
        book.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(book)
        return book

    async def increase_available_copies(self, book_id: str, count: int = 1) -> Optional[Book]:
        book = await self.get_by_id(book_id)
        if not book:
            return None
        book.available_copies = min(book.available_copies + count, book.total_copies)
        book.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(book)
        return book
