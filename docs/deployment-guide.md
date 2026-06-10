# Deployment Guide

## Docker Compose (Primary — Local Development)

```bash
# 1. Clone and configure
cp .env.example .env

# 2. Start everything
docker compose up --build

# 3. Verify
curl http://localhost:8000/health
```

Services: http://localhost:3000 (frontend), http://localhost:8000/docs (API)

---

## Kubernetes (Docker Desktop or minikube)

### Step 1 — Build images locally

```bash
make k8s-build
# This runs:
# docker build -t lms/book-service:latest    -f services/book-service/Dockerfile .
# docker build -t lms/member-service:latest  -f services/member-service/Dockerfile .
# docker build -t lms/lending-service:latest -f services/lending-service/Dockerfile .
# docker build -t lms/api-gateway:latest     -f services/api-gateway/Dockerfile .
# docker build -t lms/frontend:latest        -f services/frontend/Dockerfile services/frontend
```

### Step 2 — Enable Kubernetes in Docker Desktop

Docker Desktop → Settings → Kubernetes → Enable Kubernetes → Apply & Restart

### Step 3 — Deploy

```bash
make k8s-apply
```

### Step 4 — Check pods

```bash
kubectl get pods -n library-system
# All pods should show Running/1/1 Ready
```

### Step 5 — Access services

```bash
# Terminal 1
kubectl port-forward svc/api-gateway 8000:8000 -n library-system

# Terminal 2
kubectl port-forward svc/frontend 3000:3000 -n library-system
```

Then open http://localhost:3000

### Teardown

```bash
make k8s-delete
```

---

## Alembic Migrations (optional — Docker auto-creates schema)

Docker Compose automatically creates the database schema via `Base.metadata.create_all()`.
For explicit Alembic-managed migrations:

```bash
# Prerequisites: postgres running on localhost:5432
# (docker compose up -d postgres)

# Run migrations for all services
make migrate-all

# Or per service
make migrate-book-service
make migrate-member-service
make migrate-lending-service

# Check migration status
cd services/book-service
DATABASE_URL_SYNC=postgresql+psycopg2://library:library@localhost:5432/librarydb \
  alembic current
```
