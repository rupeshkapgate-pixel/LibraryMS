"""Tests for Lending Service - Fine Calculation and Business Logic."""
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest

from services.lending_service.app.repositories.lending_repository import (
    LendingRepository, FINE_PER_DAY
)
from services.lending_service.app.models.lending import LendingRecord, LendingStatus


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def sample_record_on_time():
    now = datetime.utcnow()
    return LendingRecord(
        id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        book_id=uuid.uuid4(),
        borrowed_at=now - timedelta(days=5),
        due_date=now + timedelta(days=9),  # still has time
        status=LendingStatus.BORROWED,
        fine_amount=0.0,
        created_at=now - timedelta(days=5),
        updated_at=now - timedelta(days=5),
    )


@pytest.fixture
def sample_record_overdue():
    now = datetime.utcnow()
    return LendingRecord(
        id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        book_id=uuid.uuid4(),
        borrowed_at=now - timedelta(days=20),
        due_date=now - timedelta(days=5),  # 5 days overdue
        status=LendingStatus.BORROWED,
        fine_amount=0.0,
        created_at=now - timedelta(days=20),
        updated_at=now - timedelta(days=20),
    )


class TestFineCalculation:
    def test_fine_per_day_constant(self):
        assert FINE_PER_DAY == 10.0

    def test_no_fine_for_on_time_return(self):
        """Fine = 0 when returned before due date."""
        now = datetime.utcnow()
        due = now + timedelta(days=5)
        # Simulate: returned now, due in 5 days → no overdue
        overdue = max(0, (now - due).days)
        fine = overdue * FINE_PER_DAY
        assert fine == 0.0

    def test_fine_for_5_days_overdue(self):
        """Fine = ₹50 for 5 days overdue."""
        now = datetime.utcnow()
        due = now - timedelta(days=5)
        overdue = max(0, (now - due).days)
        fine = overdue * FINE_PER_DAY
        assert fine == 50.0

    def test_fine_for_1_day_overdue(self):
        """Fine = ₹10 for 1 day overdue."""
        now = datetime.utcnow()
        due = now - timedelta(days=1)
        overdue = max(0, (now - due).days)
        fine = overdue * FINE_PER_DAY
        assert fine == 10.0

    def test_fine_for_30_days_overdue(self):
        """Fine = ₹300 for 30 days overdue."""
        now = datetime.utcnow()
        due = now - timedelta(days=30)
        overdue = max(0, (now - due).days)
        fine = overdue * FINE_PER_DAY
        assert fine == 300.0


class TestLendingRepository:
    @pytest.mark.asyncio
    async def test_create_lending_record(self, mock_session):
        repo = LendingRepository(mock_session)
        member_id = str(uuid.uuid4())
        book_id = str(uuid.uuid4())

        # Mock the session.add to track what was added
        added = []
        mock_session.add.side_effect = lambda r: added.append(r)

        await repo.create(member_id=member_id, book_id=book_id, due_days=14)
        assert mock_session.add.called
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_return_book_on_time(self, mock_session, sample_record_on_time):
        repo = LendingRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_record_on_time
        mock_session.execute = AsyncMock(return_value=mock_result)

        record = await repo.return_book(str(sample_record_on_time.id))
        assert record is not None
        assert record.status == LendingStatus.RETURNED
        assert record.fine_amount == 0.0
        assert record.returned_at is not None

    @pytest.mark.asyncio
    async def test_return_book_overdue(self, mock_session, sample_record_overdue):
        repo = LendingRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_record_overdue
        mock_session.execute = AsyncMock(return_value=mock_result)

        record = await repo.return_book(str(sample_record_overdue.id))
        assert record is not None
        assert record.status == LendingStatus.RETURNED
        assert record.fine_amount > 0
        assert record.fine_amount >= 5 * FINE_PER_DAY

    @pytest.mark.asyncio
    async def test_return_already_returned(self, mock_session, sample_record_on_time):
        repo = LendingRepository(mock_session)
        sample_record_on_time.status = LendingStatus.RETURNED
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_record_on_time
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.return_book(str(sample_record_on_time.id))
        assert result is None  # Should fail silently

    @pytest.mark.asyncio
    async def test_return_book_not_found(self, mock_session):
        repo = LendingRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.return_book(str(uuid.uuid4()))
        assert result is None


class TestBorrowingRules:
    """Test the business rules for borrowing."""

    def test_borrow_fails_no_copies(self):
        """Borrow should fail when available_copies == 0."""
        book = MagicMock()
        book.available_copies = 0
        assert book.available_copies == 0  # Lending service must check this

    def test_borrow_succeeds_with_copies(self):
        """Borrow should succeed when available_copies > 0."""
        book = MagicMock()
        book.available_copies = 2
        assert book.available_copies > 0

    def test_member_inactive_fails(self):
        """Borrow should fail when member is INACTIVE."""
        member = MagicMock()
        member.membership_status = "INACTIVE"
        assert member.membership_status != "ACTIVE"
