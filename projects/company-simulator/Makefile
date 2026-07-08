# =============================================================================
# Company Simulator — Makefile
# Dev environment management: Docker, Python, linting, testing
# =============================================================================

.ONESHELL:
SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

# ─── Project ─────────────────────────────────────────────────────────────
PROJECT := company-simulator
PYTHON := python3

# ─── Targets ─────────────────────────────────────────────────────────────
.PHONY: help setup dev-env \
        docker-up docker-down docker-restart docker-status docker-logs \
        install install-dev \
        db-init db-migrate db-rollback \
        lint format typecheck test test-cov \
        clean nuke

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Quick start:  make dev-env"

# ═════════════════════════════════════════════════════════════════════════
# DEVELOPMENT ENVIRONMENT
# ═════════════════════════════════════════════════════════════════════════

setup: ## One-shot: copy .env, create venv, install deps, start infra
	@echo ">>> Setting up $(PROJECT) dev environment..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example — review and adjust secrets."; \
	else \
		echo ".env already exists, skipping."; \
	fi
	@if [ ! -d .venv ]; then \
		$(PYTHON) -m venv .venv; \
		echo "Created .venv"; \
	else \
		echo ".venv already exists, skipping."; \
	fi
	@source .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@echo ">>> Setup complete. Run 'make dev-env' to start everything."

dev-env: docker-up ## Full dev environment: infra + (future) app

# ═════════════════════════════════════════════════════════════════════════
# DOCKER / INFRASTRUCTURE
# ═════════════════════════════════════════════════════════════════════════

docker-up: ## Start all Docker services (PostgreSQL, Redis, NATS, Qdrant)
	docker compose up -d
	@echo ">>> Services starting... check 'make docker-status'"

docker-down: ## Stop and remove all Docker containers
	docker compose down

docker-restart: docker-down docker-up ## Restart all Docker services

docker-status: ## Show container status and resource usage
	@docker compose ps --all
	@echo ""
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(shell docker compose ps -q) 2>/dev/null || true

docker-logs: ## Tail logs from all services (or SERVICE=redis make docker-logs)
	docker compose logs --tail=50 -f $(SERVICE)

docker-reset: ## Wipe all volumes (data loss!) and restart fresh
	docker compose down -v
	make docker-up

# ═════════════════════════════════════════════════════════════════════════
# PYTHON / DEPENDENCIES
# ═════════════════════════════════════════════════════════════════════════

install: ## Install production dependencies
	pip install -r requirements.txt

install-dev: install ## Install dev dependencies too (uncomment dev group in requirements.txt)
	pip install pytest pytest-asyncio pytest-cov httpx factory-boy faker ruff mypy

# ═════════════════════════════════════════════════════════════════════════
# DATABASE
# ═════════════════════════════════════════════════════════════════════════

db-init: ## Initialize Alembic and stamp head
	alembic init -t async migrations
	alembic stamp head

db-migrate: ## Generate a new migration (MSG="description" make db-migrate)
	alembic revision --autogenerate -m "$(MSG)"

db-rollback: ## Rollback last migration
	alembic downgrade -1

# ═════════════════════════════════════════════════════════════════════════
# CODE QUALITY
# ═════════════════════════════════════════════════════════════════════════

lint: ## Lint with ruff
	ruff check . --fix

format: ## Format with ruff
	ruff format .

typecheck: ## Static type check with mypy
	mypy .

test: ## Run all tests (fast)
	python -m pytest -xvs

test-cov: ## Run tests with coverage report
	python -m pytest --cov=app --cov-report=term --cov-report=html

# ═════════════════════════════════════════════════════════════════════════
# ARCHITECTURE ENFORCEMENT
# ═════════════════════════════════════════════════════════════════════════

validate-modules: ## Validate all module.json manifests against schema + deps
	python scripts/validate-modules.py

check-layers: ## Enforce layer import direction (no upward imports)
	python scripts/check-layer-boundary.py

check-circular: ## Detect circular imports between modules
	python scripts/check-circular-imports.py

check-api-surface: ## Verify public API export limits per module
	python scripts/check-api-surface.py

check-internal-imports: ## Block imports from other modules' internal/ paths
	python scripts/check-internal-imports.py

check-adr: ## Verify new modules have an Architecture Decision Record
	python scripts/check-adr.py

validate: validate-modules check-layers check-circular check-api-surface check-internal-imports check-adr ## Run ALL architecture validation checks

# ═════════════════════════════════════════════════════════════════════════
# CLEANUP
# ═════════════════════════════════════════════════════════════════════════

clean: ## Remove Python cache, build artifacts, and .venv
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
	find . -type f -name '*.pyo' -delete 2>/dev/null || true
	find . -type l -name '*.so' -delete 2>/dev/null || true
	rm -rf .venv *.egg-info dist build

nuke: clean docker-down ## Full reset: clean everything + wipe Docker volumes
	docker compose down -v
	rm -f .env
	@echo "All data wiped. Run 'make setup' to start fresh."
