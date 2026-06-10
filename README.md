# 🏛️ Library Management System

Production-ready microservices system for managing books, members, and borrowing operations.

> **The application is container-first. Docker Compose is the primary supported local runtime.
> Unit tests are also supported locally after installing Python dependencies.**

---

## Quick Start

```bash
cp .env.example .env
docker compose up --build
```

| URL | Description |
|-----|-------------|
| http://localhost:3000 | Frontend (Next.js) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/health | Health check |

---

## Reviewer Validation Commands

Run these in order to validate the full submission:

```bash
# 1. Generate protobuf stubs
make proto

# 2. Run all unit tests (no Docker required)
make test

# 3. Start the full stack
docker compose up --build

# 4. Check all containers are healthy
docker compose ps

# 5. Health check
curl http://localhost:8000/health

# 6. List books (empty on fresh start)
curl http://localhost:8000/api/v1/books

# 7. Run the end-to-end demo
python scripts/sample_rest_client.py
```

### Expected output — `make test`

```
services/book-service/tests/test_book_repository.py ........  PASSED
services/member-service/tests/test_member_repository.py .....  PASSED
services/lending-service/tests/test_lending.py ..........      PASSED
services/api-gateway/tests/test_schemas.py ..........          PASSED
```

### Expected output — `curl http://localhost:8000/health`

```json
{
  "status": "healthy",
  "services": {
    "book_service": "healthy",
    "member_service": "healthy",
    "lending_service": "healthy"
  }
}
```

---

## Architecture

```
Browser → Next.js Frontend (:3000)
             │ HTTP/REST
          API Gateway (:8000, FastAPI)
             │           │          │
          gRPC        gRPC       gRPC
        book-svc    member-svc  lending-svc
        (:50051)    (:50052)    (:50053)
             └───────────────────────┘
                        │
                  PostgreSQL (:5432)
              books_db / members_db / lending_db
```

See [docs/architecture.md](docs/architecture.md) for full detail including the
Saga consistency pattern for borrow/return operations.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, TailwindCSS, React Query |
| API Gateway | Python 3.11, FastAPI |
| gRPC Services | Python 3.11, grpc.aio |
| Serialization | Protocol Buffers 3 |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic |
| Database | PostgreSQL 15 |
| Containers | Docker Compose |
| Orchestration | Kubernetes |
| Tests | pytest, pytest-asyncio |
| CI/CD | GitHub Actions |

---

## Proto Generation

```bash
# Install tools (once)
make proto-install

# Generate stubs for all services
make proto
```

Stubs are written to `app/proto_generated/` inside each service.
The script also runs `scripts/fix_proto_imports.py` to rewrite bare protoc
imports to relative imports (required when stubs live inside a Python package).

**Windows users:** Run from Git Bash, or run the protoc commands directly:
```powershell
python -m grpc_tools.protoc -I proto --python_out=... --grpc_python_out=... proto\common.proto
python scripts\fix_proto_imports.py <output_dir>
```

---

## Running Tests Locally

```bash
# Install pytest + all service requirements (once)
make test-install

# Generate proto stubs (once)
make proto

# Run all tests
make test

# Run one service
make test-book-service
```

Tests use `unittest.mock` — no running database or services required.

---

## Database Migrations (Alembic)

Docker Compose creates the schema automatically via `Base.metadata.create_all()`.
To run explicit Alembic migrations against a running postgres:

```bash
# Start postgres only
docker compose up -d postgres

# Run migrations
make migrate-all

# Or per service
make migrate-book-service
```

Migration files: `services/<service>/alembic/versions/001_initial_schema.py`

---

## Kubernetes Deployment

```bash
# 1. Build images
make k8s-build

# 2. Deploy (Docker Desktop with Kubernetes enabled)
make k8s-apply

# 3. Check status
kubectl get pods -n library-system

# 4. Forward ports
kubectl port-forward svc/api-gateway 8000:8000 -n library-system
kubectl port-forward svc/frontend    3000:3000 -n library-system

# 5. Teardown
make k8s-delete
```

See [docs/deployment-guide.md](docs/deployment-guide.md) for minikube instructions.

---

## API Reference

Full interactive docs at **http://localhost:8000/docs**

### Error format

All errors return a consistent JSON body:
```json
{
  "error": "NOT_FOUND",
  "message": "Book abc123 not found",
  "details": {}
}
```

### gRPC → HTTP mapping

| gRPC | HTTP |
|------|------|
| NOT_FOUND | 404 |
| ALREADY_EXISTS | 409 |
| FAILED_PRECONDITION | 409 |
| INVALID_ARGUMENT | 422 |
| UNAVAILABLE | 503 |
| DEADLINE_EXCEEDED | 504 |
| INTERNAL | 500 |

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/architecture.md](docs/architecture.md) | Architecture + Saga pattern |
| [docs/deployment-guide.md](docs/deployment-guide.md) | Docker + Kubernetes setup |
| [docs/testing-guide.md](docs/testing-guide.md) | How to run and extend tests |
| [docs/grpc-contracts.md](docs/grpc-contracts.md) | All RPC definitions |
| [docs/database-design.md](docs/database-design.md) | Schema + ER description |

---

## Troubleshooting

See [WINDOWS_SETUP.md](WINDOWS_SETUP.md) for Windows-specific instructions.

**Proto import errors:** Run `make proto` to regenerate and fix imports.

**Test import errors:** Tests import `from app.X` — ensure you run
`pytest` from `services/<service>/` or use `make test`.

**Book creation fails:** Check that the ISBN is ≥ 10 characters and not duplicate.
