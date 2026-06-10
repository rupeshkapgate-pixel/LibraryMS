"""Tests for Member Service — repository and business rules."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.repositories.member_repository import MemberRepository
from app.models.member import Member, MembershipStatus


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit  = AsyncMock()
    session.refresh = AsyncMock()
    session.add     = MagicMock()
    session.execute = AsyncMock()
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


def _mock_execute(session, return_value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = return_value
    session.execute = AsyncMock(return_value=result)


# ── Create ────────────────────────────────────────────────────────────────────

class TestMemberCreate:
    @pytest.mark.asyncio
    async def test_create_adds_and_commits(self, mock_session):
        await MemberRepository(mock_session).create(
            {"full_name": "Bob", "email": "bob@example.com"}
        )
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_new_member_status_is_active(self, mock_session):
        added = []
        mock_session.add.side_effect = lambda m: added.append(m)
        await MemberRepository(mock_session).create(
            {"full_name": "Test", "email": "test@test.com"}
        )
        assert added[0].membership_status == MembershipStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_create_stores_correct_fields(self, mock_session):
        added = []
        mock_session.add.side_effect = lambda m: added.append(m)
        await MemberRepository(mock_session).create(
            {"full_name": "Jane Doe", "email": "jane@example.com",
             "phone": "9999999999", "address": "Pune"}
        )
        m = added[0]
        assert m.full_name == "Jane Doe"
        assert m.email == "jane@example.com"
        assert m.phone == "9999999999"


# ── Get ───────────────────────────────────────────────────────────────────────

class TestMemberGet:
    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_session, active_member):
        _mock_execute(mock_session, active_member)
        result = await MemberRepository(mock_session).get_by_id(str(active_member.id))
        assert result is not None
        assert result.email == "alice@example.com"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_session):
        _mock_execute(mock_session, None)
        result = await MemberRepository(mock_session).get_by_id(str(uuid.uuid4()))
        assert result is None


# ── Update ────────────────────────────────────────────────────────────────────

class TestMemberUpdate:
    @pytest.mark.asyncio
    async def test_update_phone(self, mock_session, active_member):
        _mock_execute(mock_session, active_member)
        result = await MemberRepository(mock_session).update(
            str(active_member.id), {"phone": "+91 11111 11111"}
        )
        assert result is not None
        assert result.phone == "+91 11111 11111"

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, mock_session):
        _mock_execute(mock_session, None)
        result = await MemberRepository(mock_session).update(str(uuid.uuid4()), {"phone": "x"})
        assert result is None


# ── Deactivate ────────────────────────────────────────────────────────────────

class TestMemberDeactivate:
    @pytest.mark.asyncio
    async def test_deactivate_sets_status_inactive(self, mock_session, active_member):
        _mock_execute(mock_session, active_member)
        result = await MemberRepository(mock_session).deactivate(str(active_member.id))
        assert result is not None
        assert result.membership_status == MembershipStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_deactivate_nonexistent_returns_none(self, mock_session):
        _mock_execute(mock_session, None)
        result = await MemberRepository(mock_session).deactivate(str(uuid.uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_deactivate_commits(self, mock_session, active_member):
        _mock_execute(mock_session, active_member)
        await MemberRepository(mock_session).deactivate(str(active_member.id))
        mock_session.commit.assert_awaited()
