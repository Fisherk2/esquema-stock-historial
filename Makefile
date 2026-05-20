# Makefile — Interfaz unificada de comandos para desarrollo.
# Centraliza todas las operaciones comunes: instalación, linting,
# testing, Docker y limpieza de artefactos.
#
# Uso: make <comando> (ej: make lint, make test)
# Ver todos los comandos: make help

.PHONY: help install dev lint format test test-cov build docker-up docker-down docker-prod-up docker-prod-down clean migrate seed typecheck demo

help:
	@echo "Available commands:"
	@echo "  install     Install dependencies"
	@echo "  dev         Start FastAPI development server"
	@echo "  lint        Run ruff linter"
	@echo "  format      Run black formatter"
	@echo "  test        Run pytest"
	@echo "  test-cov    Run pytest with coverage"
	@echo "  build       Run lint + format + test"
	@echo "  docker-up   Start Docker Compose services"
	@echo "  docker-down Stop Docker Compose services"
	@echo "  clean       Remove cache and build artifacts"
	@echo "  migrate     Run database migrations"
	@echo "  seed        Insert seed data for development"
	@echo "  typecheck   Run mypy strict type checking"
	@echo "  demo        Run demo script (scripts/demo.sh)"
	@echo "  docker-prod-up  Start Docker Compose production stack"
	@echo "  docker-prod-down Stop Docker Compose production stack"

install:
	python -m pip install -r requirements.txt

dev:
	python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check src tests

format:
	python -m black src tests

test:
	python -m pytest

test-cov:
	python -m pytest --cov=src --cov-report=term-missing --cov-report=html

typecheck:
	python -m mypy src/ --strict

# Gate de calidad pre-commit: lint + format + test deben pasar antes de commitear
build: lint format test

docker-up:
	docker compose up -d

docker-down:
	docker compose down

# Elimina caché y artefactos de build: __pycache__, .pyc, .pytest_cache,
# reportes de cobertura, caché de mypy/ruff, y directorios de distribución.
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache htmlcov .coverage .mypy_cache .ruff_cache
	rm -rf dist build *.egg-info

migrate:
	python -m src.infrastructure.db.migrate

seed:
	python -m src.infrastructure.db.seed

demo:
	bash scripts/demo.sh

docker-prod-up:
	docker compose -f docker-compose.prod.yml up -d

docker-prod-down:
	docker compose -f docker-compose.prod.yml down
