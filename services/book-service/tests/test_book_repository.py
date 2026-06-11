"""Tests for Book Service."""
import sys
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
    session.delete = AsyncMock()
    return session


@pytest.fixture
def sample_book():
    return Book(
        id=uuid.uuid4(),
        title="Clean Code",
        author="Robert C. Martin",
        isbn="9780132350884",
        publisher="Prentice Hall",
        category="Technology",
        description="A handbook of agile software craftsmanship",
        published_year=2008,
        total_copies=5,
        available_copies=3,
        shelf_location="A1-01",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestBookRepository:
    @pytest.mark.asyncio
    async def test_create_book(self, mock_session):
        repo = BookRepository(mock_session)
        data = {
            "title": "Test Book",
            "author": "Test Author",
            "isbn": "1234567890",
            "total_copies": 3,
        }

        added_books = []
        mock_session.add.side_effect = lambda book: added_books.append(book)

        book = await repo.create(data)

        assert book is not None
        assert book.title == data["title"]
        assert book.author == data["author"]
        assert book.isbn == data["isbn"]
        assert book.total_copies == 3
        assert book.available_copies == 3
        mock_session.begin.assert_called_once()
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
        mock_session.commit.assert_not_awaited()
        assert added_books == [book]

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_session, sample_book):
        repo = BookRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        book = await repo.get_by_id(str(sample_book.id))

        assert book is not None
        assert book.title == sample_book.title

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_session):
        repo = BookRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        book = await repo.get_by_id(str(uuid.uuid4()))

        assert book is None

    @pytest.mark.asyncio
    async def test_soft_delete(self, mock_session, sample_book):
        repo = BookRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.soft_delete(str(sample_book.id))

        assert result is True
        assert sample_book.deleted_at is not None
        mock_session.begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_soft_delete_not_found(self, mock_session):
        repo = BookRepository(mock_session)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await repo.soft_delete(str(uuid.uuid4()))

        assert result is False
        mock_session.begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_decrease_copies_success(self, mock_session, sample_book):
        repo = BookRepository(mock_session)
        original_available = sample_book.available_copies
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        book = await repo.decrease_available_copies(str(sample_book.id), 1)

        assert book is not None
        assert book.available_copies == original_available - 1
        mock_session.begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_decrease_copies_insufficient(self, mock_session, sample_book):
        repo = BookRepository(mock_session)
        sample_book.available_copies = 0
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        book = await repo.decrease_available_copies(str(sample_book.id), 1)

        assert book is None
        assert sample_book.available_copies == 0
        mock_session.begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_increase_copies(self, mock_session, sample_book):
        repo = BookRepository(mock_session)
        sample_book.available_copies = 2
        sample_book.total_copies = 5
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        book = await repo.increase_available_copies(str(sample_book.id), 1)

        assert book is not None
        assert book.available_copies == 3
        mock_session.begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_increase_copies_capped_at_total(self, mock_session, sample_book):
        repo = BookRepository(mock_session)
        sample_book.available_copies = 5
        sample_book.total_copies = 5
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_book
        mock_session.execute = AsyncMock(return_value=mock_result)

        book = await repo.increase_available_copies(str(sample_book.id), 1)

        assert book is not None
        assert book.available_copies == 5
        mock_session.begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_books(self, mock_session, sample_book):
        repo = BookRepository(mock_session)
        books_result = MagicMock()
        books_result.scalars.return_value.all.return_value = [sample_book]
        mock_session.scalar = AsyncMock(return_value=1)
        mock_session.execute = AsyncMock(return_value=books_result)

        books, total = await repo.list_books(page=1, page_size=20)

        assert books == [sample_book]
        assert total == 1
