"""Pydantic schemas for API Gateway."""
from datetime import datetime
from typing import List, Optional, Generic, TypeVar
from pydantic import BaseModel, EmailStr, Field, field_validator

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total_count: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[T]
    pagination: PaginationMeta


# ── Book Schemas ─────────────────────────────────────────────────────────────

class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    author: str = Field(..., min_length=1, max_length=500)
    isbn: str = Field(..., min_length=10, max_length=20)
    publisher: Optional[str] = Field(None, max_length=300)
    category: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    published_year: Optional[int] = Field(None, ge=1000, le=2100)
    total_copies: int = Field(1, ge=1)
    shelf_location: Optional[str] = Field(None, max_length=50)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    author: Optional[str] = Field(None, min_length=1, max_length=500)
    isbn: Optional[str] = Field(None, min_length=10, max_length=20)
    publisher: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    published_year: Optional[int] = Field(None, ge=1000, le=2100)
    total_copies: Optional[int] = Field(None, ge=1)
    shelf_location: Optional[str] = None


class BookResponse(BaseModel):
    id: str
    title: str
    author: str
    isbn: str
    publisher: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    published_year: Optional[int] = None
    total_copies: int
    available_copies: int
    shelf_location: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── Member Schemas ────────────────────────────────────────────────────────────

class MemberBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=300)
    email: str = Field(..., pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)


class MemberCreate(MemberBase):
    pass


class MemberUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=300)
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


class MemberResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    membership_status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ── Lending Schemas ───────────────────────────────────────────────────────────

class BorrowRequest(BaseModel):
    member_id: str = Field(..., min_length=36, max_length=36)
    book_id: str = Field(..., min_length=36, max_length=36)
    due_days: int = Field(14, ge=1, le=365)


class ReturnRequest(BaseModel):
    lending_id: str = Field(..., min_length=36, max_length=36)


class LendingRecordResponse(BaseModel):
    id: str
    member_id: str
    book_id: str
    borrowed_at: Optional[str] = None
    due_date: Optional[str] = None
    returned_at: Optional[str] = None
    status: str
    fine_amount: float
    book_title: Optional[str] = None
    book_isbn: Optional[str] = None
    member_name: Optional[str] = None
    member_email: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ReturnResponse(BaseModel):
    record: LendingRecordResponse
    fine_amount: float
    is_overdue: bool
    overdue_days: int


# ── Health Schema ─────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    services: dict


# ── Dashboard Schema ──────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_books: int
    total_members: int
    books_borrowed: int
    overdue_books: int
