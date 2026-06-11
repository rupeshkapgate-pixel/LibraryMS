"""Tests for Member Service."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.repositories.member_repository import MemberRepository
from app.models.member import Member, MembershipStatus

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def active_member():
    return Member(
        id=uuid.uuid4(),
        full_name="Alice Kumar",
        email="alice@example.com",
        phone="+91 9876543210",
        address="123 MG Road, Pune",
        membership_status=MembershipStatus.ACTIVE,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestMemberRepository:
    @pytest.mark.asyncio
    async def test_create_member(self, mock_session):
        repo = MemberRepository(mock_session)
        data = {
            "full_name": "Bob Singh",
            "email": "bob@example.com",
            "phone": "9876543210",
            "address": "456 FC Road",
        }
        await repo.create(data)
        assert mock_session.add.called
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_get_member_by_id(self, mock_session, active_member):
        repo = MemberRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = active_member
        mock_session.execute = AsyncMock(return_value=mock_result)

        member = await repo.get_by_id(str(active_member.id))
        assert member is not None
        assert member.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_deactivate_member(self, mock_session, active_member):
        repo = MemberRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = active_member
        mock_session.execute = AsyncMock(return_value=mock_result)

        member = await repo.deactivate(str(active_member.id))
        assert member is not None
        assert member.membership_status == MembershipStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_deactivate_nonexistent(self, mock_session):
        repo = MemberRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        member = await repo.deactivate(str(uuid.uuid4()))
        assert member is None

    @pytest.mark.asyncio
    async def test_member_initial_status_active(self, mock_session):
        """New members must be ACTIVE by default."""
        repo = MemberRepository(mock_session)
        added_member = None

        def capture_add(m):
            nonlocal added_member
            added_member = m

        mock_session.add.side_effect = capture_add
        await repo.create({"full_name": "Test", "email": "test@test.com"})
        assert added_member is not None
        assert added_member.membership_status == MembershipStatus.ACTIVE
