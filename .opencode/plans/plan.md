# Implementation Plan: stock-historial F0 — Preparación

## Overview

Scaffold the foundational project structure, development environment, and quality tooling for the stock-historial inventory system. Zero business logic — deliverable is a clean, lintable, testable, containerized skeleton with a working health endpoint.

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

- [ ] Task 1: pyproject.toml + requirements.txt
- [ ] Task 2: Makefile

### Checkpoint: Foundation

- [ ] `pip install -r requirements.txt` succeeds
- [ ] `make lint` and `make test` exit green
- [ ] Review with human before proceeding

### Phase 2: App Skeleton

- [ ] Task 3: src/ package tree + main.py with health endpoint
- [ ] Task 4: tests/conftest.py + health smoke test

### Checkpoint: App Skeleton

- [ ] `make dev` starts FastAPI
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `make test` passes the health smoke test
- [ ] Review with human before proceeding

### Phase 3: Containerization

- [ ] Task 5: Dockerfile + docker-compose.yml
- [ ] Task 6: .env.example + DB connection config

### Checkpoint: Containerization

- [ ] `docker compose up` starts PostgreSQL + app
- [ ] Healthchecks pass for both containers
- [ ] `.env.example` lists all required env vars
- [ ] Review with human before proceeding

### Phase 4: Quality Enforcement

- [ ] Task 7: .pre-commit-config.yaml
- [ ] Task 8: Clean Architecture import rules + CI stub

### Checkpoint: Complete

- [ ] All F0 success criteria met
- [ ] Ready for review

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
