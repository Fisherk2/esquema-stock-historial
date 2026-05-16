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
| Spec-30 | Implementación Repositorio | `asyncpg` wrapper, SQL explícito, mapeo DTO<->Row | Alta | F3 | `src/infrastructure/repositories/` | Spec-12, Spec-22 | [0/6] | Pendiente |
| Spec-31 | Vistas Materializadas | `mv_stock_historical`, `REFRESH CONCURRENTLY`, fallback | Alta | F3 | `migrations/`, `specs/` (materialized.sql) | Spec-12, Spec-30 | [0/5] | Pendiente |
| Spec-32 | Unit of Work & Transacciones | Context manager `asyncpg.transaction()`, commit/rollback | Media | F3 | `src/infrastructure/db/uow.py` | Spec-30 | [0/3] | Pendiente |
| Spec-40 | Casos de Uso (Application) | `CreateMovementUseCase`, `QueryStockAtDateUseCase` | Alta | F4 | `src/application/use_cases/` | Spec-21, Spec-22, Spec-32 | [0/5] | Bloq. |
| Spec-41 | DTOs & Validación Pydantic | Input/Output models, validación estricta, serialización JSON | Alta | F4 | `src/application/dtos/` | Spec-40 | [0/4] | Bloq. |
| Spec-42 | Rutas FastAPI /v1/ & OpenAPI | Endpoints REST, dependency injection, error mapping | Alta | F4 | `src/adapters/api/routers/`, `src/main.py` | Spec-40, Spec-41 | [0/5] | Bloq. |
| Spec-50 | Integración APScheduler | Cron job interno, política de refresh, isolation de resources | Media | F5 | `src/infrastructure/scheduler/`, `specs/` (scheduler.md) | Spec-31, Spec-42 | [0/4] | Bloq. |
| Spec-51 | Optimistic Concurrency & Retry | Decorador `@retry`, backoff exponencial, manejo `HTTP 409` | Alta | F5 | `src/application/middleware/`, `src/domain/exceptions/` | Spec-40, Spec-50 | [0/3] | Bloq. |
| Spec-52 | Logging Estructurado & Errors | `structlog`/`logging` JSON, timeouts, circuit breakers | Media | F5 | `src/core/logging.py`, `src/core/config.py` | Spec-42, Spec-51 | [0/4] | Bloq. |
| Spec-60 | Tests Unitarios | Cobertura dominio/app, mocks de protocolos, `pytest` | Alta | F6 | `tests/unit/`, `tests/fixtures/` | Spec-21, Spec-22, Spec-40 | [0/5] | Bloq. |
| Spec-61 | Tests Integración | `testcontainers.postgres`, seed DB, validación SQL real | Alta | F6 | `tests/integration/` | Spec-30, Spec-31, Spec-60 | [0/6] | Bloq. |
| Spec-62 | Tests E2E & Latencia <100ms | `httpx` client, contratos OpenAPI, load test | Alta | F6 | `tests/e2e/`, `specs/` (performance.md) | Spec-42, Spec-61 | [0/5] | Bloq. |
| Spec-63 | Pruebas de Seguridad & OWASP | Inyección SQL, validación inputs, rate limit | Media | F6 | `tests/security/`, `specs/` (security.md) | Spec-42, Spec-52 | [0/4] | Bloq. |
| Spec-70 | Dockerfile & Docker Compose Prod | Multi-stage build, `docker-compose.prod.yml`, healthchecks | Alta | F7 | `Dockerfile`, `docker-compose.prod.yml` | Spec-42, Spec-50, Spec-62 | [0/5] | Bloq. |
| Spec-71 | README Técnico & Demo Script | Instrucciones setup, arquitectura, script demo | Media | F7 | `README.md`, `scripts/demo.sh`, `docs/` | Spec-62, Spec-70 | [0/4] | Bloq. |
| Spec-72 | CI/CD Pipeline | GitHub Actions: lint, test, coverage, build, deploy | Alta | F7 | `.github/workflows/ci.yml` | Spec-03, Spec-60, Spec-70 | [0/5] | Bloq. |

> **Advertencias:**
> 1. Ningún spec inicia hasta que sus dependencias estén en estado Completado.
> 2. Cada spec debe tener su archivo `specs/SPEC-XX.md` con contratos y criterios de aceptación antes de escribir código.
> 3. Checklist se actualiza en tiempo real: `[X/Y]` según avance.
> 4. Bloqueos se documentan en notas. Si un spec lleva >2 días en pendiente, se escala a revisión.
