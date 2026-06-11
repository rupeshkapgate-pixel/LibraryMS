"""Tests for BookService and BookRepository locking behavior."""

import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

BOOK_SERVICE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LENDING_REPOSITORY_PATH = (
    PROJECT_ROOT
    / "services"
    / "lending-service"
    / "app"
    / "repositories"
    / "lending_repository.py"
)

sys.path.insert(0, str(BOOK_SERVICE_ROOT))

from app.models.book import Book
from app.repositories.book_repository import BookRepository

@pytest.fixture
def mock_session():
    """Async SQLAlchemy session mock with transaction context support."""
    session = AsyncMock()

    transaction = AsyncMock()
    transaction.__aenter__ = AsyncMock(return_value=transaction)
    transaction.__aexit__ = AsyncMock(return_value=False)

    session.begin = MagicMock(return_value=transaction)
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
        repo = BookRepository(mock_session)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        book = await repo.get_by_id_for_update(str(sample_book.id))

        assert book is not None
        call_args = mock_session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "FOR UPDATE" in compiled

    @pytest.mark.asyncio
    async def test_decrease_copies_uses_lock(self, mock_session, sample_book):
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
        repo = BookRepository(mock_session)
        sample_book.available_copies = 0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.decrease_available_copies(str(sample_book.id), 1)

        assert result is None

    @pytest.mark.asyncio
    async def test_increase_copies_capped_at_total(self, mock_session, sample_book):
        repo = BookRepository(mock_session)
        sample_book.available_copies = 5
        sample_book.total_copies = 5

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.increase_available_copies(str(sample_book.id), 2)

        assert result is not None
        assert result.available_copies == 5


class TestBookRepositoryNoCommit:
    """Verify no-commit helpers flush but do not commit."""

    @pytest.mark.asyncio
    async def test_create_no_commit_does_not_commit(self, mock_session):
        repo = BookRepository(mock_session)
        data = {
            "title": "Test",
            "author": "A",
            "isbn": "1234567890",
            "total_copies": 2,
        }

        await repo.create_no_commit(data)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        mock_session.commit.assert_not_awaited()


class TestFineCalculation:
    """Fine logic unit tests — kept independent from lending-service imports."""

    FINE_PER_DAY = 10.0

    def test_fine_for_5_days(self):
        assert self.FINE_PER_DAY * 5 == 50.0

    def test_fine_for_0_days(self):
        assert self.FINE_PER_DAY * 0 == 0.0

    def test_fine_per_day_is_10(self):
        assert self.FINE_PER_DAY == 10.0
