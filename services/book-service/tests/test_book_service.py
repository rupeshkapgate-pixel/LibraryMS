"""Tests for BookService — service layer with transaction management and locking."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import pytest

from services.book_service.app.repositories.book_repository import BookRepository
from services.book_service.app.models.book import Book


@pytest.fixture
def mock_session():
    session = AsyncMock()
    # Make session.begin() work as an async context manager
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=cm)
    cm.__aexit__ = AsyncMock(return_value=False)
    session.begin = MagicMock(return_value=cm)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def sample_book():
    return Book(
        id=uuid.uuid4(),
        title="Refactoring",
        author="Martin Fowler",
        isbn="9780201485677",
        publisher="Addison-Wesley",
        category="Technology",
        total_copies=5,
        available_copies=3,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestBookRepositoryLocking:
    """Verify that copy-mutation methods use SELECT FOR UPDATE."""

    @pytest.mark.asyncio
    async def test_get_by_id_for_update_issues_lock(self, mock_session, sample_book):
        """get_by_id_for_update must emit WITH FOR UPDATE."""
        repo = BookRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        book = await repo.get_by_id_for_update(str(sample_book.id))
        assert book is not None

        # Verify .with_for_update() appeared in the compiled query
        call_args = mock_session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "FOR UPDATE" in compiled

    @pytest.mark.asyncio
    async def test_decrease_copies_uses_lock(self, mock_session, sample_book):
        """decrease_available_copies must acquire a row lock before mutating."""
        repo = BookRepository(mock_session)
        sample_book.available_copies = 3

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.decrease_available_copies(str(sample_book.id), 1)
        assert result is not None
        assert result.available_copies == 2

        call_args = mock_session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "FOR UPDATE" in compiled

    @pytest.mark.asyncio
    async def test_decrease_copies_prevents_over_borrow(self, mock_session, sample_book):
        """Cannot decrease below zero — returns None."""
        repo = BookRepository(mock_session)
        sample_book.available_copies = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.decrease_available_copies(str(sample_book.id), 1)
        assert result is None

    @pytest.mark.asyncio
    async def test_increase_copies_capped_at_total(self, mock_session, sample_book):
        """Increasing beyond total_copies is capped."""
        repo = BookRepository(mock_session)
        sample_book.available_copies = 5
        sample_book.total_copies = 5

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.increase_available_copies(str(sample_book.id), 2)
        assert result is not None
        assert result.available_copies == 5  # capped at total


class TestBookRepositoryNoCommit:
    """Verify no-commit helpers flush but do not commit."""

    @pytest.mark.asyncio
    async def test_create_no_commit_does_not_commit(self, mock_session):
        repo = BookRepository(mock_session)
        data = {"title": "Test", "author": "A", "isbn": "1234567890", "total_copies": 2}

        await repo.create_no_commit(data)
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        mock_session.commit.assert_not_awaited()


class TestFineCalculation:
    """Fine logic unit tests — pure arithmetic, no DB."""

    def test_fine_for_5_days(self):
        from services.lending_service.app.repositories.lending_repository import FINE_PER_DAY
        assert FINE_PER_DAY * 5 == 50.0

    def test_fine_for_0_days(self):
        from services.lending_service.app.repositories.lending_repository import FINE_PER_DAY
        assert FINE_PER_DAY * 0 == 0.0

    def test_fine_per_day_is_10(self):
        from services.lending_service.app.repositories.lending_repository import FINE_PER_DAY
        assert FINE_PER_DAY == 10.0
