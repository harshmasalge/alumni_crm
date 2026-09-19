# IITGN Alumni & Donor CRM - Development Commands
# Usage: make <target>

.PHONY: help install-api install-web dev-api dev-web check-api check-web db-up db-down db-migrate db-revision test lint format

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# === API (FastAPI) ===
install-api: ## Install API dependencies in virtual environment
	cd apps/api && python -m venv .venv && .venv/bin/pip install -e .[dev]

dev-api: ## Run API with hot reload (requires db-up first)
	cd apps/api && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

check-api: ## Type-check and lint API
	cd apps/api && .venv/bin/ruff check . && .venv/bin/mypy src/app

test-api: ## Run API tests
	cd apps/api && .venv/bin/pytest -v

# === Database ===
db-up: ## Start PostgreSQL and Redis
	docker-compose up -d postgres redis

db-down: ## Stop PostgreSQL and Redis
	docker-compose down

db-migrate: ## Apply Alembic migrations
	cd apps/api && .venv/bin/alembic upgrade head

db-revision: ## Create new Alembic revision (usage: make db-revision msg="description")
	cd apps/api && .venv/bin/alembic revision --autogenerate -m "$(msg)"

db-reset: ## Reset database (down + up + migrate)
	docker-compose down -v
	docker-compose up -d postgres redis
	@echo "Waiting for PostgreSQL..."
	@sleep 5
	cd apps/api && .venv/bin/alembic upgrade head

# === Web (React + Vite) ===
install-web: ## Install web dependencies
	npm install

dev-web: ## Run CRM web with hot reload
	npm run dev:crm

check-web: ## Type-check and build web
	npm run check:crm

# === Full stack ===
install: install-api install-web ## Install all dependencies

dev: ## Run full stack (requires db-up first)
	@echo "Starting API and Web... (run in separate terminals)"
	@echo "  Terminal 1: make dev-api"
	@echo "  Terminal 2: make dev-web"

check: check-api check-web ## Run all checks

# === Docker ===
docker-up: ## Start all services with Docker Compose
	docker-compose up -d

docker-down: ## Stop all services
	docker-compose down

docker-logs: ## Follow Docker Compose logs
	docker-compose logs -f

docker-build: ## Build Docker images
	docker-compose build

# === Git ===
git-status: ## Show git status
	git status

git-diff: ## Show git diff
	git diff

# === Clean ===
clean: ## Clean build artifacts
	rm -rf apps/crm-web/dist apps/crm-web/node_modules
	rm -rf apps/api/.venv apps/api/__pycache__ apps/api/.pytest_cache apps/api/.mypy_cache apps/api/.ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true