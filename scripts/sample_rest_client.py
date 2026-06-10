#!/usr/bin/env python3
"""
Library Management System - Python REST Sample Client
Demonstrates all major API operations end-to-end.
"""
import json
import sys
import uuid
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"
session = requests.Session()
session.headers.update({"Content-Type": "application/json"})


def print_section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def print_response(label: str, resp: requests.Response):
    print(f"\n[{resp.status_code}] {label}")
    try:
        data = resp.json()
        print(json.dumps(data, indent=2, default=str)[:800])
    except Exception:
        print(resp.text[:400])


def check_health():
    print_section("1. Health Check")
    resp = session.get(f"{BASE_URL}/health")
    print_response("GET /health", resp)
    return resp.status_code == 200


def demo_books():
    print_section("2. Book CRUD Operations")

    # Create
    book_data = {
        "title": "Clean Code",
        "author": "Robert C. Martin",
        "isbn": f"978{str(uuid.uuid4().int)[:10]}",
        "publisher": "Prentice Hall",
        "category": "Technology",
        "description": "A handbook of agile software craftsmanship",
        "published_year": 2008,
        "total_copies": 5,
        "shelf_location": "A1-01"
    }
    resp = session.post(f"{BASE_URL}/api/v1/books", json=book_data)
    print_response("POST /api/v1/books", resp)
    book_id = resp.json().get("id") if resp.ok else None

    if not book_id:
        print("❌ Book creation failed")
        return None

    # Get by ID
    resp = session.get(f"{BASE_URL}/api/v1/books/{book_id}")
    print_response(f"GET /api/v1/books/{book_id[:8]}...", resp)

    # List
    resp = session.get(f"{BASE_URL}/api/v1/books?page=1&page_size=5")
    print_response("GET /api/v1/books (list)", resp)

    # Search
    resp = session.get(f"{BASE_URL}/api/v1/books/search?q=Clean&search_by=title")
    print_response("GET /api/v1/books/search?q=Clean", resp)

    # Update
    resp = session.put(f"{BASE_URL}/api/v1/books/{book_id}", json={"shelf_location": "B2-05"})
    print_response(f"PUT /api/v1/books/{book_id[:8]}...", resp)

    return book_id


def demo_members():
    print_section("3. Member CRUD Operations")

    # Create
    member_data = {
        "full_name": "Priya Sharma",
        "email": f"priya_{uuid.uuid4().hex[:6]}@example.com",
        "phone": "+91 98765 43210",
        "address": "123 MG Road, Pune, Maharashtra"
    }
    resp = session.post(f"{BASE_URL}/api/v1/members", json=member_data)
    print_response("POST /api/v1/members", resp)
    member_id = resp.json().get("id") if resp.ok else None

    if not member_id:
        print("❌ Member creation failed")
        return None

    # Get
    resp = session.get(f"{BASE_URL}/api/v1/members/{member_id}")
    print_response(f"GET /api/v1/members/{member_id[:8]}...", resp)

    # List
    resp = session.get(f"{BASE_URL}/api/v1/members?page=1&page_size=5")
    print_response("GET /api/v1/members (list)", resp)

    # Update
    resp = session.put(f"{BASE_URL}/api/v1/members/{member_id}", json={"phone": "+91 91234 56789"})
    print_response(f"PUT /api/v1/members/{member_id[:8]}...", resp)

    return member_id


def demo_lending(book_id: str, member_id: str):
    print_section("4. Lending Operations")

    # Borrow
    resp = session.post(f"{BASE_URL}/api/v1/lending/borrow", json={
        "member_id": member_id,
        "book_id": book_id,
        "due_days": 14
    })
    print_response("POST /api/v1/lending/borrow", resp)
    lending_id = resp.json().get("id") if resp.ok else None

    if not lending_id:
        print("❌ Borrow failed")
        return

    # List borrowed
    resp = session.get(f"{BASE_URL}/api/v1/lending/borrowed")
    print_response("GET /api/v1/lending/borrowed", resp)

    # By member
    resp = session.get(f"{BASE_URL}/api/v1/lending/member/{member_id}")
    print_response(f"GET /api/v1/lending/member/{member_id[:8]}...", resp)

    # Book history
    resp = session.get(f"{BASE_URL}/api/v1/lending/book/{book_id}/history")
    print_response(f"GET /api/v1/lending/book/{book_id[:8]}...history", resp)

    # Overdue
    resp = session.get(f"{BASE_URL}/api/v1/lending/overdue")
    print_response("GET /api/v1/lending/overdue", resp)

    # Return
    resp = session.post(f"{BASE_URL}/api/v1/lending/return", json={"lending_id": lending_id})
    print_response("POST /api/v1/lending/return", resp)
    if resp.ok:
        data = resp.json()
        fine = data.get("fine_amount", 0)
        overdue = data.get("is_overdue", False)
        print(f"\n  📚 Return Summary: overdue={overdue}, fine=₹{fine:.2f}")


def demo_dashboard():
    print_section("5. Dashboard Stats")
    resp = session.get(f"{BASE_URL}/api/v1/dashboard")
    print_response("GET /api/v1/dashboard", resp)


def main():
    print("\n🏛️  Library Management System - REST API Demo")
    print(f"   Target: {BASE_URL}")
    print(f"   Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not check_health():
        print("\n❌ API Gateway is not reachable. Make sure the stack is running:")
        print("   docker compose up --build -d")
        sys.exit(1)

    book_id = demo_books()
    member_id = demo_members()

    if book_id and member_id:
        demo_lending(book_id, member_id)

    demo_dashboard()

    print("\n\n✅ Demo complete!")


if __name__ == "__main__":
    main()
