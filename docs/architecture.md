# Architecture

## Overview

The Library Management System uses a **microservices architecture** with three
domain services communicating via gRPC, fronted by a FastAPI REST gateway.

```
Browser / Client
       │ HTTP/REST
┌──────▼──────────────────────────────────────┐
│         API Gateway  :8000  (FastAPI)        │
│  REST endpoints · Pydantic validation · CORS │
└────────┬─────────────┬──────────────┬────────┘
  gRPC   │       gRPC  │       gRPC   │
:50051   │      :50052  │      :50053  │
┌────────▼──┐  ┌────────▼──┐  ┌───────▼──────┐
│  book-    │  │  member-  │  │  lending-    │
│  service  │  │  service  │  │  service     │
│           │  │           │  │ (calls book  │
│ books_db  │  │members_db │  │  + member)   │
└───────────┘  └───────────┘  └──────────────┘
         └──────────────────────────┘
                     │ PostgreSQL :5432
              ┌──────▼──────┐
              │  librarydb  │
              │  books_db   │
              │  members_db │
              │  lending_db │
              └─────────────┘
```

## Service Responsibilities

| Service | Transport | Port | Database Schema |
|---------|-----------|------|-----------------|
| api-gateway | HTTP/REST | 8000 | None (proxy only) |
| book-service | gRPC | 50051 | `books_db` |
| member-service | gRPC | 50052 | `members_db` |
| lending-service | gRPC | 50053 | `lending_db` |

## Saga Pattern for Borrow/Return

### Borrow Saga (correct order, compensating transaction)

```
1. ValidateActiveMember(member_id)   → member-service  [read-only]
2. CheckAvailability(book_id)        → book-service     [read-only]
3. DecreaseAvailableCopies(book_id)  → book-service     [COMMITS remotely]
4. Create LendingRecord              → local DB         [COMMITS locally]

If step 4 fails:
  COMPENSATE: IncreaseAvailableCopies(book_id) → book-service
```

Step 3 happens **before** step 4 to prevent lending records from existing
for books that couldn't be reserved. The saga compensates if the local
write fails after the remote commit.

### Return Saga (explicit rollback on failure)

```
1. Fetch LendingRecord, validate not already returned
2. Mark returned + calculate fine   → local DB   [COMMITS locally]
3. IncreaseAvailableCopies(book_id) → book-service

If step 3 fails:
  ROLLBACK: Re-open the lending record (set status back to BORROWED)
```

This prefers explicit rollback over silent inconsistency.

## Database Design

One PostgreSQL instance with three schemas (simulating service-owned DBs):

- `books_db.books` — book catalogue + copy inventory
- `members_db.members` — member profiles + status
- `lending_db.lending_records` — borrow/return records + fines

All tables use UUID primary keys, soft deletes (`deleted_at`), and
`created_at`/`updated_at` timestamps.
