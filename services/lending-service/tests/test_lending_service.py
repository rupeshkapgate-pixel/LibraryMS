"""
Tests for LendingService — distributed saga, transaction management, locking.
"""
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))
sys.path.insert(0, str(SERVICE_ROOT / "app" / "proto_generated"))

from app.models.lending import LendingRecord, LendingStatus
from app.repositories.lending_repository import FINE_PER_DAY, LendingRepository
from app.services.lending_service import LendingService


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
def borrowed_record():
    now = datetime.utcnow()
    return LendingRecord(
        id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        book_id=uuid.uuid4(),
        borrowed_at=now - timedelta(days=5),
        due_date=now + timedelta(days=9),
        status=LendingStatus.BORROWED,
        fine_amount=0.0,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def overdue_record():
    now = datetime.utcnow()
    return LendingRecord(
        id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        book_id=uuid.uuid4(),
        borrowed_at=now - timedelta(days=20),
        due_date=now - timedelta(days=5),
        status=LendingStatus.BORROWED,
        fine_amount=0.0,
        created_at=now,
        updated_at=now,
    )


class TestLendingRepository:
    @pytest.mark.asyncio
    async def test_create_no_commit_flushes_only(self, mock_session):
        repo = LendingRepository(mock_session)
        member_id = str(uuid.uuid4())
        book_id = str(uuid.uuid4())

        await repo.create_no_commit(member_id, book_id, due_days=14)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_by_id_for_update_issues_lock(self, mock_session, borrowed_record):
        repo = LendingRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = borrowed_record
        mock_session.execute = AsyncMock(return_value=mock_result)

        record = await repo.get_by_id_for_update(str(borrowed_record.id))

        assert record is not None

        call_args = mock_session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "FOR UPDATE" in compiled

    @pytest.mark.asyncio
    async def test_return_on_time_no_fine(self, mock_session, borrowed_record):
        repo = LendingRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = borrowed_record
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.return_book(str(borrowed_record.id))

        assert result is not None
        assert result.status == LendingStatus.RETURNED
        assert result.fine_amount == 0.0

    @pytest.mark.asyncio
    async def test_return_overdue_calculates_fine(self, mock_session, overdue_record):
        repo = LendingRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = overdue_record
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.return_book(str(overdue_record.id))

        assert result is not None
        assert result.status == LendingStatus.RETURNED
        assert result.fine_amount >= 5 * FINE_PER_DAY

    @pytest.mark.asyncio
    async def test_return_already_returned_returns_none(self, mock_session, borrowed_record):
        borrowed_record.status = LendingStatus.RETURNED
        repo = LendingRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = borrowed_record
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.return_book(str(borrowed_record.id))

        assert result is None

    @pytest.mark.asyncio
    async def test_return_not_found_returns_none(self, mock_session):
        repo = LendingRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.return_book(str(uuid.uuid4()))

        assert result is None


class TestFineCalculation:
    @pytest.mark.parametrize(
        "days,expected_fine",
        [
            (0, 0.0),
            (1, 10.0),
            (5, 50.0),
            (14, 140.0),
            (30, 300.0),
        ],
    )
    def test_fine_is_10_per_day(self, days, expected_fine):
        assert days * FINE_PER_DAY == expected_fine


class TestSagaCompensation:
    @pytest.mark.asyncio
    async def test_borrow_compensates_when_book_unavailable(self, mock_session):
        member_id = str(uuid.uuid4())
        book_id = str(uuid.uuid4())

        fake_record = MagicMock()
        fake_record.id = uuid.uuid4()

        mock_repo = MagicMock()
        mock_repo.create_no_commit = AsyncMock(return_value=fake_record)

        with patch.object(
            LendingService,
            "_validate_member",
            new=AsyncMock(return_value=("Alice", "a@b.com")),
        ), patch.object(
            LendingService,
            "_validate_book",
            new=AsyncMock(),
        ), patch.object(
            LendingService,
            "_decrease_book_copies",
            new=AsyncMock(side_effect=RuntimeError("Book service down")),
        ), patch.object(
            LendingService,
            "_cancel_lending_record",
            new=AsyncMock(),
        ) as mock_cancel:
            svc = LendingService(mock_session)
            svc._repo = mock_repo

            with pytest.raises(RuntimeError, match="Failed to decrease available copies"):
                await svc.borrow_book(member_id, book_id)

            mock_cancel.assert_awaited_once_with(str(fake_record.id))
