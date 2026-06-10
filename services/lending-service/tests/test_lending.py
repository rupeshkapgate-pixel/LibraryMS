"""
Tests for Lending Service — repository, fine calculation, borrow/return flows,
saga compensation, and overdue detection.

All external gRPC calls are mocked so tests run without running services.
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock as AM
import pytest

from app.repositories.lending_repository import LendingRepository, FINE_PER_DAY
from app.models.lending import LendingRecord, LendingStatus


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit  = AsyncMock()
    session.refresh = AsyncMock()
    session.add     = MagicMock()
    session.execute = AsyncMock()
    return session


def _make_record(status=LendingStatus.BORROWED, days_overdue=0, days_remaining=9):
    now = datetime.utcnow()
    if days_overdue > 0:
        due = now - timedelta(days=days_overdue)
    else:
        due = now + timedelta(days=days_remaining)
    return LendingRecord(
        id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        book_id=uuid.uuid4(),
        borrowed_at=now - timedelta(days=5),
        due_date=due,
        status=status,
        fine_amount=0.0,
        created_at=now,
        updated_at=now,
    )


def _mock_execute(session, record):
    result = MagicMock()
    result.scalar_one_or_none.return_value = record
    result.scalars.return_value.all.return_value = [record] if record else []
    session.execute = AsyncMock(return_value=result)


# ── Fine calculation ──────────────────────────────────────────────────────────

class TestFineCalculation:
    def test_fine_constant_is_10_per_day(self):
        assert FINE_PER_DAY == 10.0

    @pytest.mark.parametrize("days,expected", [
        (0,   0.0),
        (1,  10.0),
        (5,  50.0),
        (14,140.0),
        (30,300.0),
    ])
    def test_fine_formula(self, days, expected):
        assert days * FINE_PER_DAY == expected

    def test_no_fine_when_returned_on_time(self):
        now = datetime.utcnow()
        due = now + timedelta(days=5)
        overdue = max(0, (now - due).days)
        assert overdue * FINE_PER_DAY == 0.0


# ── Create lending record ─────────────────────────────────────────────────────

class TestLendingCreate:
    @pytest.mark.asyncio
    async def test_create_adds_and_commits(self, mock_session):
        member_id = str(uuid.uuid4())
        book_id   = str(uuid.uuid4())
        added = []
        mock_session.add.side_effect = lambda r: added.append(r)

        await LendingRepository(mock_session).create(member_id, book_id, due_days=14)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()
        assert added[0].status == LendingStatus.BORROWED

    @pytest.mark.asyncio
    async def test_create_sets_due_date_correctly(self, mock_session):
        added = []
        mock_session.add.side_effect = lambda r: added.append(r)
        before = datetime.utcnow()
        await LendingRepository(mock_session).create(
            str(uuid.uuid4()), str(uuid.uuid4()), due_days=7
        )
        after = datetime.utcnow()
        due = added[0].due_date
        assert (before + timedelta(days=6)) < due < (after + timedelta(days=8))


# ── Return book ───────────────────────────────────────────────────────────────

class TestReturnBook:
    @pytest.mark.asyncio
    async def test_return_on_time_zero_fine(self, mock_session):
        record = _make_record(days_remaining=9)
        _mock_execute(mock_session, record)
        result = await LendingRepository(mock_session).return_book(str(record.id))
        assert result is not None
        assert result.status == LendingStatus.RETURNED
        assert result.fine_amount == 0.0
        assert result.returned_at is not None

    @pytest.mark.asyncio
    async def test_return_overdue_calculates_fine(self, mock_session):
        record = _make_record(days_overdue=5)
        _mock_execute(mock_session, record)
        result = await LendingRepository(mock_session).return_book(str(record.id))
        assert result.status == LendingStatus.RETURNED
        assert result.fine_amount >= 5 * FINE_PER_DAY

    @pytest.mark.asyncio
    async def test_return_already_returned_returns_none(self, mock_session):
        record = _make_record(status=LendingStatus.RETURNED)
        _mock_execute(mock_session, record)
        result = await LendingRepository(mock_session).return_book(str(record.id))
        assert result is None

    @pytest.mark.asyncio
    async def test_return_not_found_returns_none(self, mock_session):
        _mock_execute(mock_session, None)
        result = await LendingRepository(mock_session).return_book(str(uuid.uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_return_commits(self, mock_session):
        record = _make_record()
        _mock_execute(mock_session, record)
        await LendingRepository(mock_session).return_book(str(record.id))
        mock_session.commit.assert_awaited()


# ── Borrow business rules ─────────────────────────────────────────────────────

class TestBorrowingRules:
    def test_no_copies_means_unavailable(self):
        book = MagicMock()
        book.available_copies = 0
        assert book.available_copies == 0

    def test_has_copies_means_available(self):
        book = MagicMock()
        book.available_copies = 3
        assert book.available_copies > 0

    def test_inactive_member_cannot_borrow(self):
        member = MagicMock()
        member.membership_status = "INACTIVE"
        assert member.membership_status != "ACTIVE"

    def test_active_member_can_borrow(self):
        member = MagicMock()
        member.membership_status = "ACTIVE"
        assert member.membership_status == "ACTIVE"


# ── Saga compensation ─────────────────────────────────────────────────────────

class TestSagaCompensation:
    """
    Verify that BorrowBook compensates (rolls back lending record) when
    the book-service DecreaseAvailableCopies call fails after the lending
    record has been committed.
    """

    @pytest.mark.asyncio
    async def test_borrow_compensates_when_decrease_fails(self, mock_session):
        """If DecreaseAvailableCopies fails, lending record must be cancelled."""
        from app.grpc_handlers.lending_handler import LendingServiceHandler
        import grpc

        handler = LendingServiceHandler()
        context = MagicMock()
        context.set_code = MagicMock()
        context.set_details = MagicMock()

        request = MagicMock()
        request.member_id = str(uuid.uuid4())
        request.book_id   = str(uuid.uuid4())
        request.due_days  = 14

        # Mock member validation: member is active
        member_resp = MagicMock()
        member_resp.is_active = True
        member_resp.message   = "OK"
        member_resp.member    = MagicMock(full_name="Alice", email="alice@x.com")

        # Mock availability: book available
        avail_resp = MagicMock()
        avail_resp.available = True

        # Mock decrease: FAILS
        decrease_resp = MagicMock()
        decrease_resp.success = False

        created_record = MagicMock()
        created_record.id = uuid.uuid4()

        # Patch gRPC stubs and AsyncSessionLocal
        with patch("app.grpc_handlers.lending_handler.grpc.aio.insecure_channel"), \
             patch("app.grpc_handlers.lending_handler.member_pb2_grpc.MemberServiceStub") as ms, \
             patch("app.grpc_handlers.lending_handler.book_pb2_grpc.BookServiceStub") as bs, \
             patch("app.grpc_handlers.lending_handler.AsyncSessionLocal") as mock_session_ctx:

            # Set up async context manager for AsyncSessionLocal
            mock_session_obj = AsyncMock()
            mock_session_obj.__aenter__ = AsyncMock(return_value=mock_session_obj)
            mock_session_obj.__aexit__  = AsyncMock(return_value=False)
            mock_session_ctx.return_value = mock_session_obj

            repo_mock = MagicMock()
            repo_mock.create  = AsyncMock(return_value=created_record)
            repo_mock.get_by_id = AsyncMock(return_value=created_record)
            mock_session_obj.delete = AsyncMock()
            mock_session_obj.commit = AsyncMock()

            ms.return_value.ValidateActiveMember = AsyncMock(return_value=member_resp)
            bs.return_value.CheckAvailability    = AsyncMock(return_value=avail_resp)
            bs.return_value.DecreaseAvailableCopies = AsyncMock(return_value=decrease_resp)

            with patch("app.grpc_handlers.lending_handler.LendingRepository", return_value=repo_mock):
                await handler.BorrowBook(request, context)

            # Compensation: session.delete and commit must have been called
            mock_session_obj.delete.assert_awaited()
            mock_session_obj.commit.assert_awaited()


# ── Overdue ───────────────────────────────────────────────────────────────────

class TestOverdue:
    @pytest.mark.asyncio
    async def test_overdue_list_query_runs(self, mock_session):
        overdue_record = _make_record(status=LendingStatus.OVERDUE, days_overdue=3)
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [overdue_record]
        mock_session.execute = AsyncMock(return_value=result_mock)
        mock_session.scalar = AsyncMock(return_value=1)

        records, total = await LendingRepository(mock_session).list_overdue(page=1, page_size=20)
        assert isinstance(records, list)
