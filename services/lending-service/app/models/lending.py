"""SQLAlchemy models for Lending Service."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Float, Enum, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class LendingStatus(str, enum.Enum):
    BORROWED = "BORROWED"
    RETURNED = "RETURNED"
    OVERDUE = "OVERDUE"


class LendingRecord(Base):
    __tablename__ = "lending_records"
    __table_args__ = (
        CheckConstraint("due_date >= borrowed_at", name="ck_lending_due_after_borrow"),
        CheckConstraint("fine_amount >= 0", name="ck_lending_fine_non_negative"),
        CheckConstraint(
            "(status != 'RETURNED') OR returned_at IS NOT NULL",
            name="ck_lending_returned_has_returned_at",
        ),
        Index("ix_lending_member_id", "member_id"),
        Index("ix_lending_book_id", "book_id"),
        Index("ix_lending_status", "status"),
        Index("ix_lending_due_date", "due_date"),
        Index(
            "uq_lending_active_member_book",
            "member_id",
            "book_id",
            unique=True,
            postgresql_where=text("status IN ('BORROWED', 'OVERDUE')"),
        ),
        {"schema": "lending_db"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    member_id = Column(UUID(as_uuid=True), nullable=False)
    book_id = Column(UUID(as_uuid=True), nullable=False)
    borrowed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    returned_at = Column(DateTime, nullable=True)
    status = Column(
        Enum(LendingStatus, schema="lending_db"),
        nullable=False,
        default=LendingStatus.BORROWED,
    )
    fine_amount = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
