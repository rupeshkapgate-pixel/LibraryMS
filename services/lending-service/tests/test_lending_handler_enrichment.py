"""Tests for UI display enrichment in Lending gRPC handler."""
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))
sys.path.insert(0, str(SERVICE_ROOT / "app" / "proto_generated"))

from app.grpc_handlers import lending_handler
from app.models.lending import LendingRecord, LendingStatus


@pytest.fixture
def borrowed_record():
    now = datetime.utcnow()
    return LendingRecord(
        id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        book_id=uuid.uuid4(),
        borrowed_at=now - timedelta(days=1),
        due_date=now + timedelta(days=13),
        status=LendingStatus.BORROWED,
        fine_amount=0.0,
        created_at=now,
        updated_at=now,
    )


def test_record_to_proto_includes_book_and_member_display_fields(borrowed_record):
    proto_record = lending_handler._record_to_proto(
        borrowed_record,
        book_title="Clean Code",
        book_isbn="9780132350884",
        member_name="Rohit Sharma",
        member_email="rohit.sharma@example.com",
    )

    assert proto_record.book_title == "Clean Code"
    assert proto_record.book_isbn == "9780132350884"
    assert proto_record.member_name == "Rohit Sharma"
    assert proto_record.member_email == "rohit.sharma@example.com"


@pytest.mark.asyncio
async def test_safe_get_book_details_returns_display_values():
    fake_book = type("Book", (), {"title": "Clean Code", "isbn": "9780132350884"})()
    fake_stub = type("BookStub", (), {"GetBook": AsyncMock(return_value=fake_book)})()

    title, isbn = await lending_handler._safe_get_book_details(fake_stub, str(uuid.uuid4()))

    assert title == "Clean Code"
    assert isbn == "9780132350884"


@pytest.mark.asyncio
async def test_safe_get_member_details_returns_display_values():
    fake_member = type("Member", (), {"full_name": "Rohit Sharma", "email": "rohit.sharma@example.com"})()
    fake_stub = type("MemberStub", (), {"GetMember": AsyncMock(return_value=fake_member)})()

    name, email = await lending_handler._safe_get_member_details(fake_stub, str(uuid.uuid4()))

    assert name == "Rohit Sharma"
    assert email == "rohit.sharma@example.com"
