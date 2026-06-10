"""Repository layer for Lending Service."""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lending import LendingRecord, LendingStatus

FINE_PER_DAY = 10.0  # ₹10 per day
DEFAULT_DUE_DAYS = 14


class LendingRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, member_id: str, book_id: str, due_days: int = DEFAULT_DUE_DAYS) -> LendingRecord:
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

    async def return_book(self, record_id: str) -> Optional[LendingRecord]:
        record = await self.get_by_id(record_id)
        if not record:
            return None
        if record.status == LendingStatus.RETURNED:
            return None

        now = datetime.utcnow()
        record.returned_at = now
        record.updated_at = now

        # Calculate fine
        if now > record.due_date:
            overdue_days = (now - record.due_date).days
            record.fine_amount = overdue_days * FINE_PER_DAY
            record.status = LendingStatus.RETURNED
        else:
            record.fine_amount = 0.0
            record.status = LendingStatus.RETURNED

        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def update_overdue_status(self) -> int:
        """Mark all overdue records."""
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
        return count

    async def list_borrowed_books(
        self,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "borrowed_at",
        sort_order: str = "desc",
    ) -> Tuple[List[LendingRecord], int]:
        base_stmt = select(LendingRecord).where(
            LendingRecord.status.in_([LendingStatus.BORROWED, LendingStatus.OVERDUE])
        )
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)

        col = getattr(LendingRecord, sort_by, LendingRecord.borrowed_at)
        if sort_order == "desc":
            base_stmt = base_stmt.order_by(col.desc())
        else:
            base_stmt = base_stmt.order_by(col.asc())

        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0

    async def list_by_member(
        self, member_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[LendingRecord], int]:
        base_stmt = select(LendingRecord).where(
            LendingRecord.member_id == uuid.UUID(member_id)
        ).order_by(LendingRecord.borrowed_at.desc())

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)

        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0

    async def list_by_book(
        self, book_id: str, page: int = 1, page_size: int = 20
    ) -> Tuple[List[LendingRecord], int]:
        base_stmt = select(LendingRecord).where(
            LendingRecord.book_id == uuid.UUID(book_id)
        ).order_by(LendingRecord.borrowed_at.desc())

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)

        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0

    async def list_overdue(
        self, page: int = 1, page_size: int = 20
    ) -> Tuple[List[LendingRecord], int]:
        # First update overdue status
        await self.update_overdue_status()

        base_stmt = select(LendingRecord).where(
            LendingRecord.status == LendingStatus.OVERDUE
        ).order_by(LendingRecord.due_date.asc())

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)

        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0
