"""SQLAlchemy models for Book Service."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, String, Integer, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_books_title_not_blank"),
        CheckConstraint("length(trim(author)) > 0", name="ck_books_author_not_blank"),
        CheckConstraint("length(trim(isbn)) >= 10", name="ck_books_isbn_min_length"),
        CheckConstraint("total_copies >= 0", name="ck_books_total_copies_non_negative"),
        CheckConstraint("available_copies >= 0", name="ck_books_available_copies_non_negative"),
        CheckConstraint("available_copies <= total_copies", name="ck_books_available_not_greater_than_total"),
        CheckConstraint("published_year IS NULL OR published_year BETWEEN 1000 AND 9999", name="ck_books_published_year_valid"),
        Index("ix_books_title", "title"),
        Index("ix_books_author", "author"),
        Index("ix_books_isbn", "isbn"),
        Index("ix_books_category", "category"),
        Index("ix_books_deleted_at", "deleted_at"),
        {"schema": "books_db"},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    author = Column(String(500), nullable=False)
    isbn = Column(String(20), unique=True, nullable=False)
    publisher = Column(String(300), nullable=True)
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    published_year = Column(Integer, nullable=True)
    total_copies = Column(Integer, nullable=False, default=1)
    available_copies = Column(Integer, nullable=False, default=1)
    shelf_location = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
