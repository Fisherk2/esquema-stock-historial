.PHONY: help install dev lint format test test-cov build docker-up docker-down clean

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

install:
	pip install -r requirements.txt

dev:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

lint:
	ruff check src tests

format:
	black src tests

test:
	pytest

test-cov:
	pytest --cov=src --cov-report=term-missing --cov-report=html

build: lint format test

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache htmlcov .coverage .mypy_cache .ruff_cache
	rm -rf dist build *.egg-info
