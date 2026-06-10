"""Tests for API Gateway REST endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# We test schemas and validation logic
from services.api_gateway.app.schemas.schemas import (
    BookCreate, BookUpdate, MemberCreate, BorrowRequest, ReturnRequest
)
import pydantic


class TestBookSchemas:
    def test_valid_book_create(self):
        book = BookCreate(
            title="The Pragmatic Programmer",
            author="David Thomas",
            isbn="9780135957059",
            total_copies=3,
        )
        assert book.title == "The Pragmatic Programmer"

    def test_invalid_book_no_title(self):
        with pytest.raises(pydantic.ValidationError):
            BookCreate(title="", author="A", isbn="1234567890", total_copies=1)

    def test_invalid_isbn_too_short(self):
        with pytest.raises(pydantic.ValidationError):
            BookCreate(title="T", author="A", isbn="123", total_copies=1)

    def test_invalid_total_copies_zero(self):
        with pytest.raises(pydantic.ValidationError):
            BookCreate(title="T", author="A", isbn="1234567890", total_copies=0)

    def test_valid_published_year(self):
        book = BookCreate(
            title="T", author="A", isbn="1234567890", total_copies=1, published_year=2020
        )
        assert book.published_year == 2020

    def test_invalid_published_year_too_early(self):
        with pytest.raises(pydantic.ValidationError):
            BookCreate(title="T", author="A", isbn="1234567890", total_copies=1, published_year=500)


class TestMemberSchemas:
    def test_valid_member_create(self):
        m = MemberCreate(full_name="Priya Sharma", email="priya@example.com")
        assert m.email == "priya@example.com"

    def test_invalid_email(self):
        with pytest.raises(pydantic.ValidationError):
            MemberCreate(full_name="Test", email="not-an-email")

    def test_empty_name(self):
        with pytest.raises(pydantic.ValidationError):
            MemberCreate(full_name="", email="t@test.com")


class TestLendingSchemas:
    def test_valid_borrow_request(self):
        r = BorrowRequest(
            member_id="a" * 36,
            book_id="b" * 36,
            due_days=14,
        )
        assert r.due_days == 14

    def test_invalid_borrow_due_days_too_long(self):
        with pytest.raises(pydantic.ValidationError):
            BorrowRequest(member_id="a" * 36, book_id="b" * 36, due_days=400)

    def test_default_due_days(self):
        r = BorrowRequest(member_id="a" * 36, book_id="b" * 36)
        assert r.due_days == 14

    def test_valid_return_request(self):
        r = ReturnRequest(lending_id="a" * 36)
        assert len(r.lending_id) == 36
