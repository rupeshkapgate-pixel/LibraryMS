"""Tests for Book Service — repository, business rules, fine calculation."""
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.repositories.book_repository import BookRepository
from app.models.book import Book


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit  = AsyncMock()
    session.refresh = AsyncMock()
    session.add     = MagicMock()
    session.delete  = AsyncMock()
    session.execute = AsyncMock()
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


def _mock_execute(session, return_value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = return_value
    result.scalars.return_value.all.return_value = [return_value] if return_value else []
    session.execute = AsyncMock(return_value=result)
    return result


# ── Create ────────────────────────────────────────────────────────────────────

class TestBookCreate:
    @pytest.mark.asyncio
    async def test_create_adds_and_commits(self, mock_session):
        repo = BookRepository(mock_session)
        await repo.create({"title": "T", "author": "A", "isbn": "1234567890", "total_copies": 2})
        mock_session.add.assert_called_once()
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_sets_available_copies_to_total(self, mock_session):
        added = []
        mock_session.add.side_effect = lambda b: added.append(b)
        repo = BookRepository(mock_session)
        await repo.create({"title": "T", "author": "A", "isbn": "1234567890", "total_copies": 4})
        assert added[0].total_copies == 4
        assert added[0].available_copies == 4

    @pytest.mark.asyncio
    async def test_create_defaults_total_copies_to_1(self, mock_session):
        added = []
        mock_session.add.side_effect = lambda b: added.append(b)
        repo = BookRepository(mock_session)
        await repo.create({"title": "T", "author": "A", "isbn": "1234567890"})
        assert added[0].total_copies == 1
        assert added[0].available_copies == 1


# ── Get ───────────────────────────────────────────────────────────────────────

class TestBookGet:
    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_session, sample_book):
        _mock_execute(mock_session, sample_book)
        book = await BookRepository(mock_session).get_by_id(str(sample_book.id))
        assert book is not None
        assert book.title == "Clean Code"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_session):
        _mock_execute(mock_session, None)
        book = await BookRepository(mock_session).get_by_id(str(uuid.uuid4()))
        assert book is None


# ── Update ────────────────────────────────────────────────────────────────────

class TestBookUpdate:
    @pytest.mark.asyncio
    async def test_update_existing_book(self, mock_session, sample_book):
        _mock_execute(mock_session, sample_book)
        repo = BookRepository(mock_session)
        result = await repo.update(str(sample_book.id), {"shelf_location": "Z9-99"})
        assert result is not None
        assert result.shelf_location == "Z9-99"
        mock_session.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_none(self, mock_session):
        _mock_execute(mock_session, None)
        result = await BookRepository(mock_session).update(str(uuid.uuid4()), {"title": "X"})
        assert result is None


# ── Delete ────────────────────────────────────────────────────────────────────

class TestBookDelete:
    @pytest.mark.asyncio
    async def test_soft_delete_sets_deleted_at(self, mock_session, sample_book):
        _mock_execute(mock_session, sample_book)
        ok = await BookRepository(mock_session).soft_delete(str(sample_book.id))
        assert ok is True
        assert sample_book.deleted_at is not None

    @pytest.mark.asyncio
    async def test_soft_delete_not_found(self, mock_session):
        _mock_execute(mock_session, None)
        ok = await BookRepository(mock_session).soft_delete(str(uuid.uuid4()))
        assert ok is False


# ── Availability mutations ────────────────────────────────────────────────────

class TestBookAvailability:
    @pytest.mark.asyncio
    async def test_decrease_copies_success(self, mock_session, sample_book):
        _mock_execute(mock_session, sample_book)
        original = sample_book.available_copies
        result = await BookRepository(mock_session).decrease_available_copies(str(sample_book.id), 1)
        assert result is not None
        assert result.available_copies == original - 1

    @pytest.mark.asyncio
    async def test_decrease_copies_insufficient_returns_none(self, mock_session, sample_book):
        sample_book.available_copies = 0
        _mock_execute(mock_session, sample_book)
        result = await BookRepository(mock_session).decrease_available_copies(str(sample_book.id), 1)
        assert result is None

    @pytest.mark.asyncio
    async def test_increase_copies(self, mock_session, sample_book):
        sample_book.available_copies = 2
        sample_book.total_copies = 5
        _mock_execute(mock_session, sample_book)
        result = await BookRepository(mock_session).increase_available_copies(str(sample_book.id), 1)
        assert result is not None
        assert result.available_copies == 3

    @pytest.mark.asyncio
    async def test_increase_copies_capped_at_total(self, mock_session, sample_book):
        sample_book.available_copies = 5
        sample_book.total_copies = 5
        _mock_execute(mock_session, sample_book)
        result = await BookRepository(mock_session).increase_available_copies(str(sample_book.id), 2)
        assert result.available_copies == 5  # cannot exceed total_copies


# ── List / Search ─────────────────────────────────────────────────────────────

class TestBookList:
    @pytest.mark.asyncio
    async def test_list_returns_books_and_count(self, mock_session, sample_book):
        result = MagicMock()
        result.scalars.return_value.all.return_value = [sample_book]
        mock_session.execute = AsyncMock(return_value=result)
        mock_session.scalar = AsyncMock(return_value=1)
        books, total = await BookRepository(mock_session).list_books(page=1, page_size=20)
        assert isinstance(books, list)
        assert total == 1

    @pytest.mark.asyncio
    async def test_list_empty_database(self, mock_session):
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result)
        mock_session.scalar = AsyncMock(return_value=0)
        books, total = await BookRepository(mock_session).list_books(page=1, page_size=20)
        assert books == []
        assert total == 0
