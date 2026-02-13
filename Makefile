.PHONY: help install dev up down logs migrate test lint format clean

help:
	@echo "GeneNote Backend"
	@echo ""
	@echo "Setup:"
	@echo "  make install     - Install dependencies"
	@echo "  make dev         - Start API server (requires 'make up' first)"
	@echo ""
	@echo "Docker:"
	@echo "  make up          - Start PostgreSQL + Kafka"
	@echo "  make down        - Stop services"
	@echo "  make logs        - View logs"
	@echo ""
	@echo "Database:"
	@echo "  make migrate     - Run migrations"
	@echo "  make migrate-new - Create new migration"
	@echo "  make db-shell    - Open psql shell"
	@echo ""
	@echo "Quality:"
	@echo "  make test        - Run tests"
	@echo "  make test-cov    - Run tests with coverage"
	@echo "  make lint        - Check code (ruff + mypy)"
	@echo "  make format      - Format code"
	@echo "  make clean       - Remove cache files"

# ========== Setup ==========
install:
	poetry install

dev:
	poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# ========== Docker ==========
up:
	docker compose up -d db kafka

down:
	docker compose down

logs:
	docker compose logs -f

# ========== Database ==========
migrate:
	poetry run alembic upgrade head

migrate-new:
	@read -p "Migration message: " msg; \
	poetry run alembic revision --autogenerate -m "$$msg"

db-shell:
	docker compose exec db psql -U genenote -d genenote

# ========== Testing ==========
test:
	poetry run pytest tests/ -v

test-cov:
	poetry run pytest tests/ -v --cov=src --cov-report=html

# ========== Code Quality ==========
lint:
	poetry run ruff check src tests
	poetry run mypy src

format:
	poetry run ruff check src tests --fix
	poetry run ruff format src tests

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage 2>/dev/null || true
