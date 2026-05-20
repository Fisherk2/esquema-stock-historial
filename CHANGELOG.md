# Registro de Cambios (Changelog)

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Sin Lanzar]

### [0.6.0] — 2026-05-20 — F6: Testing Integral (Completado)

#### Agregado
- **Hypothesis Property-Based Testing:** Strategies centralizadas (`tests/unit/strategies.py`) para Quantity, SKU, MovementType, stock_delta. `max_examples=100` con `--hypothesis-seed=0` para reproducibilidad. Profiles `ci` (100) y `dev` (1000).
- **mypy strict:** Activado `strict=true` en `pyproject.toml` para `src/`. Tests con override `strict=false`. 74 archivos sin errores.
- **Edge Cases de Integración:** Archivos `*_edge.py` separados para cada repositorio, MV con datos masivos (100+ movimientos), UoW edge cases (rollback, conexión compartida, release), API boundary tests (IDs inexistentes, parámetros inválidos, duplicados).
- **E2E Tests con SLA:** `pytest-benchmark` para medir latencia. SLA gate p95<100ms en `/v1/stock/{id}/current` y `/v1/stock/{id}/at-date`. Flujos HTTP completos (categoría → producto → movimiento → stock). Contratos OpenAPI con Pydantic `model_validate()`.
- **Pruebas de Seguridad OWASP:** SQL injection en 4 capas (path params, query params, body fields, repository-level). Input validation boundary tests (tipos incorrectos, rangos, campos extra, metadata anidada, payloads malformados, Unicode). Error leakage tests (verificación de patrones de stack trace, SQL, file paths). Inmutabilidad enforcement (PUT/PATCH/DELETE → 405).

#### Validación
- 205 tests unitarios pasando (100% pass)
- Domain coverage: 99.60% (target ≥90%)
- Application coverage: 99.01% (target ≥85%)
- Global coverage: 99.34% (target ≥80%)
- `make lint` sin errores (41 errores corregidos)
- `make typecheck` (mypy --strict) limpio: 74 archivos
- Version actualizada a 0.6.0

#### Corregido
- 41 errores de ruff corregidos (E402, I001, F401, F811, TC002/3/4, UP037, E501, RUF003)
- Black formatting aplicado a 7 archivos

### [0.5.0] — 2026-05-19 — F5: Scheduler & Concurrencia (Completado)

#### Agregado
- **APScheduler:** Cron job interno para refresh de vista materializada, isolation de resources
- **Retry con Backoff Exponencial:** Decorador `@retry`, manejo de fallos transitorios, `HTTP 409` por confl icto de concurrencia
- **Logging Estructurado:** Request ID middleware, `logging` JSON, `statement_timeout` configurado

#### Validación
- 282 tests total (194 unit + 88 integration, 100% pass, ~20s)
- `make lint` sin errores

### [0.4.0] — 2026-05-19 — F4: Capa API (Completado)

#### Agregado
- **6 Use Cases:** `CreateMovementUseCase`, `GetMovementByIdUseCase`, `ListMovementsByProductUseCase`, `GetStockAtDateUseCase`, `GetCurrentStockUseCase`, `CreateCategoryUseCase`, `ListCategoriesUseCase` — Clean Architecture con DI pattern
- **5 DTOs Pydantic:** Input/Output models con `strict=True`, validación automática, enums con coerción
- **4 Routers FastAPI:** `/v1/categories`, `/v1/products`, `/v1/movements`, `/v1/stock` — 10 endpoints operativos
- **Error Mapping Middleware:** Domain exceptions → HTTP status codes (400, 404, 409, 422)
- **Dependency Injection:** Factory functions en `dependencies.py`, `Annotated[type, Depends()]`
- **34 API Integration Tests:** End-to-end HTTP contra PostgreSQL real con testcontainers
- **5 Error Mapping Tests:** Validación de excepción → HTTP status code mapping

#### Optimizado
- **Testcontainers:** De 88 contenedores/session a **1 contenedor/session** — tiempo de integración de ~20 min a ~20s (~99% menos overhead)
- `db_pool` session-scoped + `db_clean` function-scoped con TRUNCATE + re-seed

#### Corregido
- Protocol imports movidos fuera de `TYPE_CHECKING` en adapters para FastAPI `Annotated[type, Depends()]`
- JSONB string parsing en mappers (asyncpg 0.31 + Python 3.14 devuelve JSONB como string)
- Materialized view fallback para productos nuevos sin refresh
- Enum strict mode con `field_validator(mode="before")` para coerción de strings
- `asyncio_default_fixture_loop_scope` + `test_loop_scope` → `"session"` para compatibilidad con fixtures async session-scoped

#### Validación
- 235 tests (147 unit + 88 integration, 100% pass, ~20s)
- `make lint` sin errores
- 17/24 specs completados al cierre de F4

### [0.4.0] — 2026-05-18 — F3: Adaptadores de Datos (Completado)

#### Agregado
- **4 Repositorios Postgres:** `PostgresMovementRepository`, `PostgresProductRepository`, `PostgresCategoryRepository`, `PostgresStockQueryRepository` — todos con `asyncpg` y SQL explícito
- **3 Mappers:** Funciones puras `row_to_product()`, `row_to_category()`, `row_to_movement()` con validación de tipos
- **Vista Materializada:** Migración 008 crea `mv_stock_historical` con índice único en `product_id` para `REFRESH CONCURRENTLY`
- **Refresh Function:** `refresh_stock_view()` con `REFRESH CONCURRENTLY`, manejo de errores y métricas de latencia
- **Unit of Work:** `IUnitOfWork` (Protocol) + `PostgresUnitOfWork` con context manager auto-commit/rollback
- **Módulo de re-exports:** `src/infrastructure/repositories/__init__.py` con imports centralizados

#### Validación
- 98 tests unitarios + 43 tests de integración (100% pass)
- Cobertura de repositorios: 96.30% (target >70%)
- `make lint` y `black --check` sin errores
- Documentación auditada: 10/10 (docstrings con Args/Returns/Raises/Examples)

#### Corregido
- `asyncpg` 0.31.0 con Python 3.14 requiere `json.dumps()` para parámetros JSONB
- Docstring de `refresh_stock_view()` corregido: capturaba `UndefinedTableError` pero decía que lo lanzaba
- Docstrings mejorados en 3 archivos: explicación de estrategia MV+fallback, razón de inmutabilidad de movimientos, comentario sobre JSONB quirk

### [0.1.0] — 2026-05-14 — F0: Preparación (Completado)

#### Agregado
- Estructura Clean Architecture: `src/{domain,application,infrastructure,adapters}` + `tests/{unit,integration,e2e}`
- `pyproject.toml` con configuración de ruff, black, pytest, mypy
- `requirements.txt` con dependencias pinned para F0-F7
- `Makefile` con comandos: `install`, `dev`, `lint`, `format`, `test`, `test-cov`, `build`, `docker-up`, `docker-down`
- `Dockerfile` multi-stage (builder + runtime)
- `docker-compose.yml` con PostgreSQL 16 + app, ambos con healthchecks
- `.env.example` con variables documentadas
- `.pre-commit-config.yaml` con hooks: ruff, black, trailing-whitespace, end-of-file-fixer, check-yaml
- `.github/workflows/ci.yml` con jobs de lint y test
- FastAPI app factory (`src/main.py`) con endpoint `GET /v1/health`
- Configuración pydantic-settings (`src/core/config.py`)
- Pool de conexión asyncpg placeholder (`src/infrastructure/db/connection.py`)
- Test smoke de health endpoint (`tests/unit/test_health.py`)
- Fixture de test con `TestClient` (`tests/conftest.py`)
- Reglas de importación Clean Architecture documentadas en `docs/agents/architecture-design.md`

#### Corregido
- Import `AsyncGenerator` migrado de `typing` a `collections.abc` (Python 3.12+)
- Import `TestClient` movido a bloque `TYPE_CHECKING` para cumplir regla TC002 de ruff
- `pythonpath` agregado a `pyproject.toml` para resolver imports en pytest

---

---

## Información del Proyecto

### Repositorio
- **Nombre**: Esquema stock con historial
- **Descripción**: Esquema relacional normalizado para productos, movimientos y consultas analíticas de stock histórico.
- **Repositorio**: https://github.com/Fisherk2/esquema-stock-historial
- **Licencia**: MIT License

### Stack Tecnológico
...

### Documentación Relacionada
...

### Instrucciones de Actualización

#### Desde Versiones Anteriores
...

#### Para Versiones Futuras
...

### Contribuyendo al CHANGELOG

Al contribuir a este proyecto:

1. **Agrega entradas** a la sección `[Sin Lanzar]`
2. **Sigue versionado semántico** para cambios rupturantes
3. **Usa categorías apropiadas** (Agregado, Cambiado, Deprecado, Removido, Corregido, Seguridad)
4. **Incluye fechas** en formato `YYYY-MM-DD`
5. **Proporciona descripciones claras** explicando el impacto de los cambios
6. **Agrupa por fase** (Definir, Planear, Construir, Verificar, Revisar, Lanzar)
7. **Referencia issues relacionados** o pull requests cuando aplique

### Por Qué Este CHANGELOG Importa

Este CHANGELOG sirve como documentación viva que:

- **Rastrea la evolución** de la plantilla de desarrollo asistido por IA
- **Comunica cambios** a usuarios y contribuyentes
- **Proporciona guía de actualización** para lanzamientos futuros
- **Documenta decisiones arquitectónicas** y su racional
- **Habilita procesos de lanzamiento automatizados** con seguimiento estructurado de cambios