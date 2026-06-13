"""
LendingService — distributed saga orchestration and local transaction management.

The service layer owns all lending business rules, transaction boundaries and
book/member-service orchestration. gRPC handlers must delegate here instead of
implementing business logic directly.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, time as dt_time
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from app.grpc_clients import get_book_stub, get_member_stub
from app.models.lending import LendingRecord, LendingStatus
from app.proto_generated import book_pb2, member_pb2
from app.repositories.lending_repository import FINE_PER_DAY, LendingRepository
from app.telemetry.setup import DB_QUERY_COUNTER, DB_QUERY_LATENCY, make_grpc_metadata_with_trace

logger = logging.getLogger(__name__)
_SVC = "lending-service"
DEFAULT_DUE_DAYS = 14


def _parse_datetime_bound(value: Optional[str], *, end_of_day: bool = False) -> Optional[datetime]:
    if not value:
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid date/datetime filter: {value}") from exc
    if parsed.tzinfo:
        parsed = parsed.astimezone().replace(tzinfo=None)
    if "T" not in normalized and len(normalized) == 10:
        parsed = datetime.combine(parsed.date(), dt_time.max if end_of_day else dt_time.min)
    return parsed


class LendingService:
    """Orchestrates borrow/return workflows across local DB and gRPC services."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = LendingRepository(session)

    async def borrow_book(
        self,
        member_id: str,
        book_id: str,
        due_days: int = DEFAULT_DUE_DAYS,
    ) -> LendingRecord:
        t0 = time.perf_counter()
        try:
            if due_days <= 0:
                raise ValueError("due_days must be greater than zero")
            await self._validate_member(member_id)
            await self._validate_book(book_id)

            record = await self._repo.create_no_commit(member_id=member_id, book_id=book_id, due_days=due_days)
            await self._session.commit()
            await self._session.refresh(record)

            logger.info("Lending record created id=%s member=%s book=%s", record.id, member_id, book_id)

            try:
                await self._decrease_book_copies(book_id)
            except Exception as exc:
                logger.error(
                    "DecreaseAvailableCopies failed — compensating: cancel record %s. err=%s",
                    record.id,
                    exc,
                )
                await self._cancel_lending_record(str(record.id))
                raise RuntimeError("Failed to decrease available copies; lending record cancelled.") from exc

            DB_QUERY_COUNTER.labels(service=_SVC, operation="borrow", status="ok").inc()
            return record

        except (ValueError, PermissionError, LookupError):
            await self._session.rollback()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="borrow", status="validation_error").inc()
            raise
        except Exception:
            await self._session.rollback()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="borrow", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="borrow").observe(time.perf_counter() - t0)

    async def return_book(self, lending_id: str) -> Tuple[LendingRecord, float, bool, int]:
        """Return a book using a row-level lock so concurrent returns are idempotent."""
        t0 = time.perf_counter()
        try:
            record = await self._repo.get_by_id_for_update(lending_id)
            if not record:
                raise LookupError(f"Lending record {lending_id} not found")
            if record.status == LendingStatus.RETURNED:
                raise ValueError("Book already returned")

            now = datetime.utcnow()
            overdue_days = max(0, (now - record.due_date).days) if now > record.due_date else 0
            fine_amount = overdue_days * FINE_PER_DAY

            record.returned_at = now
            record.updated_at = now
            record.status = LendingStatus.RETURNED
            record.fine_amount = fine_amount
            book_id = str(record.book_id)

            await self._session.commit()
            await self._session.refresh(record)

            try:
                await self._increase_book_copies(book_id)
            except Exception as exc:
                logger.warning(
                    "IncreaseAvailableCopies failed for book=%s after return=%s: %s",
                    book_id,
                    lending_id,
                    exc,
                )

            DB_QUERY_COUNTER.labels(service=_SVC, operation="return", status="ok").inc()
            return record, fine_amount, fine_amount > 0, overdue_days

        except (LookupError, ValueError):
            await self._session.rollback()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="return", status="validation_error").inc()
            raise
        except Exception:
            await self._session.rollback()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="return", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="return").observe(time.perf_counter() - t0)

    async def list_borrowed(
        self,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        query: Optional[str] = None,
        member_id: Optional[str] = None,
        book_id: Optional[str] = None,
        status: Optional[LendingStatus] = None,
        due_from: Optional[str] = None,
        due_to: Optional[str] = None,
    ) -> Tuple[List[LendingRecord], int]:
        return await self._repo.list_borrowed_books(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            query=query,
            member_id=member_id,
            book_id=book_id,
            status=status,
            due_from=_parse_datetime_bound(due_from),
            due_to=_parse_datetime_bound(due_to, end_of_day=True),
        )

    async def list_by_member(
        self,
        member_id: str,
        page: int,
        page_size: int,
    ) -> Tuple[List[LendingRecord], int]:
        return await self._repo.list_by_member(member_id, page, page_size)

    async def list_by_book(
        self,
        book_id: str,
        page: int,
        page_size: int,
    ) -> Tuple[List[LendingRecord], int]:
        return await self._repo.list_by_book(book_id, page, page_size)

    async def list_overdue(
        self,
        page: int,
        page_size: int,
        query: Optional[str] = None,
        member_id: Optional[str] = None,
        book_id: Optional[str] = None,
        due_from: Optional[str] = None,
        due_to: Optional[str] = None,
    ) -> Tuple[List[LendingRecord], int]:
        return await self._repo.list_overdue(
            page,
            page_size,
            query=query,
            member_id=member_id,
            book_id=book_id,
            due_from=_parse_datetime_bound(due_from),
            due_to=_parse_datetime_bound(due_to, end_of_day=True),
        )

    async def _validate_member(self, member_id: str) -> Tuple[str, str]:
        resp = await get_member_stub().ValidateActiveMember(
            member_pb2.ValidateActiveMemberRequest(member_id=member_id),
            timeout=10,
            metadata=make_grpc_metadata_with_trace(),
        )
        if not resp.is_active:
            raise PermissionError(resp.message or "Member is not active")
        return resp.member.full_name, resp.member.email

    async def _validate_book(self, book_id: str) -> None:
        resp = await get_book_stub().CheckAvailability(
            book_pb2.CheckAvailabilityRequest(book_id=book_id),
            timeout=10,
            metadata=make_grpc_metadata_with_trace(),
        )
        if not resp.available:
            raise ValueError("No available copies of this book")

    async def _decrease_book_copies(self, book_id: str) -> None:
        resp = await get_book_stub().DecreaseAvailableCopies(
            book_pb2.UpdateCopiesRequest(book_id=book_id, count=1),
            timeout=10,
            metadata=make_grpc_metadata_with_trace(),
        )
        if not resp.success:
            raise RuntimeError("DecreaseAvailableCopies returned success=False")

    async def _increase_book_copies(self, book_id: str) -> None:
        resp = await get_book_stub().IncreaseAvailableCopies(
            book_pb2.UpdateCopiesRequest(book_id=book_id, count=1),
            timeout=10,
            metadata=make_grpc_metadata_with_trace(),
        )
        if not resp.success:
            raise RuntimeError("IncreaseAvailableCopies returned success=False")

    async def _cancel_lending_record(self, lending_id: str) -> None:
        """Compensating action: mark a committed lending record as returned/cancelled."""
        try:
            record = await self._repo.get_by_id_for_update(lending_id)
            if record:
                now = datetime.utcnow()
                record.status = LendingStatus.RETURNED
                record.returned_at = now
                record.fine_amount = 0.0
                record.updated_at = now
                await self._session.commit()
            else:
                await self._session.rollback()
        except Exception as exc:
            await self._session.rollback()
            logger.error("Compensating cancel failed for %s: %s", lending_id, exc)
