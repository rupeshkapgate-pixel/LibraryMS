"""
Book Repository — data-access layer.

Repository methods ending in `_no_commit` never commit and are intended for
service-layer transaction management. Legacy public mutation methods still exist
for direct repository callers and tests, but they now use explicit
commit/rollback instead of `session.begin()` so they do not fail when SQLAlchemy
has already auto-started a transaction after a SELECT.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book


class BookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── No-commit helpers used by BookService ────────────────────────────────

    async def create_no_commit(self, data: dict) -> Book:
        """Insert a Book row without committing; caller owns commit/rollback."""
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

    async def get_by_id_for_update(self, book_id: str) -> Optional[Book]:
        """Fetch a book with SELECT ... FOR UPDATE row-level lock."""
        stmt = (
            select(Book)
            .where(Book.id == uuid.UUID(book_id), Book.deleted_at.is_(None))
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Read-only helpers ────────────────────────────────────────────────────

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
            "title": Book.title.ilike(q),
            "author": Book.author.ilike(q),
            "category": Book.category.ilike(q),
            "isbn": Book.isbn.ilike(q),
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

    # ── Legacy transactional mutation methods ────────────────────────────────

    async def create(self, data: dict) -> Book:
        try:
            book = await self.create_no_commit(data)
            await self.session.commit()
            await self.session.refresh(book)
            return book
        except Exception:
            await self.session.rollback()
            raise

    async def update(self, book_id: str, data: dict) -> Optional[Book]:
        try:
            book = await self.get_by_id_for_update(book_id)
            if not book:
                await self.session.rollback()
                return None
            for key, value in data.items():
                if value is not None and hasattr(book, key):
                    setattr(book, key, value)
            book.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(book)
            return book
        except Exception:
            await self.session.rollback()
            raise

    async def soft_delete(self, book_id: str) -> bool:
        try:
            book = await self.get_by_id_for_update(book_id)
            if not book:
                await self.session.rollback()
                return False
            book.deleted_at = datetime.utcnow()
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            raise

    async def decrease_available_copies(self, book_id: str, count: int = 1) -> Optional[Book]:
        try:
            book = await self.get_by_id_for_update(book_id)
            if not book or book.available_copies < count:
                await self.session.rollback()
                return None
            book.available_copies -= count
            book.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(book)
            return book
        except Exception:
            await self.session.rollback()
            raise

    async def increase_available_copies(self, book_id: str, count: int = 1) -> Optional[Book]:
        try:
            book = await self.get_by_id_for_update(book_id)
            if not book:
                await self.session.rollback()
                return None
            book.available_copies = min(book.available_copies + count, book.total_copies)
            book.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(book)
            return book
        except Exception:
            await self.session.rollback()
            raise
