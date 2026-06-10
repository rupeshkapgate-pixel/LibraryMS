"""Member Service — business logic layer."""
from __future__ import annotations

import logging
import time
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.member import Member, MembershipStatus
from app.repositories.member_repository import MemberRepository
from app.telemetry.setup import DB_QUERY_COUNTER, DB_QUERY_LATENCY

logger = logging.getLogger(__name__)
_SVC = "member-service"


class MemberService:
    """
    Owns all business rules for member management.
    Transaction boundaries are managed here; the repository only builds queries.
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = MemberRepository(session)

    async def create_member(self, data: dict) -> Member:
        t0 = time.perf_counter()
        try:
            async with self._session.begin():
                existing = await self._repo.get_by_email(data["email"])
                if existing:
                    raise ValueError(f"Member with email {data['email']} already exists")
                member = await self._repo.create_no_commit(data)
            DB_QUERY_COUNTER.labels(service=_SVC, operation="create_member", status="ok").inc()
            return member
        except Exception:
            DB_QUERY_COUNTER.labels(service=_SVC, operation="create_member", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="create_member").observe(
                time.perf_counter() - t0
            )

    async def update_member(self, member_id: str, data: dict) -> Optional[Member]:
        t0 = time.perf_counter()
        try:
            async with self._session.begin():
                member = await self._repo.get_by_id_for_update(member_id)
                if not member:
                    return None
                for key, value in data.items():
                    if value is not None and hasattr(member, key):
                        setattr(member, key, value)
                from datetime import datetime
                member.updated_at = datetime.utcnow()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="update_member", status="ok").inc()
            return member
        except Exception:
            DB_QUERY_COUNTER.labels(service=_SVC, operation="update_member", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="update_member").observe(
                time.perf_counter() - t0
            )

    async def get_member(self, member_id: str) -> Optional[Member]:
        return await self._repo.get_by_id(member_id)

    async def list_members(
        self, page: int, page_size: int,
        status: Optional[MembershipStatus] = None,
        sort_by: str = "created_at", sort_order: str = "desc",
    ) -> Tuple[List[Member], int]:
        return await self._repo.list_members(
            page=page, page_size=page_size,
            status=status, sort_by=sort_by, sort_order=sort_order,
        )

    async def validate_active(self, member_id: str) -> Tuple[bool, str, Optional[Member]]:
        member = await self._repo.get_by_id(member_id)
        if not member:
            return False, f"Member {member_id} not found", None
        if member.membership_status == MembershipStatus.INACTIVE:
            return False, "Member is inactive", member
        return True, "Member is active", member

    async def deactivate(self, member_id: str) -> Optional[Member]:
        t0 = time.perf_counter()
        try:
            async with self._session.begin():
                member = await self._repo.get_by_id_for_update(member_id)
                if not member:
                    return None
                member.membership_status = MembershipStatus.INACTIVE
                from datetime import datetime
                member.updated_at = datetime.utcnow()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="deactivate", status="ok").inc()
            return member
        except Exception:
            DB_QUERY_COUNTER.labels(service=_SVC, operation="deactivate", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="deactivate").observe(
                time.perf_counter() - t0
            )
