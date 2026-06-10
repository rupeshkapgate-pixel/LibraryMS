"""Repository layer for Member Service."""
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member import Member, MembershipStatus


class MemberRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> Member:
        member = Member(
            id=uuid.uuid4(),
            full_name=data["full_name"],
            email=data["email"],
            phone=data.get("phone"),
            address=data.get("address"),
            membership_status=MembershipStatus.ACTIVE,
        )
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def get_by_id(self, member_id: str) -> Optional[Member]:
        stmt = select(Member).where(
            Member.id == uuid.UUID(member_id),
            Member.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[Member]:
        stmt = select(Member).where(Member.email == email, Member.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, member_id: str, data: dict) -> Optional[Member]:
        member = await self.get_by_id(member_id)
        if not member:
            return None
        for key, value in data.items():
            if value is not None and hasattr(member, key):
                setattr(member, key, value)
        member.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def deactivate(self, member_id: str) -> Optional[Member]:
        member = await self.get_by_id(member_id)
        if not member:
            return None
        member.membership_status = MembershipStatus.INACTIVE
        member.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def soft_delete(self, member_id: str) -> bool:
        member = await self.get_by_id(member_id)
        if not member:
            return False
        member.deleted_at = datetime.utcnow()
        await self.session.commit()
        return True

    async def list_members(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[MembershipStatus] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Member], int]:
        base_stmt = select(Member).where(Member.deleted_at.is_(None))

        if status:
            base_stmt = base_stmt.where(Member.membership_status == status)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total = await self.session.scalar(count_stmt)

        col = getattr(Member, sort_by, Member.created_at)
        if sort_order == "desc":
            base_stmt = base_stmt.order_by(col.desc())
        else:
            base_stmt = base_stmt.order_by(col.asc())

        base_stmt = base_stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(base_stmt)
        return result.scalars().all(), total or 0
