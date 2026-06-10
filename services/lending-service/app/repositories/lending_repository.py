"""
Lending Repository — data-access layer.

Provides no-commit helpers (flush only) and FOR UPDATE locking variants.
Public CRUD methods commit themselves without calling session.begin()
to be compatible with SQLAlchemy 2.x autobegin behavior.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lending import LendingRecord, LendingStatus

FINE_PER_DAY     = 10.0
DEFAULT_DUE_DAYS = 14


class LendingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── FOR UPDATE (row-level lock) ───────────────────────────────────────────

    async def get_by_id_for_update(self, record_id: str) -> Optional[LendingRecord]:
        """SELECT ... FOR UPDATE — serialises concurrent access to this row."""
        stmt = (
            select(LendingRecord)
            .where(LendingRecord.id == uuid.UUID(record_id))
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # ── no-commit helpers (used inside service-layer transactions) ────────────

    async def create_no_commit(
        self, member_id: str, book_id: str, due_days: int = DEFAULT_DUE_DAYS
    ) -> LendingRecord:
        now = datetime.utcnow()
        record = LendingRecord(
            id=uuid.uuid4(),
            member_id=uuid.UUID(member_id),
            book_id=uuid.UUID(book_id),
            borrowed_at=now,
            due_date=now + timedelta(days=due_days),
            status=LendingStatus.BORROWED,
            fine_amount=0.0,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    # ── Read-only helpers ─────────────────────────────────────────────────────

    async def get_by_id(self, record_id: str) -> Optional[LendingRecord]:
        stmt = select(LendingRecord).where(LendingRecord.id == uuid.UUID(record_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_record(self, member_id: str, book_id: str) -> Optional[LendingRecord]:
        stmt = select(LendingRecord).where(
            LendingRecord.member_id == uuid.UUID(member_id),
            LendingRecord.book_id == uuid.UUID(book_id),
            LendingRecord.status == LendingStatus.BORROWED,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_borrowed_books(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "borrowed_at",
        sort_order: str = "desc",
    ) -> Tuple[List[LendingRecord], int]:
        base = select(LendingRecord).where(
            LendingRecord.status.in_([LendingStatus.BORROWED, LendingStatus.OVERDUE])
        )
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        col = getattr(LendingRecord, sort_by, LendingRecord.borrowed_at)
        base = base.order_by(col.desc() if sort_order == "desc" else col.asc())
        base = base.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base)
        return result.scalars().all(), total or 0

    async def list_by_member(
        self, member_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[LendingRecord], int]:
        base = (
            select(LendingRecord)
            .where(LendingRecord.member_id == uuid.UUID(member_id))
            .order_by(LendingRecord.borrowed_at.desc())
        )
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        base = base.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base)
        return result.scalars().all(), total or 0

    async def list_by_book(
        self, book_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[LendingRecord], int]:
        base = (
            select(LendingRecord)
            .where(LendingRecord.book_id == uuid.UUID(book_id))
            .order_by(LendingRecord.borrowed_at.desc())
        )
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        base = base.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base)
        return result.scalars().all(), total or 0

    async def list_overdue(
        self, page: int = 1, page_size: int = 20
    ) -> Tuple[List[LendingRecord], int]:
        # First mark overdue records
        await self._mark_overdue()

        base = (
            select(LendingRecord)
            .where(LendingRecord.status == LendingStatus.OVERDUE)
            .order_by(LendingRecord.due_date.asc())
        )
        total = await self.session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        base = base.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base)
        return result.scalars().all(), total or 0

    # ── Transactional public methods (safe to call from gRPC handlers) ────────

    async def create(
        self, member_id: str, book_id: str, due_days: int = DEFAULT_DUE_DAYS
    ) -> LendingRecord:
        now = datetime.utcnow()
        record = LendingRecord(
            id=uuid.uuid4(),
            member_id=uuid.UUID(member_id),
            book_id=uuid.UUID(book_id),
            borrowed_at=now,
            due_date=now + timedelta(days=due_days),
            status=LendingStatus.BORROWED,
            fine_amount=0.0,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def return_book(self, record_id: str) -> Optional[LendingRecord]:
        record = await self.get_by_id(record_id)
        if not record or record.status == LendingStatus.RETURNED:
            return None
        now = datetime.utcnow()
        record.returned_at = now
        record.updated_at  = now
        record.status      = LendingStatus.RETURNED
        if now > record.due_date:
            record.fine_amount = (now - record.due_date).days * FINE_PER_DAY
        else:
            record.fine_amount = 0.0
        await self.session.commit()
        await self.session.refresh(record)
        return record

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _mark_overdue(self) -> None:
        now  = datetime.utcnow()
        stmt = select(LendingRecord).where(
            LendingRecord.status == LendingStatus.BORROWED,
            LendingRecord.due_date < now,
        )
        result = await self.session.execute(stmt)
        records = result.scalars().all()
        if records:
            for r in records:
                r.status     = LendingStatus.OVERDUE
                r.updated_at = now
            await self.session.commit()
