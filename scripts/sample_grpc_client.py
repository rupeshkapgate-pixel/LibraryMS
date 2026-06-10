#!/usr/bin/env python3
"""
Library Management System - Python gRPC Sample Client
Demonstrates direct gRPC communication with each service.

Run after generating protos:
  make proto
  python scripts/sample_grpc_client.py
"""
import asyncio
import sys
import uuid
import os

# Add proto generated path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import grpc

# These imports assume proto stubs are generated in one of the service dirs
# Run `make proto` first
try:
    from services.book_service.app.proto_generated import (
        book_pb2, book_pb2_grpc, common_pb2
    )
    from services.member_service.app.proto_generated import (
        member_pb2, member_pb2_grpc
    )
    from services.lending_service.app.proto_generated import (
        lending_pb2, lending_pb2_grpc
    )
except ImportError:
    print("❌ Proto stubs not found. Run: make proto")
    sys.exit(1)

BOOK_ADDR   = os.getenv("BOOK_SERVICE_ADDR",   "localhost:50051")
MEMBER_ADDR = os.getenv("MEMBER_SERVICE_ADDR", "localhost:50052")
LEND_ADDR   = os.getenv("LEND_SERVICE_ADDR",   "localhost:50053")


def print_section(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


async def demo_book_service():
    print_section("Book Service - gRPC")
    async with grpc.aio.insecure_channel(BOOK_ADDR) as channel:
        stub = book_pb2_grpc.BookServiceStub(channel)

        # Create
        isbn = f"978{str(uuid.uuid4().int)[:10]}"
        book = await stub.CreateBook(book_pb2.CreateBookRequest(
            title="Design Patterns",
            author="Gang of Four",
            isbn=isbn,
            publisher="Addison-Wesley",
            category="Technology",
            description="Elements of Reusable Object-Oriented Software",
            published_year=1994,
            total_copies=3,
            shelf_location="C3-15",
        ), timeout=10)
        print(f"✅ CreateBook: id={book.id[:8]}... title='{book.title}'")

        # Get
        fetched = await stub.GetBook(
            book_pb2.GetBookRequest(id=book.id), timeout=10
        )
        print(f"✅ GetBook: '{fetched.title}' available={fetched.available_copies}")

        # Check availability
        avail = await stub.CheckAvailability(
            book_pb2.CheckAvailabilityRequest(book_id=book.id), timeout=10
        )
        print(f"✅ CheckAvailability: available={avail.available} copies={avail.available_copies}")

        # Search
        results = await stub.SearchBooks(book_pb2.SearchBooksRequest(
            query="Design",
            search_by="title",
            pagination=common_pb2.PaginationRequest(page=1, page_size=5),
        ), timeout=10)
        print(f"✅ SearchBooks: found {results.pagination.total_count} results")

        # List
        listing = await stub.ListBooks(book_pb2.ListBooksRequest(
            pagination=common_pb2.PaginationRequest(page=1, page_size=10),
        ), timeout=10)
        print(f"✅ ListBooks: total={listing.pagination.total_count}")

        return book.id


async def demo_member_service():
    print_section("Member Service - gRPC")
    async with grpc.aio.insecure_channel(MEMBER_ADDR) as channel:
        stub = member_pb2_grpc.MemberServiceStub(channel)

        # Create
        email = f"test_{uuid.uuid4().hex[:6]}@library.com"
        member = await stub.CreateMember(member_pb2.CreateMemberRequest(
            full_name="Rahul Gupta",
            email=email,
            phone="+91 9876543210",
            address="456 FC Road, Pune",
        ), timeout=10)
        print(f"✅ CreateMember: id={member.id[:8]}... name='{member.full_name}'")

        # Validate
        validation = await stub.ValidateActiveMember(
            member_pb2.ValidateActiveMemberRequest(member_id=member.id), timeout=10
        )
        print(f"✅ ValidateActiveMember: is_active={validation.is_active} msg='{validation.message}'")

        # List
        listing = await stub.ListMembers(member_pb2.ListMembersRequest(
            pagination=common_pb2.PaginationRequest(page=1, page_size=5),
        ), timeout=10)
        print(f"✅ ListMembers: total={listing.pagination.total_count}")

        return member.id


async def demo_lending_service(book_id: str, member_id: str):
    print_section("Lending Service - gRPC")
    async with grpc.aio.insecure_channel(LEND_ADDR) as channel:
        stub = lending_pb2_grpc.LendingServiceStub(channel)

        # Borrow
        record = await stub.BorrowBook(lending_pb2.BorrowBookRequest(
            member_id=member_id,
            book_id=book_id,
            due_days=14,
        ), timeout=15)
        print(f"✅ BorrowBook: id={record.id[:8]}... status={record.status} due={record.due_date[:10]}")

        # List borrowed
        borrowed = await stub.ListBorrowedBooks(lending_pb2.ListBorrowedBooksRequest(
            pagination=common_pb2.PaginationRequest(page=1, page_size=5),
        ), timeout=10)
        print(f"✅ ListBorrowedBooks: total={borrowed.pagination.total_count}")

        # By member
        by_member = await stub.ListBorrowedBooksByMember(
            lending_pb2.ListBorrowedBooksByMemberRequest(
                member_id=member_id,
                pagination=common_pb2.PaginationRequest(page=1, page_size=5),
            ), timeout=10
        )
        print(f"✅ ListBorrowedBooksByMember: {by_member.pagination.total_count} records for member")

        # Book history
        history = await stub.ListBookBorrowHistory(
            lending_pb2.ListBookBorrowHistoryRequest(
                book_id=book_id,
                pagination=common_pb2.PaginationRequest(page=1, page_size=5),
            ), timeout=10
        )
        print(f"✅ ListBookBorrowHistory: {history.pagination.total_count} history records")

        # Return
        returned = await stub.ReturnBook(
            lending_pb2.ReturnBookRequest(lending_id=record.id), timeout=15
        )
        print(f"✅ ReturnBook: fine=₹{returned.fine_amount:.2f} overdue={returned.is_overdue}")


async def main():
    print("\n📡 Library Management System - gRPC Direct Client")
    print(f"   Book:    {BOOK_ADDR}")
    print(f"   Member:  {MEMBER_ADDR}")
    print(f"   Lending: {LEND_ADDR}")

    try:
        book_id = await demo_book_service()
        member_id = await demo_member_service()
        await demo_lending_service(book_id, member_id)
        print("\n✅ gRPC demo complete!")
    except grpc.RpcError as e:
        print(f"\n❌ gRPC error: {e.code()} - {e.details()}")
        print("Make sure services are running: make up")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
