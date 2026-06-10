# 🏛️ Library Management System — Windows Setup Guide

**Your environment:** Docker 29.2.1 · Python 3.10.11 · Node.js 24.13.1  
**Estimated time:** 15–25 minutes (mostly Docker image download time)

---

## Table of Contents

1. [Prerequisites Check](#1-prerequisites-check)
2. [Extract the Project](#2-extract-the-project)
3. [Configure Environment](#3-configure-environment)
4. [Start with Docker (Recommended)](#4-start-with-docker-recommended)
5. [Verify Everything is Running](#5-verify-everything-is-running)
6. [Access the Application](#6-access-the-application)
7. [Run the Demo Client](#7-run-the-demo-client)
8. [Run Tests](#8-run-tests)
9. [Common Commands](#9-common-commands)
10. [Troubleshooting](#10-troubleshooting)
11. [Stop the Application](#11-stop-the-application)

---

## 1. Prerequisites Check

Open **PowerShell** (or Command Prompt) and verify:

```powershell
docker -v
# Expected: Docker version 29.2.1, build a5c7197  ✓

docker compose version
# Expected: Docker Compose version v2.x.x  ✓

python --version
# Expected: Python 3.10.11  ✓

node -v
# Expected: v24.13.1  ✓
```

**Make sure Docker Desktop is running** — look for the whale icon in the system tray.
If it shows "Docker Desktop is starting…", wait for it to fully start before continuing.

---

## 2. Extract the Project

### Option A — Using the provided archive

```powershell
# Navigate to where you downloaded the .tar file
cd C:\Users\hp\Downloads

# Extract using tar (built into Windows 10/11)
tar -xf library-management-system-v2.tar

# Move into the project directory
cd library-management-system
```

> **If tar doesn't work**, use 7-Zip or WinRAR to extract the `.tar` file.

### Option B — Verify the directory structure

After extraction, verify these key files exist:

```powershell
dir
# You should see:
#   docker-compose.yml
#   .env.example
#   Makefile
#   README.md
#   proto\
#   services\
#   infrastructure\
#   scripts\
#   docs\

dir services
# You should see:
#   api-gateway\
#   book-service\
#   member-service\
#   lending-service\
#   frontend\
```

---

## 3. Configure Environment

Copy the example environment file:

```powershell
# PowerShell
Copy-Item .env.example .env

# OR Command Prompt
copy .env.example .env
```

The default `.env` file content works as-is for local development:

```
POSTGRES_USER=library
POSTGRES_PASSWORD=library
POSTGRES_DB=librarydb
NEXT_PUBLIC_API_URL=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:3000
GRPC_TIMEOUT=30
```

> **No changes needed** for running locally. All services are pre-configured
> to talk to each other via Docker's internal network.

---

## 4. Start with Docker (Recommended)

This single command builds all Docker images and starts all 6 services:

```powershell
docker compose up --build
```

**What happens step by step:**

```
Step 1: Docker pulls base images
        postgres:15-alpine     (~80 MB)
        python:3.11-slim       (~130 MB)
        node:20-alpine         (~180 MB)

Step 2: Docker builds service images
        [+] Building book-service     (installs Python deps, compiles proto files)
        [+] Building member-service   (installs Python deps, compiles proto files)
        [+] Building lending-service  (installs Python deps, compiles proto files)
        [+] Building api-gateway      (installs Python deps, compiles proto files)
        [+] Building frontend         (npm install, Next.js build)

Step 3: Containers start in dependency order
        1. postgres          → waits for health check
        2. book-service      → waits for postgres
        3. member-service    → waits for postgres
        4. lending-service   → waits for book + member services
        5. api-gateway       → waits for all gRPC services
        6. frontend          → waits for api-gateway
```

**Expected build time:** 5–15 minutes on first run (downloading images + building).
Subsequent starts take under 60 seconds.

### To run in background (detached mode):

```powershell
docker compose up --build -d
```

---

## 5. Verify Everything is Running

### Check container status:

```powershell
docker compose ps
```

**Expected output:**

```
NAME                 STATUS              PORTS
lms-postgres         Up (healthy)        0.0.0.0:5432->5432/tcp
lms-book-service     Up (healthy)        0.0.0.0:50051->50051/tcp
lms-member-service   Up (healthy)        0.0.0.0:50052->50052/tcp
lms-lending-service  Up                  0.0.0.0:50053->50053/tcp
lms-api-gateway      Up                  0.0.0.0:8000->8000/tcp
lms-frontend         Up                  0.0.0.0:3000->3000/tcp
```

> All services should show **Up**. `book-service` and `member-service` will show
> **(healthy)** once their gRPC health checks pass (takes ~30 seconds).

### Check API Gateway health:

```powershell
# PowerShell
Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing | Select-Object -ExpandProperty Content

# OR using curl (if available)
curl http://localhost:8000/health
```

**Expected response:**

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

## 6. Access the Application

All services are available immediately after `docker compose up`:

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend UI** | http://localhost:3000 | Main web application |
| **API Docs (Swagger)** | http://localhost:8000/docs | Interactive REST API documentation |
| **API Docs (ReDoc)** | http://localhost:8000/redoc | Alternative API documentation |
| **Health Check** | http://localhost:8000/health | Service health status |
| **Dashboard API** | http://localhost:8000/api/v1/dashboard | Stats JSON |

Open your browser and go to **http://localhost:3000** to see the application.

### What you can do in the UI:

1. **Dashboard** — View total books, members, borrowed books, overdue count
2. **Books → Add Book** — Add a new book to the catalogue
3. **Members → Add Member** — Register a new library member
4. **Borrow Book** — Issue a book to a member
5. **Return Book** — Process a book return (fine calculated automatically)
6. **Borrowed Books** — See all currently borrowed books
7. **Overdue Books** — See all overdue records

---

## 7. Run the Demo Client

Once the stack is running, you can run the Python REST demo client
to see all API operations in action:

```powershell
# Install requests library (only needed once)
pip install requests

# Run the demo
python scripts\sample_rest_client.py
```

**Expected output:**

```
🏛️  Library Management System - REST API Demo
   Target: http://localhost:8000
   Time:   2024-xx-xx xx:xx:xx

============================================================
  1. Health Check
============================================================
[200] GET /health
{"status": "healthy", ...}

============================================================
  2. Book CRUD Operations
============================================================
[201] POST /api/v1/books
{"id": "xxxxxxxx-...", "title": "Clean Code", ...}

============================================================
  3. Member CRUD Operations
============================================================
[201] POST /api/v1/members
{"id": "xxxxxxxx-...", "full_name": "Priya Sharma", ...}

============================================================
  4. Lending Operations
============================================================
[201] POST /api/v1/lending/borrow
{"id": "xxxxxxxx-...", "status": "BORROWED", "due_date": "..."}

  📚 Return Summary: overdue=False, fine=₹0.00

✅ Demo complete!
```

---

## 8. Run Tests

Open a **new** PowerShell window in the project root:

### Install test dependencies:

```powershell
# Install all Python test dependencies
pip install pytest pytest-asyncio

# Install service-specific requirements (needed for imports)
pip install -r services\book-service\requirements.txt
pip install -r services\member-service\requirements.txt
pip install -r services\lending-service\requirements.txt
pip install -r services\api-gateway\requirements.txt
```

### Generate proto stubs locally (required for tests):

```powershell
# Install grpcio-tools
pip install grpcio-tools protobuf

# Generate stubs for book-service
python -m grpc_tools.protoc `
    -I proto `
    --python_out=services\book-service\app\proto_generated `
    --grpc_python_out=services\book-service\app\proto_generated `
    proto\common.proto proto\book.proto proto\member.proto proto\lending.proto

# Create __init__.py
New-Item -ItemType File -Path services\book-service\app\proto_generated\__init__.py -Force

# Generate stubs for member-service
python -m grpc_tools.protoc `
    -I proto `
    --python_out=services\member-service\app\proto_generated `
    --grpc_python_out=services\member-service\app\proto_generated `
    proto\common.proto proto\book.proto proto\member.proto proto\lending.proto

New-Item -ItemType File -Path services\member-service\app\proto_generated\__init__.py -Force

# Generate stubs for lending-service
python -m grpc_tools.protoc `
    -I proto `
    --python_out=services\lending-service\app\proto_generated `
    --grpc_python_out=services\lending-service\app\proto_generated `
    proto\common.proto proto\book.proto proto\member.proto proto\lending.proto

New-Item -ItemType File -Path services\lending-service\app\proto_generated\__init__.py -Force

# Generate stubs for api-gateway
python -m grpc_tools.protoc `
    -I proto `
    --python_out=services\api-gateway\app\grpc_clients\proto_generated `
    --grpc_python_out=services\api-gateway\app\grpc_clients\proto_generated `
    proto\common.proto proto\book.proto proto\member.proto proto\lending.proto

New-Item -ItemType File -Path services\api-gateway\app\grpc_clients\proto_generated\__init__.py -Force
```

### Run the tests:

```powershell
# Run all tests
python -m pytest services\book-service\tests\ -v
python -m pytest services\member-service\tests\ -v
python -m pytest services\lending-service\tests\ -v
python -m pytest services\api-gateway\tests\ -v

# Run a specific test file
python -m pytest services\lending-service\tests\test_lending.py -v

# Run with verbose output and short traceback
python -m pytest services\ -v --tb=short
```

**Expected output:**

```
========================= test session starts ==========================
platform win32 -- Python 3.10.11, pytest-8.x.x, pluggy-1.x.x
collected 18 items

services\book-service\tests\test_book_repository.py::TestBookRepository::test_create_book PASSED
services\book-service\tests\test_book_repository.py::TestBookRepository::test_get_by_id_found PASSED
services\lending-service\tests\test_lending.py::TestFineCalculation::test_fine_per_day_constant PASSED
services\lending-service\tests\test_lending.py::TestFineCalculation::test_fine_for_5_days_overdue PASSED
...
========================= 18 passed in 1.23s ===========================
```

---

## 9. Common Commands

All commands below run from the **project root** (`library-management-system\`):

### Container management:

```powershell
# Start all services (foreground, shows logs)
docker compose up --build

# Start all services (background)
docker compose up --build -d

# Stop all services
docker compose down

# Stop and delete all data (volumes)
docker compose down -v

# Restart a single service
docker compose restart api-gateway

# Rebuild and restart a single service
docker compose up --build -d book-service
```

### View logs:

```powershell
# All services
docker compose logs -f

# Single service
docker compose logs -f api-gateway
docker compose logs -f book-service
docker compose logs -f lending-service

# Last 50 lines
docker compose logs --tail=50 api-gateway
```

### Database access:

```powershell
# Connect to PostgreSQL
docker compose exec postgres psql -U library -d librarydb

# Inside psql: list all schemas
\dn

# Inside psql: list books table
\dt books_db.*

# Inside psql: view all books
SELECT id, title, author, available_copies FROM books_db.books;

# Exit psql
\q
```

### API calls with curl (if available) or PowerShell:

```powershell
# Create a book (PowerShell)
$body = @{
    title = "The Pragmatic Programmer"
    author = "David Thomas"
    isbn = "9780135957059"
    total_copies = 3
    category = "Technology"
} | ConvertTo-Json

Invoke-WebRequest -Uri http://localhost:8000/api/v1/books `
    -Method POST `
    -ContentType "application/json" `
    -Body $body `
    -UseBasicParsing | Select-Object -ExpandProperty Content

# List books
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/books?page=1&page_size=10" `
    -UseBasicParsing | Select-Object -ExpandProperty Content

# Search books
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/books/search?q=pragmatic" `
    -UseBasicParsing | Select-Object -ExpandProperty Content
```

---

## 10. Troubleshooting

### ❌ Docker Desktop not running

**Symptom:** `error during connect: This error may indicate that the docker daemon is not running`

**Fix:** Open Docker Desktop from the Start menu and wait for it to fully start.

---

### ❌ Port already in use

**Symptom:** `Bind for 0.0.0.0:3000 failed: port is already allocated`

**Fix:**

```powershell
# Find what's using the port (example: port 3000)
netstat -ano | findstr :3000

# Kill the process (replace PID with the number from above)
taskkill /PID <PID> /F

# Or change ports in docker-compose.yml
# Example: change 3000:3000 to 3001:3000 for the frontend
```

---

### ❌ Services show "Exited" in docker compose ps

**Symptom:** A service exited immediately after starting.

**Fix:**

```powershell
# Check the logs for the failing service
docker compose logs book-service

# Common causes:
# 1. Database not ready yet - increase wait time
# 2. Port conflict - see above
# 3. Build error - rebuild
docker compose up --build --force-recreate
```

---

### ❌ Frontend shows "Failed to fetch" or blank page

**Symptom:** The UI loads but shows no data or network errors.

**Cause:** The frontend cannot reach the API Gateway.

**Fix:** Make sure the API Gateway is running:

```powershell
docker compose ps api-gateway
# Should show: Up

# Test the API directly
Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing
```

If the API is running but the frontend still fails, check CORS:

```powershell
docker compose logs api-gateway | Select-String "CORS"
```

---

### ❌ Health check shows "unhealthy" for gRPC services

**Symptom:** `book_service: "unhealthy"` in the `/health` response.

**Cause:** gRPC services take 20–40 seconds to start after PostgreSQL becomes healthy.

**Fix:** Wait 1–2 minutes and try again. The services retry automatically.

```powershell
# Watch health status
while ($true) {
    Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing | 
        Select-Object -ExpandProperty Content
    Start-Sleep 5
}
```

---

### ❌ Build fails: "could not find expected ':'" (YAML error)

**Cause:** Windows line endings (CRLF) in YAML files.

**Fix:**

```powershell
# Convert line endings (requires git)
git config --global core.autocrlf false

# Or use VS Code: open the file, click "CRLF" in the bottom bar, change to "LF"
```

---

### ❌ "Module not found" errors in tests

**Cause:** Proto stubs haven't been generated locally.

**Fix:** Run the proto generation commands from Step 8 above.

---

### ❌ Docker build is very slow

**Tip:** Enable BuildKit for faster builds:

```powershell
# Set environment variable
$env:DOCKER_BUILDKIT = "1"
$env:COMPOSE_DOCKER_CLI_BUILD = "1"

# Then rebuild
docker compose up --build
```

---

### ❌ "no such file or directory: public" in frontend build

**Fix:** The `public` directory is already created in the project. If missing:

```powershell
New-Item -ItemType Directory -Path services\frontend\public -Force
```

---

### ❌ lending-service keeps restarting

**Cause:** It depends on `book-service` and `member-service` being healthy.
If those take too long, lending-service starts before they're ready.

**Fix:** Start services in order:

```powershell
# Start just the database and backend services first
docker compose up -d postgres book-service member-service

# Wait 30 seconds, then start the rest
Start-Sleep 30
docker compose up -d lending-service api-gateway frontend
```

---

## 11. Stop the Application

```powershell
# Stop all containers (keeps data)
docker compose down

# Stop and remove ALL data (clean slate)
docker compose down -v

# Stop a single service
docker compose stop frontend
```

---

## Port Reference

| Port | Service | Description |
|------|---------|-------------|
| 3000 | Frontend | Next.js web application |
| 8000 | API Gateway | FastAPI REST API |
| 5432 | PostgreSQL | Database (internal) |
| 50051 | Book Service | gRPC server |
| 50052 | Member Service | gRPC server |
| 50053 | Lending Service | gRPC server |

---

## Quick Reference Card

```
START:   docker compose up --build -d
STOP:    docker compose down
LOGS:    docker compose logs -f
STATUS:  docker compose ps
UI:      http://localhost:3000
API:     http://localhost:8000/docs
HEALTH:  http://localhost:8000/health
```
