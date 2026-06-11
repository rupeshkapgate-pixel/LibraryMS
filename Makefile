.PHONY: help up down build proto test lint clean k8s-apply k8s-delete logs

SHELL := /bin/bash
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
SERVICES := book-service member-service lending-service api-gateway

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\n\033[1mLibrary Management System\033[0m\n\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# ── Docker ────────────────────────────────────────────────────────────────
up: ## Start all services (docker compose up --build)
	docker compose up --build -d
	@echo "\n✅ Services started!"
	@echo "   Frontend:    http://localhost:3000"
	@echo "   API Gateway: http://localhost:8000"
	@echo "   API Docs:    http://localhost:8000/docs"

down: ## Stop all services
	docker compose down

build: ## Build all Docker images
	docker compose build

logs: ## Follow logs for all services
	docker compose logs -f

logs-%: ## Follow logs for a specific service (make logs-api-gateway)
	docker compose logs -f $*

restart-%: ## Restart a specific service
	docker compose restart $*

ps: ## Show running containers
	docker compose ps

# ── Proto ─────────────────────────────────────────────────────────────────
proto: ## Generate protobuf stubs for all services
	@chmod +x scripts/generate_proto.sh
	@bash scripts/generate_proto.sh

proto-install: ## Install grpcio-tools for proto generation
	pip install grpcio-tools protobuf

# ── Database ──────────────────────────────────────────────────────────────
db-init: ## Initialize database schemas
	docker compose exec postgres psql -U library -d librarydb -f /docker-entrypoint-initdb.d/init_db.sql

db-shell: ## Open psql shell
	docker compose exec postgres psql -U library -d librarydb

# ── Testing ───────────────────────────────────────────────────────────────
test: ## Run all tests
	@echo "Running book-service tests..."
	cd services/book-service && pip install -r requirements.txt pytest pytest-asyncio -q && \
		python -m pytest tests/ -v --tb=short || true
	@echo "\nRunning member-service tests..."
	cd services/member-service && pip install -r requirements.txt pytest pytest-asyncio -q && \
		python -m pytest tests/ -v --tb=short || true
	@echo "\nRunning lending-service tests..."
	cd services/lending-service && pip install -r requirements.txt pytest pytest-asyncio -q && \
		python -m pytest tests/ -v --tb=short || true
	@echo "\nRunning api-gateway tests..."
	cd services/api-gateway && pip install -r requirements.txt pytest pytest-asyncio -q && \
		python -m pytest tests/ -v --tb=short || true

test-%: ## Run tests for a specific service (make test-book-service)
	cd services/$* && pip install -r requirements.txt pytest pytest-asyncio -q && \
		python -m pytest tests/ -v

# ── Linting ───────────────────────────────────────────────────────────────
lint: ## Lint all Python services
	@for svc in $(SERVICES); do \
		echo "Linting $$svc..."; \
		cd services/$$svc && ruff check app/ && cd ../..; \
	done

format: ## Auto-format all Python services with black
	@for svc in $(SERVICES); do \
		echo "Formatting $$svc..."; \
		cd services/$$svc && black app/ && cd ../..; \
	done

# ── Kubernetes ────────────────────────────────────────────────────────────
k8s-apply: ## Apply all Kubernetes manifests
	kubectl apply -f infrastructure/k8s/namespace.yaml
	kubectl apply -f infrastructure/k8s/configmap.yaml
	kubectl apply -f infrastructure/k8s/secret.yaml
	kubectl apply -f infrastructure/k8s/postgres-deployment.yaml
	@echo "Waiting for postgres..."
	kubectl wait --for=condition=ready pod -l app=postgres -n library-system --timeout=60s
	kubectl apply -f infrastructure/k8s/book-service-deployment.yaml
	kubectl apply -f infrastructure/k8s/member-service-deployment.yaml
	kubectl apply -f infrastructure/k8s/lending-service-deployment.yaml
	kubectl apply -f infrastructure/k8s/api-gateway-deployment.yaml
	kubectl apply -f infrastructure/k8s/frontend-deployment.yaml
	kubectl apply -f infrastructure/k8s/ingress.yaml
	kubectl apply -f infrastructure/k8s/hpa.yaml
	kubectl apply -f infrastructure/k8s/network-policy.yaml
	@echo "\n✅ Kubernetes deployment complete!"

k8s-delete: ## Delete all Kubernetes resources
	kubectl delete namespace library-system --ignore-not-found

k8s-status: ## Show Kubernetes pod status
	kubectl get pods -n library-system

k8s-logs-%: ## Stream K8s logs for a service
	kubectl logs -f -l app=$* -n library-system

# ── Frontend ──────────────────────────────────────────────────────────────
frontend-install: ## Install frontend dependencies
	cd services/frontend && npm install

frontend-dev: ## Start frontend in dev mode
	cd services/frontend && npm run dev

frontend-build: ## Build frontend for production
	cd services/frontend && npm run build

# ── Local Dev ─────────────────────────────────────────────────────────────
dev-book: ## Start book-service locally
	cd services/book-service && python main.py

dev-member: ## Start member-service locally
	cd services/member-service && python main.py

dev-lending: ## Start lending-service locally
	cd services/lending-service && python main.py

dev-gateway: ## Start api-gateway locally
	cd services/api-gateway && uvicorn app.main:app --reload --port 8000

# ── Sample Clients ────────────────────────────────────────────────────────
sample-client: ## Run Python REST sample client
	python scripts/sample_rest_client.py

grpc-client: ## Run Python gRPC sample client
	python scripts/sample_grpc_client.py

# ── Cleanup ───────────────────────────────────────────────────────────────
clean: ## Remove all containers, volumes, and generated proto files
	docker compose down -v --remove-orphans
	find . -path "*/proto_generated/*.py" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	@echo "✅ Cleanup complete"
