"""
Tests for API Gateway — Pydantic schema validation and gRPC→HTTP error mapping.

These tests run without starting any services.
"""
import pytest
import pydantic

from app.schemas.schemas import (
    BookCreate, BookUpdate, MemberCreate, MemberUpdate,
    BorrowRequest, ReturnRequest,
)


# ── Book schemas ──────────────────────────────────────────────────────────────

class TestBookCreate:
    def test_valid_minimal(self):
        b = BookCreate(title="T", author="A", isbn="1234567890", total_copies=1)
        assert b.title == "T"

    def test_valid_full(self):
        b = BookCreate(
            title="Clean Code", author="Robert C. Martin",
            isbn="9780132350884", publisher="Prentice Hall",
            category="Technology", description="A guide",
            published_year=2008, total_copies=5, shelf_location="A1",
        )
        assert b.published_year == 2008

    def test_empty_title_invalid(self):
        with pytest.raises(pydantic.ValidationError):
            BookCreate(title="", author="A", isbn="1234567890", total_copies=1)

    def test_empty_author_invalid(self):
        with pytest.raises(pydantic.ValidationError):
            BookCreate(title="T", author="", isbn="1234567890", total_copies=1)

    def test_isbn_too_short(self):
        with pytest.raises(pydantic.ValidationError):
            BookCreate(title="T", author="A", isbn="123", total_copies=1)

    def test_isbn_too_long(self):
        with pytest.raises(pydantic.ValidationError):
            BookCreate(title="T", author="A", isbn="1" * 21, total_copies=1)

    def test_zero_copies_invalid(self):
        with pytest.raises(pydantic.ValidationError):
            BookCreate(title="T", author="A", isbn="1234567890", total_copies=0)

    def test_year_too_early_invalid(self):
        with pytest.raises(pydantic.ValidationError):
            BookCreate(title="T", author="A", isbn="1234567890", total_copies=1, published_year=999)

    def test_year_too_late_invalid(self):
        with pytest.raises(pydantic.ValidationError):
            BookCreate(title="T", author="A", isbn="1234567890", total_copies=1, published_year=2200)


class TestBookUpdate:
    def test_all_fields_optional(self):
        b = BookUpdate()
        assert b.title is None

    def test_partial_update_valid(self):
        b = BookUpdate(shelf_location="B2")
        assert b.shelf_location == "B2"


# ── Member schemas ────────────────────────────────────────────────────────────

class TestMemberCreate:
    def test_valid_member(self):
        m = MemberCreate(full_name="Priya Sharma", email="priya@example.com")
        assert m.email == "priya@example.com"

    def test_invalid_email_no_at(self):
        with pytest.raises(pydantic.ValidationError):
            MemberCreate(full_name="X", email="notanemail")

    def test_invalid_email_no_domain(self):
        with pytest.raises(pydantic.ValidationError):
            MemberCreate(full_name="X", email="x@")

    def test_empty_name_invalid(self):
        with pytest.raises(pydantic.ValidationError):
            MemberCreate(full_name="", email="x@example.com")

    def test_optional_fields(self):
        m = MemberCreate(full_name="X", email="x@example.com", phone="999", address="Pune")
        assert m.phone == "999"


class TestMemberUpdate:
    def test_all_fields_optional(self):
        m = MemberUpdate()
        assert m.full_name is None


# ── Lending schemas ───────────────────────────────────────────────────────────

class TestBorrowRequest:
    def test_valid_borrow(self):
        r = BorrowRequest(member_id="a" * 36, book_id="b" * 36, due_days=14)
        assert r.due_days == 14

    def test_default_due_days_is_14(self):
        r = BorrowRequest(member_id="a" * 36, book_id="b" * 36)
        assert r.due_days == 14

    def test_due_days_above_365_invalid(self):
        with pytest.raises(pydantic.ValidationError):
            BorrowRequest(member_id="a" * 36, book_id="b" * 36, due_days=366)

    def test_due_days_zero_invalid(self):
        with pytest.raises(pydantic.ValidationError):
            BorrowRequest(member_id="a" * 36, book_id="b" * 36, due_days=0)


class TestReturnRequest:
    def test_valid_return(self):
        r = ReturnRequest(lending_id="a" * 36)
        assert len(r.lending_id) == 36


# ── gRPC → HTTP error mapping ─────────────────────────────────────────────────

class TestGrpcErrorMapping:
    """
    Verify that the gateway maps gRPC status codes to the correct HTTP codes
    and returns the standardized error format.
    """

    def test_not_found_maps_to_404(self):
        import grpc
        from app.routers.books import grpc_error_to_http
        err = MagicMock()
        err.code    = lambda: grpc.StatusCode.NOT_FOUND
        err.details = lambda: "Book not found"

        class MagicMock:
            pass

        import unittest.mock
        err = unittest.mock.MagicMock()
        err.code    = lambda: grpc.StatusCode.NOT_FOUND
        err.details = lambda: "Book not found"

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            grpc_error_to_http(err)
        assert exc_info.value.status_code == 404

    def test_already_exists_maps_to_409(self):
        import grpc, unittest.mock
        from app.routers.books import grpc_error_to_http
        from fastapi import HTTPException
        err = unittest.mock.MagicMock()
        err.code    = lambda: grpc.StatusCode.ALREADY_EXISTS
        err.details = lambda: "duplicate"
        with pytest.raises(HTTPException) as exc_info:
            grpc_error_to_http(err)
        assert exc_info.value.status_code == 409

    def test_failed_precondition_maps_to_400(self):
        import grpc, unittest.mock
        from app.routers.books import grpc_error_to_http
        from fastapi import HTTPException
        err = unittest.mock.MagicMock()
        err.code    = lambda: grpc.StatusCode.FAILED_PRECONDITION
        err.details = lambda: "no copies"
        with pytest.raises(HTTPException) as exc_info:
            grpc_error_to_http(err)
        assert exc_info.value.status_code == 400

    def test_internal_maps_to_500(self):
        import grpc, unittest.mock
        from app.routers.books import grpc_error_to_http
        from fastapi import HTTPException
        err = unittest.mock.MagicMock()
        err.code    = lambda: grpc.StatusCode.INTERNAL
        err.details = lambda: "server error"
        with pytest.raises(HTTPException) as exc_info:
            grpc_error_to_http(err)
        assert exc_info.value.status_code == 500
