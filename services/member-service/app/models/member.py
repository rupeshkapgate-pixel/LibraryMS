"""SQLAlchemy models for Member Service."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase
import enum


class Base(DeclarativeBase):
    pass


class MembershipStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class Member(Base):
    __tablename__ = "members"
    __table_args__ = (
        Index("ix_members_email", "email"),
        Index("ix_members_status", "membership_status"),
        Index("ix_members_deleted_at", "deleted_at"),
        {"schema": "members_db"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(300), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    address = Column(String(500), nullable=True)
    membership_status = Column(
        Enum(MembershipStatus, schema="members_db"),
        nullable=False,
        default=MembershipStatus.ACTIVE,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
