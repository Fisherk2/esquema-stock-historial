# Spec: stock-historial — F0: Preparación

## Objective

Set up the foundational project structure, development environment, and quality tooling for an immutable inventory management system. This phase produces zero business logic — its deliverable is a clean, lintable, testable skeleton that all subsequent phases (F1–F7) build upon.

**Target users:** Warehouse/inventory staff, accounting/finance teams, and API consumers (developers).

**MVP scope (for context; not implemented in F0):**
- Movement recording: IN, OUT, ADJUSTMENT, TRANSFER
- Historical stock queries at any date (<100ms via materialized views)
- Product management: SKU, name, description, unit of measure, categories, min stock threshold
- Low-stock alerts via API query (no push notifications)

**F0 success criteria:**
- `make lint` passes with zero errors
- `make test` runs (even if no tests exist yet — green exit)
- `make dev` starts FastAPI with health endpoint returning `{"status": "ok"}`
- Clean Architecture layer boundaries are enforceable via import conventions
- Docker Compose dev environment starts PostgreSQL 16+ and the app
- Pre-commit hooks run ruff + black on every commit

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Runtime | Python | 3.12+ |
| Framework | FastAPI | 0.115+ |
| Validation | Pydantic | 2.x |
| DB Driver | asyncpg | 0.30+ |
| Scheduler | APScheduler | 3.10+ |
| DB | PostgreSQL | 16+ |
| Linter | Ruff | 0.8+ |
| Formatter | Black | 24.x |
| Testing | pytest + pytest-asyncio | 8.x / 0.24+ |
| Integration | testcontainers | 4.x |
| Settings | pydantic-settings | 2.x |
| Containerization | Docker + Docker Compose | 27+ / 2.x |

## Commands

```
Install:     pip install -r requirements.txt
Dev:         make dev
Lint:        make lint
Format:      make format
Test:        make test
Test (cov):  make test-cov
Build:       make build
Docker up:   make docker-up
Docker down: make docker-down
```

## Project Structure

```
stock-historial/
├── src/
│   ├── domain/                    # Entities, value objects, domain exceptions, business rules
│   │   ├── __init__.py
│   │   ├── entities/              # Product, Movement classes
│   │   ├── value_objects/         # MovementType, SKU, etc.
│   │   ├── exceptions/            # InsufficientStockError, ImmutabilityViolationError
│   │   ├── rules/                 # Stock validation, immutability enforcement
│   │   └── ports/                 # Protocols: IMovementRepository, IStockQueryRepository
│   ├── application/               # Use cases, DTOs, application protocols
│   │   ├── __init__.py
│   │   ├── use_cases/             # RecordMovementUseCase, QueryStockAtDateUseCase
│   │   ├── dtos/                  # Pydantic input/output models
│   │   └── interfaces/            # Application-level protocols
│   ├── infrastructure/            # External concerns: DB, scheduler, logging
│   │   ├── __init__.py
│   │   ├── db/                    # asyncpg connection pool, migrations, UoW
│   │   ├── repositories/          # PostgresRepository implementations
│   │   ├── scheduler/             # APScheduler config, refresh policy
│   │   └── logging/               # Structured logging setup
│   ├── adapters/                  # HTTP layer: FastAPI routers, middleware
│   │   ├── __init__.py
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── routers/           # /v1/movements, /v1/stock, /v1/products
│   │       ├── middleware/         # Error mapping, rate limiting
│   │       └── dependencies.py    # FastAPI Depends() wiring
│   └── main.py                    # DI container, app factory, entrypoint
├── tests/
│   ├── conftest.py                # Shared fixtures (mock repos, async client)
│   ├── unit/                      # Mocked protocols, pure business logic
│   ├── integration/               # Testcontainers PostgreSQL, real SQL
│   └── e2e/                       # Full HTTP flows, latency assertions
├── migrations/                    # SQL migration files (numbered)
├── scripts/                       # Demo, seed, utility scripts
├── docs/                          # Architecture, ADRs, guides
├── specs/                         # Spec files per spec tracking table
├── .env.example                   # Template for environment variables
├── .gitignore
├── .pre-commit-config.yaml        # Pre-commit hooks (ruff, black)
├── docker-compose.yml             # Dev: PostgreSQL + app
├── Dockerfile                     # Multi-stage production build
├── Makefile                       # All developer commands
├── pyproject.toml                 # Ruff, black, pytest, mypy config
├── requirements.txt               # Pinned dependencies
└── README.md                      # Setup instructions, architecture overview
```

## Code Style

```python
# Naming: snake_case for functions/variables, PascalCase for classes
# Type hints: required on all function signatures
# Imports: stdlib → third-party → local (isort order)
# Async: all I/O functions are async; no sync DB calls
# Errors: domain exceptions, never raw ValueError in use cases

from __future__ import annotations

from src.domain.value_objects.movement_type import MovementType
from src.domain.ports.movement_repository import IMovementRepository


async def record_movement(
    movement_type: MovementType,
    product_id: str,
    quantity: int,
    repository: IMovementRepository,
) -> str:
    if quantity <= 0:
        raise ValueError("quantity must be positive")
    movement_id = await repository.create(
        movement_type=movement_type,
        product_id=product_id,
        quantity=quantity,
    )
    return movement_id
```

**Key conventions:**
- Max line length: 88 (black default)
- Cyclomatic complexity per function: <10
- Classes: <300 lines. Functions: single responsibility
- No `print()` — use `logging` or `structlog`
- SQL: parameterized only (`$1`, `$2`), never string concatenation
- Docstrings: Google style on public classes/functions

## Testing Strategy

| Level | Location | Framework | Scope |
|-------|----------|-----------|-------|
| Unit | `tests/unit/` | pytest + pytest-asyncio | Domain rules, use cases (mocked repos) |
| Integration | `tests/integration/` | pytest + testcontainers | SQL queries, materialized views, real DB |
| E2E | `tests/e2e/` | pytest + httpx | Full HTTP flows, latency <100ms |

**Coverage targets:** domain/ >85%, application/ >85%, infrastructure/ >70%

**Patterns:**
- Mock repositories implement domain `Protocol` interfaces
- Each integration test gets an isolated PostgreSQL via testcontainers
- `freezegun` for deterministic time in historical queries
- Scheduler is disabled in `TESTING` mode

## Boundaries

### Always do
- Enforce Clean Architecture layers (domain never imports infrastructure)
- Validate all inputs with Pydantic at the API edge
- Use parameterized SQL only (`$1`, `$2`) — never string concatenation

### Ask first
- DB schema changes (migrations, new tables, alter columns)
- Adding new Python dependencies
- CI/Docker configuration changes
- Domain interface/protocol changes

### Never do
- Commit secrets (`.env`, credentials, API keys)
- Mutate historical data (`UPDATE`/`DELETE` on `movements` table)
- Use ORM for analytical queries (CTEs, window functions)
- Use `print()` in production
- Mix synchronous code in async routes (blocks event loop)

## Success Criteria

- [ ] `make lint` passes with 0 errors
- [ ] `make test` exits green (even with empty test suite)
- [ ] `make dev` starts FastAPI; `GET /health` returns `{"status": "ok"}`
- [ ] `docker compose up` starts PostgreSQL + app with healthchecks
- [ ] Pre-commit hooks run ruff + black on commit
- [ ] `pyproject.toml` configures ruff, black, pytest, mypy
- [ ] Clean Architecture import rules documented and enforceable
- [ ] `.env.example` lists all required environment variables
- [ ] `requirements.txt` has all F0 dependencies pinned

## Open Questions

1. Should `mypy` strict mode be enforced in CI, or start with basic mode and tighten later?
2. Should we use `alembic` for migration management or raw numbered SQL files?
3. Is `structlog` preferred over stdlib `logging` from day one, or add later?
4. Should the health endpoint also check DB connectivity (`SELECT 1`) in F0 or defer to F1?

---

# Spec: stock-historial — F1: Infraestructura DB

## Objective

Establecer la infraestructura completa de base de datos: esquema normalizado (3NF),
migraciones SQL idempotentes, pool de conexiones integrado al lifespan de FastAPI,
endpoint de health con verificación DB, y datos de prueba para desarrollo.

**F1 success criteria:**
- `make migrate` ejecuta todas las migraciones idempotentemente
- `make seed` inserta datos de prueba (~10 productos, ~30 movimientos)
- `GET /v1/health` retorna `{status, db}` con verificación `SELECT 1`
- Trigger de inmutabilidad bloquea `UPDATE`/`DELETE` en `movements`
- Índices compuestos y parciales creados para consultas <100ms
- Tests de integración validan esquema, constraints, trigger e índices

## Schema

```
ENUM: movement_type AS ENUM ('IN','OUT','ADJUSTMENT','TRANSFER')

TABLE categories:
  id          BIGINT GENERATED ALWAYS AS IDENTITY PK
  name        TEXT NOT NULL UNIQUE
  description TEXT
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()

TABLE products:
  id          BIGINT GENERATED ALWAYS AS IDENTITY PK
  sku         TEXT NOT NULL UNIQUE
  name        TEXT NOT NULL
  description TEXT
  unit_of_measure TEXT NOT NULL DEFAULT 'unit'
  category_id BIGINT NOT NULL REFERENCES categories(id) ON DELETE RESTRICT
  min_stock_threshold INTEGER NOT NULL DEFAULT 0 CHECK (>= 0)
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()

TABLE movements:
  id            BIGINT GENERATED ALWAYS AS IDENTITY PK
  product_id    BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT
  movement_type movement_type NOT NULL
  quantity      INTEGER NOT NULL CHECK (quantity > 0)
  metadata      JSONB DEFAULT '{}'
  reference     TEXT
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()

TRIGGER: enforce_movements_immutability (BEFORE UPDATE OR DELETE → RAISE EXCEPTION)

INDEXES:
  ix_movements_product_created  ON movements (product_id, created_at DESC)
  ix_movements_type_in|out|adjustment|transfer  (partial indexes)
  ix_products_category_id       ON products (category_id)
```

## Commands

```
Migrate:     make migrate
Seed:        make seed
Test:        make test
Build:       make build
```

## Files

- `migrations/001_*.sql` — movement_type ENUM
- `migrations/002_*.sql` — categories table
- `migrations/003_*.sql` — products table
- `migrations/004_*.sql` — movements table
- `migrations/005_*.sql` — immutability trigger
- `migrations/006_*.sql` — indexes
- `migrations/007_*.sql` — seed data
- `src/infrastructure/db/migrate.py` — migration runner
- `src/infrastructure/db/seed.py` — seed executor
- `src/infrastructure/db/connection.py` — pool management (lifespan integrated)
- `src/main.py` — lifespan calls init_pool/close_pool
- `src/adapters/api/routers/health.py` — health endpoint with SELECT 1
- `tests/integration/test_db_schema.py` — integration tests (15 cases)

---

# Spec: stock-historial — F2: Núcleo de Dominio

## Objective

Construir el nucleo de dominio puro del sistema: entidades, value objects,
excepciones, reglas de negocio y protocolos (ports). Cero codigo de
infraestructura — logica de dominio framework-agnostic.

**F2 success criteria:**
- `make lint` pasa con 0 errores en `src/domain/`
- `make test` pasa todos los tests unitarios de dominio
- Cobertura de `src/domain/` > 85%
- No hay imports de Pydantic, application o infrastructure en `domain/`
- Todos los Protocolos son `@runtime_checkable` y satisfacen mocks en tests
- Entidades validan sus invariantes en `__post_init__`
- Reglas son funciones puras (sin estado, sin I/O)

## Domain Components

### Entities
- **Movement** — `@dataclass(frozen=True)`, inmutable, metadatos validados por tipo
- **Product** — `@dataclass`, SKU value object, validacion de nombre/umbral/unidad
- **Category** — `@dataclass`, validacion de nombre no vacio

### Value Objects
- **MovementType** — `Enum` con 4 valores: IN, OUT, ADJUSTMENT, TRANSFER
- **Quantity** — `@dataclass(frozen=True)`, valida `value > 0`
- **SKU** — `@dataclass(frozen=True)`, regex `[A-Za-z0-9\-_]{1,50}`

### Exceptions
- **DomainError** — base exception, todas heredan de esta
- **InsufficientStockError** — lleva `product_id`, `requested`, `available`
- **ImmutabilityViolationError** — lleva `entity_type`, `entity_id`
- **InvalidQuantityError** — para cantidades <= 0
- **InvalidSKUError** — para formatos de SKU invalidos

### Rules (pure functions)
- **calculate_stock_delta** — +qty para IN/ADJUSTMENT, -qty para OUT/TRANSFER
- **validate_stock_not_negative** — lanza InsufficientStockError si stock < 0
- **enforce_immutability** — bloquea update/delete en Movement
- **validate_movement_type_consistency** — valida metadata segun tipo

### Ports (typing.Protocol)
- **IMovementRepository** — create, get_by_id, list_by_product (NO update/delete)
- **IStockQueryRepository** — get_current_stock, get_stock_at_date
- **IProductRepository** — create, get_by_id, get_by_sku, list_all, list_below_threshold
- **ICategoryRepository** — create, get_by_id, list_all (sin paginacion)

## Files Created

- `src/domain/entities/movement.py`, `product.py`, `category.py`
- `src/domain/value_objects/movement_type.py`, `quantity.py`, `sku.py`
- `src/domain/exceptions/domain_error.py`, `insufficient_stock.py`,
  `immutability_violation.py`, `invalid_quantity.py`, `invalid_sku.py`
- `src/domain/rules/stock_validation.py`, `immutability.py`,
  `movement_consistency.py`
- `src/domain/ports/movement_repository.py`, `stock_query_repository.py`,
  `product_repository.py`, `category_repository.py`
- `src/domain/__init__.py` — re-export de toda la API publica
- `tests/unit/domain/` — 80+ tests unitarios

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| `@dataclass` natives (no Pydantic) | Dominio framework-agnostic; Pydantic solo para DTOs |
| `Movement` frozen | Inmutabilidad a nivel de lenguaje |
| `typing.Protocol` + `@runtime_checkable` | DIP sin acoplamiento por herencia |
| MovementType como `Enum` | Set cerrado de 4 valores, mapeo 1:1 a PostgreSQL ENUM |
| FK como `int` (no navegacion) | Entidades serializables, sin lazy-loading |
| TRANSFER como un solo Movement | Registro atomico con origin/destination en metadata |
| Reglas como funciones puras | Sin estado, sin I/O, testables facilmente |

---

# Spec: stock-historial — F3: Adaptadores de Datos

## Objective

Implementar los adaptadores de datos que conectan el dominio puro (F2) con PostgreSQL (F1). Esta fase materializa los 4 ports del dominio como repositorios concretos con `asyncpg` y SQL explícito, añade la vista materializada para consultas de stock <100ms, y establece el patrón Unit of Work para transacciones multi-repositorio.

**Usuarios objetivo:** Los casos de uso de F4 (Application layer) consumirán estos repositorios. Son el puente entre dominio e infraestructura.

**Detalles completos:** Ver los specs individuales para diseño completo con código:
- [SPEC-30](specs/SPEC-30.md) — Repositorios + Mappers
- [SPEC-31](specs/SPEC-31.md) — Vistas Materializadas
- [SPEC-32](specs/SPEC-32.md) — Unit of Work & Transacciones

## Tech Stack

| Componente | Tecnología | Notas |
|-----------|-----------|-------|
| DB Driver | asyncpg | Ya en F0 |
| DB | PostgreSQL 16+ | Ya en F1 |
| Testing | pytest + testcontainers.postgres | Ya en F0 |
| **Nuevas dependencias** | Ninguna | F3 no añade dependencias externas |

## Commands

```
Test:        make test          # Unit + integration tests
Test (cov):  make test-cov      # Con reporte de cobertura
Lint:        make lint          # ruff + black --check
Migrate:     make migrate       # Ejecuta migraciones 001-008
Build:       make build         # lint + format + test
```

## Project Structure

**Archivos nuevos que F3 crea:**

```
src/infrastructure/repositories/
├── __init__.py              # Re-exports de todos los repositorios
├── mappers.py               # Funciones puras: Row → Entity
├── movement_repository.py   # PostgresMovementRepository
├── product_repository.py    # PostgresProductRepository
├── category_repository.py   # PostgresCategoryRepository
└── stock_query_repository.py # PostgresStockQueryRepository

src/infrastructure/db/
├── refresh.py               # refresh_stock_view() — refresh manual
└── uow.py                   # PostgresUnitOfWork — context manager

src/domain/ports/
└── unit_of_work.py          # IUnitOfWork Protocol (nuevo)

migrations/
└── 008_create_mv_stock_historical.sql  # Vista materializada + índices
```

## Code Style

Las convenciones de F0 se aplican. F3 añade patrones específicos de repositorios:

```python
# Patrón de repositorio F3:
# 1. SQL explícito como constantes de clase (legible, EXPLAIN-friendly)
# 2. Parámetros posicionales ($1, $2) — NUNCA concatenación
# 3. Mappers como funciones puras separadas del repositorio
# 4. Constructor con pool + connection opcional (soporte UoW)
# 5. Método _get_conn() abstracto: pool o conexión de transacción

from __future__ import annotations
from typing import TYPE_CHECKING
import asyncpg
from src.domain.ports.movement_repository import IMovementRepository
from src.domain.entities.movement import Movement
from src.infrastructure.repositories.mappers import map_movement_row

if TYPE_CHECKING:
    pass


class PostgresMovementRepository(IMovementRepository):
    """Repositorio de movimientos con asyncpg y SQL explícito."""

    _CREATE_SQL = """
        INSERT INTO movements (product_id, movement_type, quantity, metadata, reference, created_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, product_id, movement_type, quantity, metadata, reference, created_at
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        connection: asyncpg.Connection | None = None,
    ) -> None:
        self._pool = pool
        self._connection = connection

    def _get_conn(self) -> asyncpg.Pool | asyncpg.Connection:
        return self._connection if self._connection else self._pool

    async def create(self, movement: Movement) -> Movement:
        row = await self._get_conn().fetchrow(
            self._CREATE_SQL,
            movement.product_id,
            movement.movement_type.value,
            movement.quantity.value,
            movement.metadata,
            movement.reference,
            movement.created_at,
        )
        return map_movement_row(row)
```

**Convenciones específicas de F3:**
- SQL: todas las queries como constantes de clase (uppercase, Snake SQL)
- Mappers: funciones puras en `mappers.py`, sin estado, sin I/O
- Mappers asumen DB válida (CHECK constraints protegen la integridad) pero lanzan excepciones de dominio si los tipos no coinciden
- No ORM, no query builders — SQL explícito siempre
- Cada método de repositorio es un único `fetchrow` o `fetch`

## Testing Strategy

| Level | Location | Framework | Scope |
|-------|----------|-----------|-------|
| Unit | `tests/unit/infrastructure/` | pytest | Mappers aislados (mock Records) |
| Integration | `tests/integration/` | pytest + testcontainers.postgres | SQL real, repositorios, vista materializada, UoW |

**Coverage targets:** infrastructure/repositories/ >70%

**Patrones de test F3:**
- Fixture `db_pool` existente se reutiliza para todos los tests de integración
- Cada test de repositorio: `create()` → `get_by_id()` → verificar entidad retornada
- Mappers: mock `asyncpg.Record` con dict, validar transformación tipos
- Vista materializada: insertar movimientos → refresh → comparar con cálculo directo
- UoW: commit (persistir datos), rollback (excepción no persiste), conexión compartida
- Fallback: si vista no existe, `get_current_stock()` usa cálculo directo

## Boundaries

### Always do
- SQL explícito con parámetros posicionales (`$1`, `$2`) — cero string concatenation
- Mappers como funciones puras (sin estado, sin I/O)
- Los repositorios NO implementan `update()` ni `delete()` para entidades inmutables
- Connection opcional en constructor para soporte de Unit of Work

### Ask first
- Cambiar la firma de los ports del dominio (Protocolos en `domain/ports/`)
- Añadir nuevos métodos a `IUnitOfWork` más allá de `connection`
- Cambiar el tipo de retorno de `get_current_stock()` (actualmente `float`)
- Modificar la estructura de la vista materializada `mv_stock_historical`
- Añadir nuevas dependencias para F3

### Never do
- Usar ORM o query builders — SQL explícito siempre
- Concatenar strings en queries (SQL injection risk)
- Mutar entidades de dominio dentro de los mappers (las entidades son inmutables)
- Commit manual en UoW — solo commit/rollback automático vía context manager
- Añadir lógica de negocio en los repositorios — eso es responsabilidad de los use cases

## Implementation Order

```
Spec-30 (Repositorios + Mappers)
    ↓
Spec-31 (Vistas Materializadas)
    ↓
Spec-32 (Unit of Work + IUnitOfWork Protocol)
```

- **Spec-30 primero:** Define los 4 repositorios y sus mappers. Es la base que dependen Spec-31 y Spec-32.
- **Spec-31 segundo:** Actualiza `PostgresStockQueryRepository` para usar la vista materializada. Requiere los repos de Spec-30.
- **Spec-32 tercero:** Añade `IUnitOfWork` y `PostgresUnitOfWork`. Requiere que los repos tengan `connection` opcional (ya implementado en Spec-30).

## Success Criteria

### Spec-30: Repositorios + Mappers
- [ ] Los 4 repositorios implementan sus protocols respectivos
- [ ] Todo SQL usa parámetros posicionales (`$1`, `$2`) — cero concatenación
- [ ] Mappers son funciones puras testeables aisladamente
- [ ] Constructor acepta `connection` opcional para UoW
- [ ] `PostgresMovementRepository` NO tiene `update()` ni `delete()`
- [ ] Tests de integración validan CRUD, paginación, cálculo de stock, mapeo de tipos

### Spec-31: Vistas Materializadas
- [ ] Vista `mv_stock_historical` existe tras migración 008
- [ ] Índice único `ix_mv_stock_historical_product` existe (REFRESH CONCURRENTLY)
- [ ] `refresh_stock_view()` ejecuta sin error
- [ ] `get_current_stock()` usa vista, retorna mismo valor que cálculo directo
- [ ] `get_stock_at_date()` sigue usando cálculo directo (no usa vista)
- [ ] Tests validan: creación vista, refresh, consistencia, fallback

### Spec-32: Unit of Work
- [ ] `PostgresUnitOfWork` funciona como context manager asíncrono
- [ ] Rollback automático en excepción
- [ ] Commit automático al salir sin excepción
- [ ] Conexión compartida entre múltiples repositorios
- [ ] Conexión siempre liberada al pool
- [ ] `IUnitOfWork` verificable como Protocol
- [ ] Tests validan: commit, rollback, conexión compartida, aislamiento

**Aggregate criteria:** `make lint` sin errores en todos los archivos nuevos | Coverage infrastructure/ >70% | `make test` pasa todos los tests

## Resolved Questions

### Específicas de F3

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| F3-Q1 | `get_current_stock()` retorna `int` o `float`? | **`float`** | El port ya está definido como `float` en F2. Mantener compatibilidad. La implementación convierte explícitamente. |
| F3-Q2 | Añadir método batch `get_stock_for_multiple_products()`? | **No en F3** | YAGNI. Se puede añadir en F5/F6 si los use cases lo necesitan. |
| F3-Q3 | Los mappers validan entidades o asumen DB válida? | **Asumen DB válida** | DB tiene CHECK constraints, FK, trigger. Los mappers solo transforman tipos. Si un tipo no coincide, lanzan excepción de dominio (`InvalidSKUError`, `ValueError`). No validan invariantes de negocio. |
| F3-Q4 | Incluir `category_id` en vista materializada? | **No** | Mínimo viable. Se puede añadir en migración futura si se necesitan consultas por categoría. |
| F3-Q5 | Añadir `timeout` en `refresh_stock_view()`? | **No** | Se maneja con `statement_timeout` global de PostgreSQL si se necesita. |
| F3-Q6 | Añadir endpoint admin `POST /v1/admin/refresh-stock-view`? | **No en F3** | Refresh manual se hace vía función Python o APScheduler en F5. |
| F3-Q7 | UoW expone `commit()`/`rollback()` explícitos? | **Solo automático** | Commit/rollback solo vía context manager. Simple y explícito. |
| F3-Q8 | Protocol `IUnitOfWork` incluye `commit()`/`rollback()`? | **Solo `connection`** | El Protocol solo define la propiedad `connection`. |
| F3-Q9 | Crear `UnitOfWorkFactory`? | **No** | El caller instancia repos manualmente con `uow.connection`. Simple y explícito. |

### Preguntas de F3 (resueltas — ver tabla arriba)
1. ~~¿`get_current_stock()` retorna `int` o `float`?~~ → Resuelto: `float` (compatibilidad con port F2).
2. ~~¿Añadir método batch `get_stock_for_multiple_products()`?~~ → Resuelto: No en F3 (YAGNI).
3. ~~¿Mappers validan entidades o asumen DB válida?~~ → Resuelto: Asumen DB válida con validación de tipos.
4. ~~¿Incluir `category_id` en vista materializada?~~ → Resuelto: No (mínimo viable).
5. ~~¿Añadir `timeout` en `refresh_stock_view()`?~~ → Resuelto: No (usa `statement_timeout` global).
6. ~~¿Añadir endpoint admin de refresh?~~ → Resuelto: No en F3 (F5 con APScheduler).
7. ~~¿UoW expone `commit()`/`rollback()` explícitos?~~ → Resuelto: Solo automático.
8. ~~¿Protocol `IUnitOfWork` incluye `commit()`/`rollback()`?~~ → Resuelto: Solo `connection`.
9. ~~¿Crear `UnitOfWorkFactory`?~~ → Resuelto: No (caller instancia manualmente).

---

# Spec: stock-historial — F4: Capa API (Casos de Uso + Endpoints)

## Objective

Implementar la capa de aplicación (6 use cases + DTOs Pydantic) y la capa de adaptadores HTTP (4 routers FastAPI `/v1/`, DI factories, error mapping middleware) que exponen las operaciones del dominio como API REST.

**Usuarios objetivo:** Desarrolladores que consumen la API REST y operadores de inventario.

**F4 success criteria:**
- `make lint` pasa con 0 errores
- 6 use cases con `async execute()` implementados
- 4 routers FastAPI registrados en `/v1/` con 10 endpoints operativos
- Errores de dominio mapeados a `ErrorResponse` con status codes semánticos
- OpenAPI (`/docs`) muestra los 10 endpoints con ejemplos
- Tests unitarios pasan (>85% cobertura en `application/`)
- Version 0.4.0 en `main.py`

## Tech Stack

| Componente | Tecnología | Notas |
|-----------|-----------|-------|
| Runtime | Python 3.12+ | Sin cambios |
| Framework | FastAPI 0.136+ | Ya en F0 |
| Validación | Pydantic 2.13+ | DTOs strict mode |
| **Nuevas dependencias** | Ninguna | F4 no añade deps externas |

## Commands

```
Install:    pip install -r requirements.txt
Dev:        make dev
Lint:       make lint
Format:     make format
Test:       make test
Test (cov): make test-cov
Build:      make build
```

## Project Structure

**Archivos creados/modificados en F4:**

```
# Nuevos archivos
src/application/use_cases/
├── record_movement.py          # RecordMovementUseCase
├── query_current_stock.py      # QueryCurrentStockUseCase
├── query_stock_at_date.py      # QueryStockAtDateUseCase
├── create_product.py           # CreateProductUseCase
├── list_products.py            # ListProductsUseCase (retorna tupla items, total)
├── create_category.py          # CreateCategoryUseCase
└── __init__.py

src/application/dtos/
├── movement_dtos.py            # CreateMovementInput, MovementOutput, MovementListOutput
├── stock_dtos.py               # CurrentStockOutput, StockAtDateOutput
├── product_dtos.py             # CreateProductInput, ProductOutput, ProductListOutput
├── category_dtos.py           # CreateCategoryInput, CategoryOutput
├── error_dtos.py               # ErrorResponse, ErrorDetail
└── __init__.py

src/adapters/api/
├── dependencies.py             # Factory functions: pool → repos → use cases
├── middleware/error_handler.py # Exception handlers: DomainError → HTTP
└── routers/
    ├── movements.py            # POST/GET /v1/movements
    ├── stock.py                # GET /v1/stock/{id}/current, /at-date
    ├── products.py             # POST/GET /v1/products
    └── categories.py           # POST/GET /v1/categories

# Modificaciones
src/domain/rules/stock_validation.py  # ADD: product_id param
src/domain/ports/movement_repository.py  # ADD: count_by_product()
src/domain/ports/product_repository.py   # ADD: count_all()
src/infrastructure/repositories/movement_repository.py  # ADD: count_by_product()
src/infrastructure/repositories/product_repository.py   # ADD: count_all()
src/main.py                      # UPDATE: routers + error handlers + version 0.4.0

# Tests nuevos
tests/unit/application/use_cases/   # 6 archivos de tests
tests/unit/application/dtos/        # 5 archivos de tests
tests/integration/api/              # 5 archivos de tests de endpoints
```

## Code Style

```python
# Use Case: clase con DI en __init__, único método async execute()
class RecordMovementUseCase:
    def __init__(self, movement_repo, product_repo, stock_query_repo, uow) -> None:
        self._movement_repo = movement_repo
        ...

    async def execute(self, product_id: int, movement_type: MovementType, ...) -> Movement:
        ...

# Router: Annotated[UseCase, Depends(factory)] — patrón FastAPI moderno
@router.post("", response_model=MovementOutput, status_code=201)
async def create_movement(
    body: CreateMovementInput,
    use_case: Annotated[RecordMovementUseCase, Depends(get_record_movement_use_case)],
) -> MovementOutput:
    movement = await use_case.execute(...)
    return MovementOutput(...)
```

## Testing Strategy

| Level | Location | Framework | Scope |
|-------|----------|-----------|-------|
| Unit | `tests/unit/application/` | pytest + mocks | Use cases y DTOs |
| Integration | `tests/integration/api/` | pytest + testcontainers + httpx | Endpoints reales |

## Boundaries

### Always do
- Use cases inyectan Protocolos en `__init__`, no implementaciones concretas
- Input DTOs usan `ConfigDict(strict=True)`
- Errores de dominio se propagan sin capturar (adapter los mapea)
- `validate_stock_not_negative()` recibe `product_id` como parámetro

### Ask first
- Cambiar firmas de ports del dominio
- Cambiar mapeo excepciones → HTTP status codes
- Añadir nuevas dependencias

### Never do
- Importar de `infrastructure/` en `application/use_cases/`
- Capturar excepciones de dominio en use cases
- Mutar datos históricos

## Endpoint Summary

| Método | Ruta | Status | Response |
|--------|------|--------|----------|
| POST | `/v1/movements` | 201 | `MovementOutput` |
| GET | `/v1/movements/{id}` | 200/404 | `MovementOutput` |
| GET | `/v1/movements?product_id=...` | 200 | `MovementListOutput` |
| GET | `/v1/stock/{id}/current` | 200 | `CurrentStockOutput` |
| GET | `/v1/stock/{id}/at-date?date=...` | 200 | `StockAtDateOutput` |
| POST | `/v1/products` | 201 | `ProductOutput` |
| GET | `/v1/products` | 200 | `ProductListOutput` |
| GET | `/v1/products/{id}` | 200/404 | `ProductOutput` |
| POST | `/v1/categories` | 201 | `CategoryOutput` |
| GET | `/v1/categories` | 200 | `list[CategoryOutput]` |

## Success Criteria

### Spec-40: Casos de Uso
- [x] 6 use cases con `async execute()` implementados
- [x] `RecordMovementUseCase` verifica producto, valida stock, usa UoW
- [x] `ListProductsUseCase` retorna `(items, total)` tupla
- [x] Zero imports de `infrastructure/` en use cases
- [x] Excepciones de dominio propagadas sin capturar

### Spec-41: DTOs
- [x] Input DTOs con `ConfigDict(strict=True)`
- [x] `CreateMovementInput` valida metadata via `@model_validator`
- [x] `CreateProductInput` valida SKU regex
- [x] Output DTOs con `id` y `created_at`
- [x] `ErrorResponse` formato consistente

### Spec-42: Routers + Error Mapping
- [x] 4 routers registrados con prefix `/v1`
- [x] POST retorna 201, GET retorna 200
- [x] `InsufficientStockError` → 409, `InvalidSKUError` → 422, `ValueError` → 400
- [x] OpenAPI `/docs` muestra 10 endpoints
- [x] `main.py` version 0.4.0

### Domain Fixes
- [x] `validate_stock_not_negative()` recibe `product_id`
- [x] `IMovementRepository.count_by_product()` añadido
- [x] `IProductRepository.count_all()` añadido

### Aggregate
- [x] `make lint` sin errores
- [x] 147 unit tests pasan
- [x] Version 0.4.0

## Resolved Questions

| # | Pregunta | Decisión |
|---|----------|----------|
| F4-Q1 | ¿`count_by_product()` ahora o después? | Ahora (paginación exacta) |
| F4-Q2 | ¿Fix `validate_stock_not_negative()` con `product_id`? | Ahora (errores engañosos) |
| F4-Q3 | ¿Dónde guardar spec F4? | Append a SPEC.md |
| F4-Q4 | ¿Testing scope? | Unit + Integration |
| F4-Q5 | ¿`ListProductsUseCase` retorna total? | Sí, via `count_all()` |
| F4-Q6 | ¿GET by ID directo a repo? | Sí (CQRS pattern) |
| F4-Q7 | ¿Use cases como clases o funciones? | Clases (DI, testing) |
| F4-Q8 | ¿UoW para todos los movimientos? | Solo OUT/TRANSFER |
| F4-Q9 | ¿API snake_case o camelCase? | snake_case |
| F4-Q10 | ¿Error mapping middleware o handlers? | Exception handlers |
