"""Repository layer for Lending Service."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lending import LendingRecord, LendingStatus

FINE_PER_DAY = 10.0  # ₹10 per day
DEFAULT_DUE_DAYS = 14


class LendingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_no_commit(
        self,
        member_id: str,
        book_id: str,
        due_days: int = DEFAULT_DUE_DAYS,
    ) -> LendingRecord:
        """Create a lending record without committing.

        Used by the service layer when it owns the transaction boundary.
        """
        now = datetime.utcnow()
        record = LendingRecord(
            id=uuid.uuid4(),
            member_id=uuid.UUID(member_id),
            book_id=uuid.UUID(book_id),
            borrowed_at=now,
            due_date=now + timedelta(days=due_days),
            returned_at=None,
            status=LendingStatus.BORROWED,
            fine_amount=0.0,
            created_at=now,
            updated_at=now,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def create(
        self,
        member_id: str,
        book_id: str,
        due_days: int = DEFAULT_DUE_DAYS,
    ) -> LendingRecord:
        """Legacy transactional create kept for repository unit tests and scripts."""
        try:
            record = await self.create_no_commit(member_id=member_id, book_id=book_id, due_days=due_days)
            await self.session.commit()
            await self.session.refresh(record)
            return record
        except Exception:
            await self.session.rollback()
            raise

    async def get_by_id(self, record_id: str) -> Optional[LendingRecord]:
        stmt = select(LendingRecord).where(LendingRecord.id == uuid.UUID(record_id))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, record_id: str) -> Optional[LendingRecord]:
        """Fetch a lending record with SELECT ... FOR UPDATE row-level lock."""
        stmt = select(LendingRecord).where(LendingRecord.id == uuid.UUID(record_id)).with_for_update()
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_record(
        self,
        member_id: str,
        book_id: str,
    ) -> Optional[LendingRecord]:
        stmt = select(LendingRecord).where(
            LendingRecord.member_id == uuid.UUID(member_id),
            LendingRecord.book_id == uuid.UUID(book_id),
            LendingRecord.status.in_([LendingStatus.BORROWED, LendingStatus.OVERDUE]),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def return_book(self, record_id: str) -> Optional[LendingRecord]:
        """Legacy return path, now protected by the same row lock as LendingService.

        This removes the previous unlocked concurrent-return path and keeps direct
        repository callers consistent with the service return flow.
        """
        try:
            record = await self.get_by_id_for_update(record_id)
            if not record:
                await self.session.rollback()
                return None
            if record.status == LendingStatus.RETURNED:
                await self.session.rollback()
                return None

            now = datetime.utcnow()
            record.returned_at = now
            record.updated_at = now
            overdue_days = max(0, (now - record.due_date).days) if now > record.due_date else 0
            record.fine_amount = overdue_days * FINE_PER_DAY
            record.status = LendingStatus.RETURNED

            await self.session.commit()
            await self.session.refresh(record)
            return record
        except Exception:
            await self.session.rollback()
            raise

    async def update_overdue_status(self) -> int:
        """Mark all overdue borrowed records."""
        now = datetime.utcnow()
        stmt = select(LendingRecord).where(
            LendingRecord.status == LendingStatus.BORROWED,
            LendingRecord.due_date < now,
        )
        result = await self.session.execute(stmt)
        records = result.scalars().all()

        count = 0
        for record in records:
            record.status = LendingStatus.OVERDUE
            record.updated_at = now
            count += 1

        if count:
            await self.session.commit()
        else:
            await self.session.rollback()
        return count

    def _apply_common_filters(
        self,
        stmt,
        *,
        query: Optional[str] = None,
        member_id: Optional[str] = None,
        book_id: Optional[str] = None,
        due_from: Optional[datetime] = None,
        due_to: Optional[datetime] = None,
    ):
        if member_id:
            stmt = stmt.where(LendingRecord.member_id == uuid.UUID(member_id))
        if book_id:
            stmt = stmt.where(LendingRecord.book_id == uuid.UUID(book_id))
        if due_from:
            stmt = stmt.where(LendingRecord.due_date >= due_from)
        if due_to:
            stmt = stmt.where(LendingRecord.due_date <= due_to)
        if query:
            q = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    cast(LendingRecord.id, String).ilike(q),
                    cast(LendingRecord.member_id, String).ilike(q),
                    cast(LendingRecord.book_id, String).ilike(q),
                )
            )
        return stmt

    async def list_borrowed_books(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "borrowed_at",
        sort_order: str = "desc",
        query: Optional[str] = None,
        member_id: Optional[str] = None,
        book_id: Optional[str] = None,
        status: Optional[LendingStatus] = None,
        due_from: Optional[datetime] = None,
        due_to: Optional[datetime] = None,
    ) -> Tuple[List[LendingRecord], int]:
        base_stmt = select(LendingRecord)
        if status:
            base_stmt = base_stmt.where(LendingRecord.status == status)
        else:
            base_stmt = base_stmt.where(LendingRecord.status.in_([LendingStatus.BORROWED, LendingStatus.OVERDUE]))
        base_stmt = self._apply_common_filters(
            base_stmt,
            query=query,
            member_id=member_id,
            book_id=book_id,
            due_from=due_from,
            due_to=due_to,
        )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)

        allowed_sort_columns = {
            "borrowed_at": LendingRecord.borrowed_at,
            "due_date": LendingRecord.due_date,
            "returned_at": LendingRecord.returned_at,
            "status": LendingRecord.status,
            "fine_amount": LendingRecord.fine_amount,
            "created_at": LendingRecord.created_at,
            "updated_at": LendingRecord.updated_at,
        }
        col = allowed_sort_columns.get(sort_by, LendingRecord.borrowed_at)
        base_stmt = base_stmt.order_by(col.desc() if sort_order == "desc" else col.asc())
        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0

    async def list_by_member(
        self,
        member_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[LendingRecord], int]:
        base_stmt = (
            select(LendingRecord)
            .where(LendingRecord.member_id == uuid.UUID(member_id))
            .order_by(LendingRecord.borrowed_at.desc())
        )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)

        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0

    async def list_by_book(
        self,
        book_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[LendingRecord], int]:
        base_stmt = (
            select(LendingRecord).where(LendingRecord.book_id == uuid.UUID(book_id)).order_by(LendingRecord.borrowed_at.desc())
        )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)

        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0

    async def list_overdue(
        self,
        page: int = 1,
        page_size: int = 20,
        query: Optional[str] = None,
        member_id: Optional[str] = None,
        book_id: Optional[str] = None,
        due_from: Optional[datetime] = None,
        due_to: Optional[datetime] = None,
    ) -> Tuple[List[LendingRecord], int]:
        await self.update_overdue_status()

        base_stmt = select(LendingRecord).where(LendingRecord.status == LendingStatus.OVERDUE)
        base_stmt = self._apply_common_filters(
            base_stmt,
            query=query,
            member_id=member_id,
            book_id=book_id,
            due_from=due_from,
            due_to=due_to,
        )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)

        base_stmt = base_stmt.order_by(LendingRecord.due_date.asc())
        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0
