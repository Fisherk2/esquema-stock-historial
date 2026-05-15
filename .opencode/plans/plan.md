# Implementation Plan: stock-historial F0 — Preparación

## Overview

Scaffold the foundational project structure, development environment, and quality tooling for the stock-historial inventory system. Zero business logic — deliverable is a clean, lintable, testable, containerized skeleton with a working health endpoint.

**Status:** COMPLETED (2026-05-14)

## Architecture Decisions

- **Vertical slicing by working state** — each task leaves the system verifiably runnable, not just "files exist"
- **pyproject.toml as single source of truth** for ruff, black, pytest, mypy config (no scattered configs)
- **FastAPI app factory pattern** — `create_app()` in `src/main.py` for testability and DI
- **src/core/config.py for Settings** — pydantic-settings class in its own `core/` package, easily importable by all layers
- **Docker Compose dev-only** — PostgreSQL 16 + app with healthchecks; no prod compose yet (deferred to F7)
- **Pre-commit as quality gate** — ruff + black on every commit, no manual linting

## Dependency Graph

```
pyproject.toml + requirements.txt
│
├── Makefile
├── src/__init__.py tree + main.py (FastAPI app)
│   └── tests/conftest.py + health smoke test
│
├── Dockerfile + docker-compose.yml + .env.example
│
└── .pre-commit-config.yaml + CI workflow
```

## Task List

### Phase 1: Foundation

- [x] Task 1: pyproject.toml + requirements.txt
- [x] Task 2: Makefile

### Checkpoint: Foundation

- [x] `pip install -r requirements.txt` succeeds
- [x] `make lint` and `make test` exit green
- [x] Review with human before proceeding

### Phase 2: App Skeleton

- [x] Task 3: src/ package tree + main.py with health endpoint
- [x] Task 4: tests/conftest.py + health smoke test

### Checkpoint: App Skeleton

- [x] `make dev` starts FastAPI
- [x] `GET /health` returns `{"status": "ok"}`
- [x] `make test` passes the health smoke test
- [x] Review with human before proceeding

### Phase 3: Containerization

- [x] Task 5: Dockerfile + docker-compose.yml
- [x] Task 6: .env.example + DB connection config

### Checkpoint: Containerization

- [x] `docker compose up` starts PostgreSQL + app
- [x] Healthchecks pass for both containers
- [x] `.env.example` lists all required env vars
- [x] Review with human before proceeding

### Phase 4: Quality Enforcement

- [x] Task 7: .pre-commit-config.yaml
- [x] Task 8: Clean Architecture import rules + CI stub

### Checkpoint: Complete

- [x] All F0 success criteria met
- [x] Ready for review

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| ruff `banned-api` doesn't support custom import rules | Med | Fall back to `import-linter` or manual convention documented in code style |
| asyncpg pool initialization in F0 without real DB schema | Low | Placeholder only; connects on startup event, graceful fallback if DB unreachable |
| Pre-commit hooks slow down commit workflow | Low | Use ruff's speed; skip heavy hooks; test-only on CI |
| pyproject.toml config conflicts between ruff and black | Low | ruff's `lint` section doesn't overlap with black; test with `make lint && make format` |

## Open Questions

1. Should `mypy` strict mode be enforced in CI, or start with basic mode?
2. Should we use `alembic` for migration management or raw numbered SQL files?
3. Is `structlog` preferred over stdlib `logging` from day one?
4. Should the health endpoint also check DB connectivity (`SELECT 1`) in F0 or defer to F1?
