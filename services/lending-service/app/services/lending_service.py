"""
LendingService — distributed saga orchestration and local transaction management.

The service uses explicit commit()/rollback() instead of `async with session.begin()`.
SQLAlchemy AsyncSession auto-begins a transaction on SELECT; explicit transaction
blocks can therefore fail with "A transaction is already begun on this Session"
when a prior read has already opened a transaction.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import List, Tuple

import grpc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lending import LendingRecord, LendingStatus
from app.proto_generated import book_pb2, book_pb2_grpc, member_pb2, member_pb2_grpc
from app.repositories.lending_repository import FINE_PER_DAY, LendingRepository
from app.telemetry.setup import DB_QUERY_COUNTER, DB_QUERY_LATENCY

logger = logging.getLogger(__name__)
_SVC = "lending-service"

BOOK_SERVICE_ADDR = f"{os.getenv('BOOK_SERVICE_HOST', 'localhost')}:{os.getenv('BOOK_SERVICE_PORT', '50051')}"
MEMBER_SERVICE_ADDR = f"{os.getenv('MEMBER_SERVICE_HOST', 'localhost')}:{os.getenv('MEMBER_SERVICE_PORT', '50052')}"

DEFAULT_DUE_DAYS = 14


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
            await self._validate_member(member_id)
            await self._validate_book(book_id)

            record = await self._repo.create_no_commit(
                member_id=member_id,
                book_id=book_id,
                due_days=due_days,
            )
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
                raise RuntimeError(
                    "Failed to decrease available copies; lending record cancelled."
                ) from exc

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
            DB_QUERY_LATENCY.labels(service=_SVC, operation="borrow").observe(
                time.perf_counter() - t0
            )

    async def return_book(self, lending_id: str) -> Tuple[LendingRecord, float, bool, int]:
        """Return a book and calculate fine using a row-level lock."""
        t0 = time.perf_counter()
        try:
            record = await self._repo.get_by_id_for_update(lending_id)
            if not record:
                raise LookupError(f"Lending record {lending_id} not found")
            if record.status == LendingStatus.RETURNED:
                raise ValueError("Book already returned")

            now = datetime.utcnow()
            record.returned_at = now
            record.updated_at = now
            record.status = LendingStatus.RETURNED

            overdue_days = 0
            fine_amount = 0.0
            if now > record.due_date:
                overdue_days = max(0, (now - record.due_date).days)
                fine_amount = overdue_days * FINE_PER_DAY

            record.fine_amount = fine_amount
            book_id = str(record.book_id)
            is_overdue = fine_amount > 0

            await self._session.commit()
            await self._session.refresh(record)

            try:
                await self._increase_book_copies(book_id)
            except Exception as exc:
                logger.warning(
                    "IncreaseAvailableCopies failed for book=%s (non-fatal, retry possible): %s",
                    book_id,
                    exc,
                )

            logger.info(
                "Book returned: record=%s fine=%.2f overdue_days=%d",
                lending_id,
                fine_amount,
                overdue_days,
            )
            DB_QUERY_COUNTER.labels(service=_SVC, operation="return", status="ok").inc()
            return record, fine_amount, is_overdue, overdue_days

        except (LookupError, ValueError):
            await self._session.rollback()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="return", status="validation_error").inc()
            raise
        except Exception:
            await self._session.rollback()
            DB_QUERY_COUNTER.labels(service=_SVC, operation="return", status="error").inc()
            raise
        finally:
            DB_QUERY_LATENCY.labels(service=_SVC, operation="return").observe(
                time.perf_counter() - t0
            )

    async def list_borrowed(
        self,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
    ) -> Tuple[List[LendingRecord], int]:
        return await self._repo.list_borrowed_books(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
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

    async def list_overdue(self, page: int, page_size: int) -> Tuple[List[LendingRecord], int]:
        return await self._repo.list_overdue(page, page_size)

    async def _validate_member(self, member_id: str) -> Tuple[str, str]:
        channel = grpc.aio.insecure_channel(MEMBER_SERVICE_ADDR)
        stub = member_pb2_grpc.MemberServiceStub(channel)
        try:
            resp = await stub.ValidateActiveMember(
                member_pb2.ValidateActiveMemberRequest(member_id=member_id),
                timeout=10,
            )
        finally:
            await channel.close()

        if not resp.is_active:
            raise PermissionError(resp.message or "Member is not active")
        return resp.member.full_name, resp.member.email

    async def _validate_book(self, book_id: str) -> None:
        channel = grpc.aio.insecure_channel(BOOK_SERVICE_ADDR)
        stub = book_pb2_grpc.BookServiceStub(channel)
        try:
            resp = await stub.CheckAvailability(
                book_pb2.CheckAvailabilityRequest(book_id=book_id),
                timeout=10,
            )
        finally:
            await channel.close()

        if not resp.available:
            raise ValueError("No available copies of this book")

    async def _decrease_book_copies(self, book_id: str) -> None:
        channel = grpc.aio.insecure_channel(BOOK_SERVICE_ADDR)
        stub = book_pb2_grpc.BookServiceStub(channel)
        try:
            resp = await stub.DecreaseAvailableCopies(
                book_pb2.UpdateCopiesRequest(book_id=book_id, count=1),
                timeout=10,
            )
        finally:
            await channel.close()

        if not resp.success:
            raise RuntimeError("DecreaseAvailableCopies returned success=False")

    async def _increase_book_copies(self, book_id: str) -> None:
        channel = grpc.aio.insecure_channel(BOOK_SERVICE_ADDR)
        stub = book_pb2_grpc.BookServiceStub(channel)
        try:
            await stub.IncreaseAvailableCopies(
                book_pb2.UpdateCopiesRequest(book_id=book_id, count=1),
                timeout=10,
            )
        finally:
            await channel.close()

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
