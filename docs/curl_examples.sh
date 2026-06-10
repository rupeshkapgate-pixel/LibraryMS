# Library Management System - cURL Examples
# Replace UUIDs with actual values from your running system.

BASE_URL="http://localhost:8000"

# ── Health ────────────────────────────────────────────────────────────────
curl -s "$BASE_URL/health" | jq

# ── Dashboard ─────────────────────────────────────────────────────────────
curl -s "$BASE_URL/api/v1/dashboard" | jq

# ── Books ─────────────────────────────────────────────────────────────────

# Create a book
curl -s -X POST "$BASE_URL/api/v1/books" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Clean Code",
    "author": "Robert C. Martin",
    "isbn": "9780132350884",
    "publisher": "Prentice Hall",
    "category": "Technology",
    "description": "A handbook of agile software craftsmanship",
    "published_year": 2008,
    "total_copies": 5,
    "shelf_location": "A1-01"
  }' | jq

# List books
curl -s "$BASE_URL/api/v1/books?page=1&page_size=20" | jq

# Get book by ID
BOOK_ID="<your-book-uuid>"
curl -s "$BASE_URL/api/v1/books/$BOOK_ID" | jq

# Search books
curl -s "$BASE_URL/api/v1/books/search?q=Clean&search_by=title" | jq
curl -s "$BASE_URL/api/v1/books/search?q=Martin&search_by=author" | jq
curl -s "$BASE_URL/api/v1/books/search?q=Technology&search_by=category" | jq

# Update book
curl -s -X PUT "$BASE_URL/api/v1/books/$BOOK_ID" \
  -H "Content-Type: application/json" \
  -d '{"shelf_location": "B2-05", "total_copies": 8}' | jq

# Delete book (soft delete)
curl -s -X DELETE "$BASE_URL/api/v1/books/$BOOK_ID" -w "HTTP %{http_code}\n"

# ── Members ───────────────────────────────────────────────────────────────

# Create member
curl -s -X POST "$BASE_URL/api/v1/members" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Priya Sharma",
    "email": "priya.sharma@example.com",
    "phone": "+91 98765 43210",
    "address": "123 MG Road, Pune, Maharashtra"
  }' | jq

# List members
curl -s "$BASE_URL/api/v1/members?page=1&page_size=20" | jq

# Get member
MEMBER_ID="<your-member-uuid>"
curl -s "$BASE_URL/api/v1/members/$MEMBER_ID" | jq

# Update member
curl -s -X PUT "$BASE_URL/api/v1/members/$MEMBER_ID" \
  -H "Content-Type: application/json" \
  -d '{"phone": "+91 91234 56789"}' | jq

# Deactivate member
curl -s -X DELETE "$BASE_URL/api/v1/members/$MEMBER_ID" -w "HTTP %{http_code}\n"

# ── Lending ───────────────────────────────────────────────────────────────

# Borrow a book
BOOK_ID="<your-book-uuid>"
MEMBER_ID="<your-member-uuid>"
curl -s -X POST "$BASE_URL/api/v1/lending/borrow" \
  -H "Content-Type: application/json" \
  -d "{
    \"member_id\": \"$MEMBER_ID\",
    \"book_id\": \"$BOOK_ID\",
    \"due_days\": 14
  }" | jq

# Return a book
LENDING_ID="<your-lending-uuid>"
curl -s -X POST "$BASE_URL/api/v1/lending/return" \
  -H "Content-Type: application/json" \
  -d "{\"lending_id\": \"$LENDING_ID\"}" | jq

# List all borrowed books
curl -s "$BASE_URL/api/v1/lending/borrowed?page=1&page_size=20" | jq

# Borrowed books by member
curl -s "$BASE_URL/api/v1/lending/member/$MEMBER_ID" | jq

# Book borrow history
curl -s "$BASE_URL/api/v1/lending/book/$BOOK_ID/history" | jq

# Overdue books
curl -s "$BASE_URL/api/v1/lending/overdue" | jq

# ── API Docs (browser) ────────────────────────────────────────────────────
# Swagger UI: http://localhost:8000/docs
# ReDoc:      http://localhost:8000/redoc
