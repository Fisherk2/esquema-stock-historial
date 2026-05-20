# Seguimiento de Specs

Directorio de referencia: `specs/` (cada spec con contratos, ejemplos y SQL validado).

| ID | Nombre | Descripción | Prioridad | Fase | Archivos Involucrados | Dependencias | Checklist | Estado |
|----|--------|-------------|-----------|------|----------------------|--------------|-----------|--------|
| Spec-01 | Estructura y convenciones | Árbol Clean Architecture, naming, `.gitignore` | Alta | F0 | `src/`, `tests/`, `.gitignore`, `pyproject.toml` | Ninguna | [4/4] | Completado |
| Spec-02 | Entorno de desarrollo | Docker Compose dev, `.env.example`, `Makefile` | Alta | F0 | `docker-compose.yml`, `.env.example`, `Makefile`, `requirements.txt` | Spec-01 | [3/3] | Completado |
| Spec-03 | Calidad y automatización | `ruff`, `black`, `pytest`, pre-commit, CI/CD | Media | F0 | `.pre-commit-config.yaml`, `pyproject.toml`, `.github/workflows/` | Spec-01, Spec-02 | [5/5] | Completado |
| Spec-04 | Documentación inicial | `AGENTS.md`, `WORKFLOW.md`, `README.md`, `specs/` | Alta | F0 | `AGENTS.md`, `WORKFLOW.md`, `README.md`, `specs/` | Spec-01 | [4/4] | Completado |
| Spec-10 | Configuración DB | PostgreSQL 16+, `asyncpg`, connection pooling, healthcheck | Alta | F1 | `src/infrastructure/db/`, `docker-compose.yml` | Spec-02 | [3/3] | Completado |
| Spec-11 | Esquema y Migraciones | Tablas `products`, `movements`, constraints, FK, 3NF | Alta | F1 | `migrations/`, `specs/` (DDL) | Spec-10 | [6/6] | Completado |
| Spec-12 | Índices y Optimización Base | Índices compuestos, parciales, `EXPLAIN` baseline, seed data | Media | F1 | `migrations/`, `specs/` (indexes.sql) | Spec-11 | [4/4] | Completado |
| Spec-20 | Entidades (Domain) | Clases `Product`, `Movement`, value objects, excepciones de dominio | Alta | F2 | `src/domain/entities/`, `src/domain/exceptions/` | Spec-11 | [5/5] | Completado |
| Spec-21 | Reglas de Negocio | Validación inmutabilidad, stock no negativo, transaccionalidad | Alta | F2 | `src/domain/rules/`, `src/domain/protocols/` | Spec-20 | [4/4] | Completado |
| Spec-22 | Protocolos/Interfaces | `IMovementRepository`, `IStockQueryRepo`, `IUseCase` | Alta | F2 | `src/domain/ports/`, `specs/` (interfaces.md) | Spec-20 | [3/3] | Completado |
| Spec-30 | Implementación Repositorio | `asyncpg` wrapper, SQL explícito, mapeo DTO<->Row | Alta | F3 | `src/infrastructure/repositories/` | Spec-12, Spec-22 | [7/7] | Completado |
| Spec-31 | Vistas Materializadas | `mv_stock_historical`, `REFRESH CONCURRENTLY`, fallback | Alta | F3 | `migrations/`, `specs/` (materialized.sql) | Spec-12, Spec-30 | [4/4] | Completado |
| Spec-32 | Unit of Work & Transacciones | Context manager `asyncpg.transaction()`, commit/rollback | Media | F3 | `src/infrastructure/db/uow.py` | Spec-30 | [3/3] | Completado |
| Spec-40 | Casos de Uso (Application) | `CreateMovementUseCase`, `QueryStockAtDateUseCase` | Alta | F4 | `src/application/use_cases/` | Spec-21, Spec-22, Spec-32 | [5/5] | Completado |
| Spec-41 | DTOs & Validación Pydantic | Input/Output models, validación estricta, serialización JSON | Alta | F4 | `src/application/dtos/` | Spec-40 | [4/4] | Completado |
| Spec-42 | Rutas FastAPI /v1/ & OpenAPI | Endpoints REST, dependency injection, error mapping | Alta | F4 | `src/adapters/api/routers/`, `src/main.py` | Spec-40, Spec-41 | [5/5] | Completado |
| Spec-50 | Integración APScheduler | Cron job interno, política de refresh, isolation de resources | Media | F5 | `src/infrastructure/scheduler/scheduler.py`, `src/core/config.py`, `src/main.py` | Spec-31, Spec-42 | [6/6] | Completado |
| Spec-51 | Optimistic Concurrency & Retry | Decorador `@retry`, backoff exponencial, manejo `HTTP 409` | Alta | F5 | `src/core/retry.py`, `src/domain/exceptions/concurrency_conflict.py`, `src/adapters/api/middleware/error_handler.py` | Spec-40, Spec-50 | [7/7] | Completado |
| Spec-52 | Logging Estructurado & Errors | `logging` JSON, request ID middleware, `statement_timeout` | Media | F5 | `src/infrastructure/logging/config.py`, `src/adapters/api/middleware/request_logging.py`, `src/core/config.py` | Spec-42, Spec-51 | [8/8] | Completado |
| Spec-60 | Tests Unitarios — Hypothesis + mypy strict | Property-based testing (Hypothesis max_examples=100, seed=0), mypy strict en src/, edge cases en use cases, coverage domain/≥90% app/≥85% | Alta | F6 | `tests/unit/strategies.py`, `tests/unit/domain/`, `tests/unit/application/use_cases/`, `pyproject.toml`, `requirements.txt`, `Makefile` | Spec-21, Spec-22, Spec-40 | [10/10] | Completado |
| Spec-61 | Tests Integración — Edge Cases | Edge cases repositorios (not found, paginación, fecha futura), MV con datos masivos (100+), UoW edge cases, API boundary tests | Alta | F6 | `tests/integration/*_edge.py`, `tests/integration/helpers.py`, `tests/integration/test_mv_stock_edge.py`, `tests/integration/test_uow_edge.py` | Spec-30, Spec-31, Spec-60 | [8/8] | Completado |
| Spec-62 | Tests E2E & Latencia <100ms | pytest-benchmark SLA p95<100ms, flujos HTTP completos, contratos OpenAPI (Pydantic model_validate), SLA gate hook | Alta | F6 | `tests/e2e/conftest.py`, `tests/e2e/test_stock_latency.py`, `tests/e2e/test_full_flows.py`, `tests/e2e/test_openapi_contracts.py`, `pyproject.toml`, `requirements.txt` | Spec-42, Spec-61 | [12/12] | Completado |
| Spec-63 | Pruebas de Seguridad — SQLi + Input Validation | OWASP SQL injection payloads (path/query/body/repo), input boundary tests, malformed payloads, Unicode edge cases, error leakage (body only), immutability 405 | Media | F6 | `tests/security/__init__.py`, `tests/security/conftest.py`, `tests/security/test_sql_injection.py`, `tests/security/test_input_validation.py`, `tests/security/test_error_leakage.py` | Spec-42, Spec-52 | [11/11] | Completado |
| Spec-70 | Dockerfile & Docker Compose Prod | Non-root user, OCI labels, .dockerignore, prod compose, .env.example 17 vars, Makefile +commands | Alta | F7 | `Dockerfile`, `.dockerignore`, `docker-compose.prod.yml`, `.env.example`, `Makefile` | Spec-42, Spec-50, Spec-62 | [17/17] | Completado |
| Spec-71 | README Técnico & Demo Script & Documentación | README v1.0.0, ARCHITECTURE.md (3 Mermaid), API_REFERENCE.md (11 endpoints), SETUP.md, demo.sh, CONTRIBUTING.md | Media | F7 | `README.md`, `docs/ARCHITECTURE.md`, `docs/API_REFERENCE.md`, `docs/SETUP.md`, `scripts/demo.sh`, `CONTRIBUTING.md` | Spec-62, Spec-70 | [12/12] | Completado |
| Spec-72 | CI/CD Pipeline | 5 gates secuenciales (lint→typecheck→test→coverage→docker-build), coverage sub-gates, Docker build con cache GHA | Alta | F7 | `.github/workflows/ci.yml` | Spec-03, Spec-60, Spec-70 | [14/14] | Completado |

> **Advertencias:**
> 1. Ningún spec inicia hasta que sus dependencias estén en estado Completado.
> 2. Cada spec debe tener su archivo `specs/SPEC-XX.md` con contratos y criterios de aceptación antes de escribir código.
> 3. Checklist se actualiza en tiempo real: `[X/Y]` según avance.
> 4. Bloqueos se documentan en notas. Si un spec lleva >2 días en pendiente, se escala a revisión.
