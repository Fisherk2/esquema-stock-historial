# AGENTS.md

> **Note:** This document is the project's architectural source of truth. For execution order and spec traceability, see [WORKFLOW.md](WORKFLOW.md).

Inventory management system based on an **Immutable Source of Truth** — each movement is atomic and unalterable, with historical stock queries in `<100ms` via materialized views.

**Current phase:** F7 — Deployment & Documentation ✅ Completed (v1.0.0)

## Quick Reference

- **Runtime:** Python 3.12+ · `pip install -r requirements.txt`
- **Build:** `make build`
- **Test:** `make test` (unit + integration + e2e)
- **Lint:** `make lint` (ruff + black --check)
- **DB:** PostgreSQL 16+ · `asyncpg`
- **Framework:** FastAPI + Pydantic + APScheduler

## Detailed Guidelines

- [Architecture and Design](docs/agents/architecture-design.md) — Clean Architecture, patterns, layers
- [Development Guidelines](docs/agents/development-guidelines.md) — SOLID, structure, pre-commit, errors
- [Testing Strategy](docs/agents/testing-strategy.md) — Phases, frameworks, metrics, mocking
- [Security and Prohibitions](docs/agents/security-prohibitions.md) — Validation, secrets, prohibited practices
- [Performance Optimization](docs/agents/performance-optimisation.md) — SQL, views, indexes, latency
- [Tooling and CI/CD](docs/agents/tooling-ci-cd.md) — Ruff, Black, pytest, GitHub Actions, Docker
