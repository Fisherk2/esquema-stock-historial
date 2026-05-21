# Specs Tracking

Reference directory: `specs/` (each spec with contracts, examples, and validated SQL).

| ID | Name | Description | Priority | Phase | Involved Files | Dependencies | Checklist | Status |
|----|--------|-------------|-----------|------|----------------------|--------------|-----------|--------|
| Spec-01 | Structure and conventions | Clean Architecture tree, naming, `.gitignore` | High | F0 | `src/`, `tests/`, `.gitignore`, `pyproject.toml` | None | [4/4] | Completed |
| Spec-02 | Development environment | Docker Compose dev, `.env.example`, `Makefile` | High | F0 | `docker-compose.yml`, `.env.example`, `Makefile`, `requirements.txt` | Spec-01 | [3/3] | Completed |
| Spec-03 | Quality and automation | `ruff`, `black`, `pytest`, pre-commit, CI/CD | Medium | F0 | `.pre-commit-config.yaml`, `pyproject.toml`, `.github/workflows/` | Spec-01, Spec-02 | [5/5] | Completed |
| Spec-04 | Initial documentation | `AGENTS.md`, `WORKFLOW.md`, `README.md`, `specs/` | High | F0 | `AGENTS.md`, `WORKFLOW.md`, `README.md`, `specs/` | Spec-01 | [4/4] | Completed |
| Spec-10 | DB Configuration | PostgreSQL 16+, `asyncpg`, connection pooling, healthcheck | High | F1 | `src/infrastructure/db/`, `docker-compose.yml` | Spec-02 | [3/3] | Completed |
| Spec-11 | Schema and Migrations | Tables `products`, `movements`, constraints, FK, 3NF | High | F1 | `migrations/`, `specs/` (DDL) | Spec-10 | [6/6] | Completed |
| Spec-12 | Indexes and Base Optimization | Composite indexes, partial, `EXPLAIN` baseline, seed data | Medium | F1 | `migrations/`, `specs/` (indexes.sql) | Spec-11 | [4/4] | Completed |
| Spec-20 | Entities (Domain) | Classes `Product`, `Movement`, value objects, domain exceptions | High | F2 | `src/domain/entities/`, `src/domain/exceptions/` | Spec-11 | [5/5] | Completed |
| Spec-21 | Business Rules | Immutability validation, non-negative stock, transactionality | High | F2 | `src/domain/rules/`, `src/domain/protocols/` | Spec-20 | [4/4] | Completed |
| Spec-22 | Protocols/Interfaces | `IMovementRepository`, `IStockQueryRepo`, `IUseCase` | High | F2 | `src/domain/ports/`, `specs/` (interfaces.md) | Spec-20 | [3/3] | Completed |
| Spec-30 | Repository Implementation | `asyncpg` wrapper, explicit SQL, DTO<->Row mapping, pagination in categories | High | F3 | `src/infrastructure/repositories/` | Spec-12, Spec-22 | [7/7] | Completed |
| Spec-31 | Materialized Views | `mv_stock_historical`, `REFRESH CONCURRENTLY`, fallback | High | F3 | `migrations/`, `specs/` (materialized.sql) | Spec-12, Spec-30 | [4/4] | Completed |
| Spec-32 | Unit of Work & Transactions | Context manager `asyncpg.transaction()`, commit/rollback | Medium | F3 | `src/infrastructure/db/uow.py` | Spec-30 | [3/3] | Completed |
| Spec-40 | Use Cases (Application) | `CreateMovementUseCase`, `QueryStockAtDateUseCase` | High | F4 | `src/application/use_cases/` | Spec-21, Spec-22, Spec-32 | [5/5] | Completed |
| Spec-41 | DTOs & Pydantic Validation | Input/Output models, strict validation, JSON serialization, `extra="forbid"`, `StrEnum` | High | F4 | `src/application/dtos/` | Spec-40 | [4/4] | Completed |
| Spec-42 | FastAPI Routes /v1/ & OpenAPI | REST endpoints, dependency injection, error mapping (traceback verification), pagination DB categories, security headers, timezone handling | High | F4 | `src/adapters/api/routers/`, `src/main.py` | Spec-40, Spec-41 | [5/5] | Completed |
| Spec-50 | APScheduler Integration | Internal cron job, refresh policy, resource isolation, statement_timeout inherited from pool | Medium | F5 | `src/infrastructure/scheduler/scheduler.py`, `src/core/config.py`, `src/main.py` | Spec-31, Spec-42 | [6/6] | Completed |
| Spec-51 | Optimistic Concurrency & Retry | Decorator `@retry` (requires explicit `exceptions`), exponential backoff, `HTTP 409` handling | High | F5 | `src/core/retry.py`, `src/domain/exceptions/concurrency_conflict.py`, `src/adapters/api/middleware/error_handler.py` | Spec-40, Spec-50 | [7/7] | Completed |
| Spec-52 | Structured Logging & Errors | JSON `logging`, request ID middleware, `statement_timeout` via pool `server_settings`, double-init guard | Medium | F5 | `src/infrastructure/logging/config.py`, `src/adapters/api/middleware/request_logging.py`, `src/core/config.py`, `src/infrastructure/db/connection.py` | Spec-42, Spec-51 | [8/8] | Completed |
| Spec-60 | Unit Tests — Hypothesis + mypy strict | Property-based testing (Hypothesis max_examples=100, seed=0), mypy strict in src/, edge cases in use cases, coverage domain/≥90% app/≥85% | High | F6 | `tests/unit/strategies.py`, `tests/unit/domain/`, `tests/unit/application/use_cases/`, `pyproject.toml`, `requirements.txt`, `Makefile` | Spec-21, Spec-22, Spec-40 | [10/10] | Completed |
| Spec-61 | Integration Tests — Edge Cases | Repository edge cases (not found, pagination, future date), MV with massive data (100+), UoW edge cases, API boundary tests, security headers tests, pagination bounds, timezone handling | High | F6 | `tests/integration/*_edge.py`, `tests/integration/helpers.py`, `tests/integration/test_mv_stock_edge.py`, `tests/integration/test_uow_edge.py`, `tests/integration/api/test_security_headers.py`, `tests/integration/api/test_pagination_and_timezone.py` | Spec-30, Spec-31, Spec-60 | [8/8] | Completed |
| Spec-62 | E2E Tests & Latency <100ms | pytest-benchmark SLA p95<100ms, complete HTTP flows, OpenAPI contracts (Pydantic model_validate), SLA gate hook | High | F6 | `tests/e2e/conftest.py`, `tests/e2e/test_stock_latency.py`, `tests/e2e/test_full_flows.py`, `tests/e2e/test_openapi_contracts.py`, `pyproject.toml`, `requirements.txt` | Spec-42, Spec-61 | [12/12] | Completed |
| Spec-63 | Security Tests — SQLi + Input Validation | OWASP SQL injection payloads (path/query/body/repo), input boundary tests, malformed payloads, Unicode edge cases, error leakage (body only), immutability 405 | Medium | F6 | `tests/security/__init__.py`, `tests/security/conftest.py`, `tests/security/test_sql_injection.py`, `tests/security/test_input_validation.py`, `tests/security/test_error_leakage.py` | Spec-42, Spec-52 | [11/11] | Completed |
| Spec-70 | Dockerfile & Docker Compose Prod | Non-root user, OCI labels, .dockerignore, prod compose, .env.example 17 vars, Makefile +commands | High | F7 | `Dockerfile`, `.dockerignore`, `docker-compose.prod.yml`, `.env.example`, `Makefile` | Spec-42, Spec-50, Spec-62 | [17/17] | Completed |
| Spec-71 | Technical README & Demo Script & Documentation | README v1.0.0, ARCHITECTURE.md (3 Mermaid), API_REFERENCE.md (11 endpoints), SETUP.md, demo.sh, CONTRIBUTING.md | Medium | F7 | `README.md`, `docs/ARCHITECTURE.md`, `docs/API_REFERENCE.md`, `docs/SETUP.md`, `scripts/demo.sh`, `CONTRIBUTING.md` | Spec-62, Spec-70 | [12/12] | Completed |
| Spec-72 | CI/CD Pipeline | 5 sequential gates (lint→typecheck→test→coverage→docker-build), coverage sub-gates, Docker build with GHA cache | High | F7 | `.github/workflows/ci.yml` | Spec-03, Spec-60, Spec-70 | [14/14] | Completed |

> **Warnings:**
> 1. No spec starts until its dependencies are in Completed status.
> 2. Each spec must have its `specs/SPEC-XX.md` file with contracts and acceptance criteria before writing code.
> 3. Checklist is updated in real-time: `[X/Y]` as progress is made.
> 4. Blockers are documented in notes. If a spec is pending for >2 days, it is escalated for review.
