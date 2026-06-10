.PHONY: help up down build proto proto-install test test-% lint format \
        db-shell db-init migrate-% k8s-apply k8s-delete k8s-status \
        frontend-install frontend-dev frontend-build clean \
        dev-book dev-member dev-lending dev-gateway sample-client

SHELL     := /bin/bash
ROOT_DIR  := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
SERVICES  := book-service member-service lending-service api-gateway

# ─────────────────────────────────────────────────────────────────────────────
help: ## Show this help
	@awk 'BEGIN {FS=":.*##"; printf "\n\033[1mLibrary Management System\033[0m\n\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} \
	  /^[a-zA-Z_%-]+:.*?##/ {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# ── Docker ─────────────────────────────────────────────────────────────────
up: ## Build images and start all services
	docker compose up --build -d
	@echo "\n✅ Stack is up!"
	@echo "   Frontend:  http://localhost:3000"
	@echo "   API:       http://localhost:8000"
	@echo "   Swagger:   http://localhost:8000/docs"

down: ## Stop all services
	docker compose down

build: ## Build Docker images without starting
	docker compose build

restart-%: ## Restart one service: make restart-api-gateway
	docker compose restart $*

ps: ## Show container status
	docker compose ps

logs: ## Follow logs for all services
	docker compose logs -f

logs-%: ## Follow logs for one service: make logs-book-service
	docker compose logs -f $*

# ── Proto generation ────────────────────────────────────────────────────────
proto-install: ## Install grpcio-tools (run once)
	pip install grpcio-tools protobuf

proto: ## Generate protobuf stubs and fix imports for all services
	@chmod +x scripts/generate_proto.sh
	@bash scripts/generate_proto.sh

# ── Database ────────────────────────────────────────────────────────────────
db-shell: ## Connect to PostgreSQL
	docker compose exec postgres psql -U library -d librarydb

db-init: ## Run init_db.sql manually
	docker compose exec postgres psql -U library -d librarydb \
	  -f /docker-entrypoint-initdb.d/init_db.sql

migrate-%: ## Run Alembic migrations for a service: make migrate-book-service
	@echo "Running migrations for $*..."
	cd services/$* && \
	  DATABASE_URL_SYNC=postgresql+psycopg2://library:library@localhost:5432/librarydb \
	  alembic upgrade head

migrate-all: ## Run Alembic migrations for all services
	@for svc in book-service member-service lending-service; do \
	  echo "Migrating $$svc..."; \
	  cd $(ROOT_DIR)/services/$$svc && \
	    DATABASE_URL_SYNC=postgresql+psycopg2://library:library@localhost:5432/librarydb \
	    alembic upgrade head && \
	  cd $(ROOT_DIR); \
	done
	@echo "✅ All migrations applied"

# ── Testing ─────────────────────────────────────────────────────────────────
test: ## Run all unit tests (no services required)
	@echo "Running book-service tests..."
	@cd services/book-service && python -m pytest tests/ -v --tb=short
	@echo "\nRunning member-service tests..."
	@cd services/member-service && python -m pytest tests/ -v --tb=short
	@echo "\nRunning lending-service tests..."
	@cd services/lending-service && python -m pytest tests/ -v --tb=short
	@echo "\nRunning api-gateway tests..."
	@cd services/api-gateway && python -m pytest tests/ -v --tb=short
	@echo "\n✅ All tests passed"

test-%: ## Run tests for one service: make test-book-service
	@cd services/$* && python -m pytest tests/ -v --tb=short

test-install: ## Install test dependencies locally
	pip install pytest pytest-asyncio
	@for svc in $(SERVICES); do \
	  pip install -r services/$$svc/requirements.txt; \
	done

# ── Lint ─────────────────────────────────────────────────────────────────────
lint: ## Lint all Python services
	@for svc in $(SERVICES); do \
	  echo "Linting $$svc..."; \
	  ruff check services/$$svc/app/ --ignore E501,E402; \
	done

format: ## Format all Python services
	@for svc in $(SERVICES); do \
	  black services/$$svc/app/; \
	done

# ── Kubernetes ───────────────────────────────────────────────────────────────
k8s-build: ## Build and tag images for Kubernetes
	@echo "Building images for Kubernetes..."
	@for svc in book-service member-service lending-service api-gateway; do \
	  echo "  Building lms/$$svc:latest ..."; \
	  docker build -t lms/$$svc:latest -f services/$$svc/Dockerfile . ; \
	done
	@echo "  Building lms/frontend:latest ..."
	docker build -t lms/frontend:latest -f services/frontend/Dockerfile services/frontend
	@echo "✅ All images built"

k8s-apply: ## Deploy to Kubernetes (run k8s-build first)
	kubectl apply -f infrastructure/k8s/namespace.yaml
	kubectl apply -f infrastructure/k8s/configmap.yaml
	kubectl apply -f infrastructure/k8s/secret.yaml
	kubectl apply -f infrastructure/k8s/postgres-deployment.yaml
	@echo "Waiting for postgres to be ready..."
	kubectl wait --for=condition=ready pod -l app=postgres -n library-system --timeout=120s
	kubectl apply -f infrastructure/k8s/book-service-deployment.yaml
	kubectl apply -f infrastructure/k8s/member-service-deployment.yaml
	kubectl apply -f infrastructure/k8s/lending-service-deployment.yaml
	kubectl apply -f infrastructure/k8s/api-gateway-deployment.yaml
	kubectl apply -f infrastructure/k8s/frontend-deployment.yaml
	kubectl apply -f infrastructure/k8s/ingress.yaml
	kubectl apply -f infrastructure/k8s/hpa.yaml
	kubectl apply -f infrastructure/k8s/network-policy.yaml
	@echo "\n✅ Kubernetes deployment complete!"
	@echo "   Run: make k8s-status"

k8s-delete: ## Remove all Kubernetes resources
	kubectl delete namespace library-system --ignore-not-found

k8s-status: ## Show pod status
	kubectl get pods -n library-system

k8s-port-forward: ## Forward API and Frontend ports (run in separate terminals)
	@echo "Run these in separate terminals:"
	@echo "  kubectl port-forward svc/api-gateway 8000:8000 -n library-system"
	@echo "  kubectl port-forward svc/frontend    3000:3000 -n library-system"

k8s-logs-%: ## Stream pod logs: make k8s-logs-book-service
	kubectl logs -f -l app=$* -n library-system

# ── Frontend ─────────────────────────────────────────────────────────────────
frontend-install: ## Install frontend npm deps
	cd services/frontend && npm install --legacy-peer-deps

frontend-dev: ## Start frontend in dev mode (hot reload)
	cd services/frontend && npm run dev

frontend-build: ## Build frontend for production
	cd services/frontend && npm run build

# ── Local dev (without Docker) ────────────────────────────────────────────────
dev-book: ## Start book-service locally (requires local postgres)
	cd services/book-service && python main.py

dev-member: ## Start member-service locally
	cd services/member-service && python main.py

dev-lending: ## Start lending-service locally
	cd services/lending-service && python main.py

dev-gateway: ## Start api-gateway locally (hot reload)
	cd services/api-gateway && uvicorn app.main:app --reload --port 8000

# ── Sample clients ────────────────────────────────────────────────────────────
sample-client: ## Run the full REST demo against running stack
	python scripts/sample_rest_client.py

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Remove containers, volumes, and generated proto stubs
	docker compose down -v --remove-orphans
	find . -path "*/proto_generated/*.py" ! -name "__init__.py" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	@echo "✅ Cleanup complete"

# ── Reviewer validation ───────────────────────────────────────────────────────
validate: ## Run the full reviewer validation sequence
	@echo "1. Generating proto stubs..."
	@bash scripts/generate_proto.sh
	@echo "\n2. Running unit tests..."
	@make test
	@echo "\n3. Starting stack..."
	@docker compose up --build -d
	@echo "Waiting 30s for services to start..."
	@sleep 30
	@echo "\n4. Health check..."
	@curl -sf http://localhost:8000/health | python3 -m json.tool
	@echo "\n5. List books (should return empty pagination)..."
	@curl -sf "http://localhost:8000/api/v1/books?page=1&page_size=5" | python3 -m json.tool
	@echo "\n✅ Validation complete!"
