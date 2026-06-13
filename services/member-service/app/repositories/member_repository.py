"""Repository layer for Member Service."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member import Member, MembershipStatus


class MemberRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_no_commit(self, data: dict) -> Member:
        """Create a member without committing; caller owns commit/rollback."""
        member = Member(
            id=uuid.uuid4(),
            full_name=data["full_name"],
            email=data["email"],
            phone=data.get("phone"),
            address=data.get("address"),
            membership_status=MembershipStatus.ACTIVE,
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def create(self, data: dict) -> Member:
        try:
            member = await self.create_no_commit(data)
            await self.session.commit()
            await self.session.refresh(member)
            return member
        except Exception:
            await self.session.rollback()
            raise

    async def get_by_id(self, member_id: str) -> Optional[Member]:
        stmt = select(Member).where(
            Member.id == uuid.UUID(member_id),
            Member.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_for_update(self, member_id: str) -> Optional[Member]:
        """Fetch a member with SELECT ... FOR UPDATE row-level lock."""
        stmt = (
            select(Member)
            .where(Member.id == uuid.UUID(member_id), Member.deleted_at.is_(None))
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Member]:
        stmt = select(Member).where(Member.email == email, Member.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, member_id: str, data: dict) -> Optional[Member]:
        try:
            member = await self.get_by_id_for_update(member_id)
            if not member:
                await self.session.rollback()
                return None
            for key, value in data.items():
                if value is not None and hasattr(member, key):
                    setattr(member, key, value)
            member.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(member)
            return member
        except Exception:
            await self.session.rollback()
            raise

    async def deactivate(self, member_id: str) -> Optional[Member]:
        try:
            member = await self.get_by_id_for_update(member_id)
            if not member:
                await self.session.rollback()
                return None
            member.membership_status = MembershipStatus.INACTIVE
            member.updated_at = datetime.utcnow()
            await self.session.commit()
            await self.session.refresh(member)
            return member
        except Exception:
            await self.session.rollback()
            raise

    async def soft_delete(self, member_id: str) -> bool:
        try:
            member = await self.get_by_id_for_update(member_id)
            if not member:
                await self.session.rollback()
                return False
            member.deleted_at = datetime.utcnow()
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            raise

    async def list_members(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[MembershipStatus] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        query: Optional[str] = None,
    ) -> Tuple[List[Member], int]:
        base_stmt = select(Member).where(Member.deleted_at.is_(None))

        if status:
            base_stmt = base_stmt.where(Member.membership_status == status)
        if query:
            q = f"%{query.strip()}%"
            base_stmt = base_stmt.where(
                or_(
                    Member.full_name.ilike(q),
                    Member.email.ilike(q),
                    Member.phone.ilike(q),
                    Member.address.ilike(q),
                )
            )

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)

        allowed_sort_columns = {
            "full_name": Member.full_name,
            "email": Member.email,
            "membership_status": Member.membership_status,
            "created_at": Member.created_at,
            "updated_at": Member.updated_at,
        }
        col = allowed_sort_columns.get(sort_by, Member.created_at)
        base_stmt = base_stmt.order_by(col.desc() if sort_order == "desc" else col.asc())
        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0
