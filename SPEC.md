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

---

# Spec: stock-historial — F5: Scheduler & Concurrencia

## Objective

Integrar tres componentes de infraestructura que dotan al sistema de resiliencia y observabilidad: (1) APScheduler como motor de tareas en background para el refresh periódico de la vista materializada `mv_stock_historical`, (2) decorador de reintentos con backoff exponencial para manejar conflictos transaccionales, y (3) logging estructurado con request correlation y timeouts de DB configurables.

**Usuarios objetivo:** Operadores de inventario que necesitan datos frescos, y equipos de ops que necesitan visibilidad del comportamiento de la aplicación.

**F5 success criteria:**
- `AsyncIOScheduler` se inicia en el lifespan de FastAPI con refresh configurable
- `SCHEDULER_ENABLED=false` deshabilita el scheduler sin error
- `_refresh_job` usa retry con 3 reintentos + backoff exponencial + jitter
- `RequestLoggingMiddleware` genera `request_id` único por request y lo propaga via `contextvars`
- `/v1/health` se excluye del request logging
- JSON format en producción, formato legible en desarrollo
- `statement_timeout` configurable: 5s para API, 30s para refresh
- `make lint` pasa con 0 errores
- Tests unitarios y de integración validan scheduler, retry, y logging
- Version 0.5.0 en `main.py`

## Tech Stack

| Componente | Tecnología | Notas |
|-----------|-----------|-------|
| Scheduler | APScheduler 3.11.2 | Ya en requirements.txt (F0). Se usa `AsyncIOScheduler` |
| Retry | Decorador custom | Sin dependencia nueva — backoff exponencial + jitter |
| Logging | Python `logging` estándar | Sin `structlog` en F5. JSON formatter custom |
| **Nuevas dependencias** | Ninguna | F5 no añade deps externas |

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

**Archivos nuevos que F5 crea:**

```
src/core/
├── retry.py                      # Decorador @retry_with_backoff
└── config.py                     # UPDATE: campos scheduler, logging, timeouts

src/infrastructure/scheduler/
├── __init__.py                   # UPDATE: re-exports públicos
└── scheduler.py                  # AsyncIOScheduler integration

src/infrastructure/logging/
├── __init__.py                   # UPDATE: re-exports
└── config.py                     # Logging setup + JSON formatter

src/adapters/api/middleware/
├── request_logging.py            # RequestLoggingMiddleware (excluye /v1/health)
└── error_handler.py              # UPDATE: handler ConcurrencyConflictError

src/domain/exceptions/
├── concurrency_conflict.py       # Nueva excepción de dominio
└── __init__.py                   # UPDATE: re-export

src/infrastructure/db/
└── connection.py                 # UPDATE: statement_timeout configurado via Settings

src/main.py                       # UPDATE: lifespan incluye scheduler + logging setup
```

**Archivos de spec detallados:**

- [SPEC-50](specs/SPEC-50.md) — Integración APScheduler
- [SPEC-51](specs/SPEC-51.md) — Optimistic Concurrency & Retry
- [SPEC-52](specs/SPEC-52.md) — Logging Estructurado & Errors

## Code Style

```python
# Decorador async retryable — backoff exponencial + jitter
@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    max_delay=10.0,
    jitter=0.5,
    exceptions=_RETRYABLE_EXCEPTIONS,
)
async def _refresh_job(pool: Pool, statement_timeout: int = 30) -> None:
    start = time.monotonic()
    _logger.info("Starting mv_stock_historical refresh")
    await pool.execute(f"SET LOCAL statement_timeout = '{statement_timeout * 1000}'")
    await refresh_stock_view(pool)
    elapsed = time.monotonic() - start
    _logger.info("mv_stock_historical refreshed in %.2fs", elapsed)

# Middleware de request logging — contextvar propagation
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    EXCLUDED_PATHS: set[str] = {"/v1/health", "/health"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)
        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)
        # ... log + timing + response headers ...
```

**Convenciones específicas de F5:**
- Scheduler: `AsyncIOScheduler` (no `BackgroundScheduler`) — usa event loop existente
- Retry: decorador genérico, no específico de DB. Captura solo excepciones explícitas
- Logging: `contextvars` para `request_id` — thread-safe y async-safe
- Timeouts: `SET LOCAL` para refresh (no afecta otras conexiones del pool)
- Health checks excluidos del logging — reducen ruido en producción

## Testing Strategy

| Level | Location | Framework | Scope |
|-------|----------|-----------|-------|
| Unit | `tests/unit/infrastructure/scheduler/` | pytest + mocks | Scheduler creation, job registration |
| Unit | `tests/unit/core/` | pytest | Retry decorator behavior, JSON formatter |
| Unit | `tests/unit/domain/exceptions/` | pytest | ConcurrencyConflictError |
| Integration | `tests/integration/` | pytest + testcontainers | Request middleware, X-Request-ID header |

**Coverage targets:** infrastructure/scheduler/ >70%, core/retry.py >80%, infrastructure/logging/ >70%

**Patrones de test F5:**
- Scheduler: mock de `AsyncIOScheduler`, verificar `add_job` con parámetros correctos
- Retry: mock `asyncio.sleep`, verificar backoff exponencial, excepciones no-retryables propagan inmediatamente
- Logging: verificar JSON válido, campos esperados, `request_id` en extras
- Middleware: verificar `X-Request-ID` en headers, `/v1/health` no loggea

## Boundaries

### Always do
- `AsyncIOScheduler` integrado en el lifespan — start en startup, shutdown en cleanup
- Retry solo captura excepciones explícitas (no `Exception` genérica)
- `/v1/health` excluido del request logging
- `statement_timeout` se configura via Settings, no hardcodeado
- `request_id` se propaga via `contextvars` y se incluye en headers de respuesta

### Ask first
- Añadir nuevos jobs al scheduler (más allá de refresh)
- Cambiar el decorador retry para aplicarlo a use cases (modificaría Spec-40)
- Migrar de `logging` estándar a `structlog`
- Cambiar el mapeo `ConcurrencyConflictError` → HTTP status code
- Añadir nuevas dependencias para F5

### Never do
- Usar `BackgroundScheduler` (crea thread pool separado — incompatible con asyncio)
- Capturar `Exception` genérica en el retry decorador
- Loggear body de requests (riesgo de datos sensibles)
- Modificar use cases de F4 para añadir retry (Spec-40 completado)
- Commit secrets en `.env`

## Implementation Order

```
Spec-52 (Logging + Settings + request_id)
    ↓ (dependencia: Config, error_handler)
Spec-51 (Retry + ConcurrencyConflictError)
    ↓ (dependencia: retry decorator)
Spec-50 (Scheduler con retry aplicado)
```

- **Spec-52 primero:** Configura logging, Settings, middleware de request. Es la base que usan todos los demás componentes de F5. Añade campos de configuración en `config.py` que necesitan Spec-50 y Spec-51.
- **Spec-51 segundo:** Añade `ConcurrencyConflictError` y el decorador `@retry_with_backoff`. No requiere que el scheduler exista, pero prepara la infraestructura de reintentos.
- **Spec-50 tercero:** Integra APScheduler aplicando el retry del Spec-51 al refresh job. Actualiza el lifespan de FastAPI.

> **Nota:** Aunque Spec-50 aparece como el primero en el número, la implementación debe empezar con Spec-52 (config/logging), luego Spec-51 (retry), y finalmente Spec-50 (scheduler). El DAG de dependencias en docs/workflow/dependency-graphs.md refleja esto: S52 → S51 → S50.

## Success Criteria

### Spec-50: Integración APScheduler
- [ ] `AsyncIOScheduler` se inicia en el `lifespan` de FastAPI
- [ ] Job `refresh_stock_view` se registra con intervalo configurable
- [ ] `SCHEDULER_ENABLED=false` deshabilita el scheduler sin error
- [ ] `shutdown_scheduler()` detiene el scheduler gracefulmente antes de cerrar el pool
- [ ] El refresh usa `statement_timeout` configurable (default 30s)
- [ ] Solo una instancia del job puede ejecutarse a la vez (`max_instances=1`)
- [ ] Tests unitarios validan la creación del scheduler con mocks

### Spec-51: Optimistic Concurrency & Retry
- [ ] `ConcurrencyConflictError` hereda de `DomainError`
- [ ] `@retry_with_backoff` reintenta con backoff exponencial + jitter
- [ ] El decorador solo captura excepciones especificadas
- [ ] Cada reintento se loggea con WARNING; fallo final con ERROR
- [ ] `_refresh_job` usa retry con 3 reintentos
- [ ] `ConcurrencyConflictError` se mapea a HTTP 409 `CONCURRENCY_CONFLICT`
- [ ] Tests validan: éxito al reintento, fallo final, excepción no-retryable

### Spec-52: Logging Estructurado & Errors
- [ ] `setup_logging()` configura formato text o JSON según `LOG_FORMAT`
- [ ] `RequestLoggingMiddleware` genera `request_id` único por request
- [ ] `X-Request-ID` se incluye en headers de respuesta
- [ ] `/v1/health` se excluye del request logging
- [ ] `request_id` se propaga via `contextvars` a todos los logs
- [ ] `statement_timeout` se configura en el pool via `API_STATEMENT_TIMEOUT_SECONDS`
- [ ] Loggers de terceros silencian a WARNING
- [ ] Tests validan JSON formatter output y middleware headers

### Aggregate
- [ ] `make lint` sin errores en todos los archivos nuevos
- [ ] `make test` pasa todos los tests (no rompe tests existentes de F0-F4)
- [ ] Version 0.5.0 en `main.py`
- [ ] `AGENTS.md` actualizado a "F5: En Progreso"

## Resolved Questions

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| F5-Q1 | ¿`AsyncIOScheduler` o `BackgroundScheduler`? | `AsyncIOScheduler` | Usa event loop existente de FastAPI. `BackgroundScheduler` crea thread pool separado |
| F5-Q2 | ¿El retry debe aplicarse a use cases de movimiento? | **Solo refresh job** | Los use cases de Spec-40 están completados. Aplicar retry rompería tests existentes |
| F5-Q3 | ¿El request logging debe excluir `/v1/health`? | **Sí** | Health checks frecuentes (K8s/Docker) generan ruido sin valor diagnóstico |
| F5-Q4 | ¿`statement_timeout` global o configurable? | **Configurable via Settings** | API necesita 5s, refresh necesita 30s. Hardcodear sería inflexible |
| F5-Q5 | ¿`structlog` o `logging` estándar? | `logging` estándar | Suficiente para F5. Se puede migrar en F6+ si se necesita más potencia |
| F5-Q6 | ¿El scheduler debe tener su propio pool de conexiones? | **No** | Usa pool compartido. `REFRESH CONCURRENTLY` no bloquea lecturas |
| F5-Q7 | ¿Debe existir endpoint admin para refresh manual? | **No en F5** | Añadiría complejidad (auth, access control). Usar función directa o scheduler |
| F5-Q8 | ¿`CronTrigger` o `IntervalTrigger`? | `IntervalTrigger` | Más simple y suficiente para refresh periódico. Se puede cambiar a cron después |
| F5-Q9 | ¿El decorador retry debe ser sync o async? | **Async** | Todas las operaciones que necesitan retry son async en este proyecto |
| F5-Q10 | ¿Los logs deben ir a archivo además de stdout? | **Solo stdout** | En contenedores Docker, stdout es capturado por el runtime |

---

# Spec: stock-historial — F6: Testing Integral

## Objective

Consolidar y expandir la suite de tests del sistema con cuatro objetivos complementarios: (1) **property-based testing** con Hypothesis y **mypy strict** como quality gate de tipos (Spec-60); (2) **edge cases de integración** contra PostgreSQL real con testcontainers (Spec-61); (3) **tests E2E de latencia** que validan el SLA core de `<100ms` con pytest-benchmark (Spec-62); (4) **pruebas de seguridad** que validan inmunidad a SQL injection y solidez de input validation (Spec-63).

**F6 success criteria:**
- Hypothesis con `max_examples=100` y `--hypothesis-seed=0` para reproducibilidad
- `mypy src/ --strict` pasa sin errores; tests quedan con `strict=false`
- Edge cases de integración en archivos separados (`*_edge.py`), 0 regresiones en 97 tests existentes
- Latencia de stock queries en p95 < 100ms (SLA gate con pytest-benchmark)
- SQL injection payloads (OWASP) rechazados en todas las capas de entrada
- Input validation boundary tests: tipos incorrectos, rangos, campos extra, payloads malformados
- Error responses no exponen stack traces ni SQL internals
- Movimientos son inmutables: PUT/PATCH/DELETE → 405
- Coverage: domain/ ≥90%, application/ ≥85%, infrastructure/ ≥70%, global ≥80%
- `make lint` pasa con 0 errores
- 0 regresiones en 291 tests existentes

## Tech Stack

| Componente | Tecnología | Notas |
|-----------|-----------|-------|
| Property-Based Testing | Hypothesis 6.x+ | Dev dependency. Strategies composables, `max_examples=100` CI / 1000 dev |
| Type Checking | mypy `--strict` | Solo en `src/`. Tests con `strict=false` |
| Latency Benchmark | pytest-benchmark | In-process, sin servidor externo. SLA gate p95 < 100ms |
| Security Testing | httpx + pytest | Payloads OWASP Testing Guide v4. Sin herramientas externas |
| **Nuevas dependencias (dev)** | hypothesis, pytest-benchmark | Solo dev dependencies. Cero nuevas deps de producción |

## Commands

```
Install: pip install -r requirements.txt
Dev: make dev
Lint: make lint
Typecheck: make typecheck
Format: make format
Test: make test
Test (cov): make test-cov
Test (E2E): pytest tests/e2e/ -v
Test (Security): pytest tests/security/ -v
Test (Benchmark only): pytest tests/e2e/ --benchmark-only
Build: make build
```

## Project Structure

**Archivos nuevos que F6 crea:**

```
tests/unit/
├── strategies.py                          # Hypothesis strategies centralizadas
├── domain/
│   ├── test_quantity.py                   # UPDATE: + property-based tests
│   ├── test_sku.py                        # UPDATE: + property-based tests
│   └── test_rules.py                      # UPDATE: + property-based tests
└── application/use_cases/
    ├── test_record_movement.py            # UPDATE: + edge cases
    ├── test_create_product.py             # UPDATE: + edge cases
    ├── test_list_products.py              # UPDATE: + edge cases
    ├── test_query_current_stock.py        # UPDATE: + edge cases
    ├── test_query_stock_at_date.py        # UPDATE: + edge cases
    └── test_create_category.py            # UPDATE: + edge cases

tests/integration/
├── helpers.py                             # Batch insert helper
├── repositories/
│   ├── test_movement_repository_edge.py   # NEW: edge cases
│   ├── test_product_repository_edge.py    # NEW: edge cases
│   ├── test_category_repository_edge.py   # NEW: edge cases
│   └── test_stock_query_repository_edge.py # NEW: edge cases
├── test_mv_stock_edge.py                  # NEW: MV con datos masivos
├── test_uow_edge.py                       # NEW: UoW edge cases
└── api/
    ├── test_movements_api_edge.py         # NEW: API edge cases
    ├── test_stock_api_edge.py             # NEW: API edge cases
    ├── test_products_api_edge.py          # NEW: API edge cases
    └── test_categories_api_edge.py        # NEW: API edge cases

tests/e2e/
├── conftest.py                            # NEW: fixtures + benchmark config + SLA gate
├── test_stock_latency.py                  # NEW: SLA <100ms benchmarks
├── test_full_flows.py                     # NEW: flujos HTTP end-to-end
└── test_openapi_contracts.py              # NEW: validación contra Pydantic DTOs

tests/security/
├── __init__.py                            # NEW: package marker
├── conftest.py                            # NEW: fixtures compartidos
├── test_sql_injection.py                  # NEW: OWASP SQL injection payloads
├── test_input_validation.py               # NEW: boundary & malformed payload tests
└── test_error_leakage.py                  # NEW: error leakage + immutability tests
```

**Archivos de spec detallados:**

- [SPEC-60](specs/SPEC-60.md) — Tests Unitarios: Hypothesis + mypy strict
- [SPEC-61](specs/SPEC-61.md) — Tests de Integración: Edge Cases & Escenarios Extendidos
- [SPEC-62](specs/SPEC-62.md) — Tests E2E & Latencia <100ms
- [SPEC-63](specs/SPEC-63.md) — Pruebas de Seguridad: SQL Injection + Input Validation

**Archivos existentes que F6 modifica:**

```
pyproject.toml     # mypy strict=true, Hypothesis config, addopts seed, markers
requirements.txt   # +hypothesis, +pytest-benchmark
Makefile           # +typecheck command
src/**/*.py        # Type hints para mypy strict (annotations only)
```

## Code Style

- **Hypothesis strategies:** módulo centralizado `tests/unit/strategies.py`. Strategies nombradas con `_strategy` suffix
- **Edge case tests:** archivos separados `*_edge.py`, no modificar tests existentes
- **Security tests:** directorio separado `tests/security/`. Payloads parametrizados con `@pytest.mark.parametrize`
- **Benchmark tests:** marcados con `@pytest.mark.benchmark(group="...")`. SLA gate implementado como pytest hook
- **Type annotations:** `# type: ignore[xxx]` solo con comentario explicativo. mypy strict en `src/` únicamente

## Testing Strategy

| Level | Location | Framework | Scope |
|-------|----------|-----------|-------|
| Unit (PBT) | `tests/unit/` | pytest + Hypothesis | Domain value objects, rules, use case edge cases |
| Unit (Types) | `src/` | mypy --strict | Type safety gate en CI |
| Integration (Edge) | `tests/integration/*_edge.py` | pytest + testcontainers | Repository edge cases, MV masivos, UoW, API boundary |
| E2E (Latency) | `tests/e2e/test_stock_latency.py` | pytest-benchmark | SLA p95 < 100ms para stock queries |
| E2E (Flows) | `tests/e2e/test_full_flows.py` | pytest + httpx | Flujos HTTP completos end-to-end |
| E2E (Contracts) | `tests/e2e/test_openapi_contracts.py` | pytest + Pydantic | Respuestas validan contra DTOs |
| Security (SQLi) | `tests/security/test_sql_injection.py` | pytest + httpx + asyncpg | OWASP SQL injection payloads |
| Security (Input) | `tests/security/test_input_validation.py` | pytest + httpx | Boundary, malformed, Unicode |
| Security (Leakage) | `tests/security/test_error_leakage.py` | pytest + httpx | No stack traces, no SQL, immutability |

**Coverage targets:** domain/ ≥90%, application/ ≥85%, infrastructure/ ≥70%, global ≥80%

**Patrones de test F6:**
- Hypothesis: `@given(qty=valid_quantity_strategy)` para property-based tests. Seed fijo en CI
- Edge cases: tablas de test con descripción, expected behavior, y resultado
- Benchmark: `benchmark(lambda: asyncio.run(api_client.get(...)))` con SLA gate hook
- Security: `@pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)` para cobertura sistemática
- Contratos: `MovementOutput.model_validate(resp.json())` para validar contra Pydantic

## Boundaries

### Always do
- Hypothesis strategies en módulo centralizado (`tests/unit/strategies.py`)
- Edge case tests en archivos separados (`*_edge.py`), nunca modificar tests existentes
- `--hypothesis-seed=0` en CI para reproducibilidad
- mypy `strict=true` solo en `src/`; tests con `strict=false`
- SLA gate: p95 < 100ms (no max, no p99)
- Security tests usan OWASP payloads estándar
- `# type: ignore[xxx]` con comentario explicativo obligatorio
- Coverage por paquete: domain ≥90%, application ≥85%, infrastructure ≥70%

### Ask first
- Cambiar `max_examples` de Hypothesis (default 100 CI / 1000 dev)
- Añadir nuevos tipos de security tests (más allá de SQLi + input validation)
- Cambiar el percentil SLA (p95 → p99)
- Añadir timing attack tests
- Modificar fixtures de integración existentes (`db_pool`, `db_clean`, `api_client`)
- Añadir dependencias de producción nuevas

### Never do
- Modificar tests existentes (291 unit + integration) — crear archivos nuevos
- Usar Locust/k6 para benchmarks (son load testing, no in-process)
- Usar `sqlmap` u herramientas externas no-deterministas
- Activar mypy strict en `tests/` (mocks y fixtures no se benefician)
- Añadir dependencias de producción en F6 (solo dev deps)
- Commit secrets o datos sensibles en payloads de test
- Añadir auth/authorization/rate-limiting tests (fuera de scope F6)

## Implementation Order

```
Spec-60 (Unit: Hypothesis + mypy strict + edge cases)
↓ (dependencia: type hints, strategies)
Spec-61 (Integration: edge cases contra DB real)
↓ (dependencia: fixtures, helpers, DB real)
Spec-62 (E2E: latencia + flujos + contratos)
↓ (dependencia: API completa funcionando)
Spec-63 (Security: SQLi + input validation)
```

- **Spec-60 primero:** Establece la base de type safety (mypy strict) y property-based testing (Hypothesis). Los type hints añadidos benefician a todos los specs siguientes.
- **Spec-61 segundo:** Extiende integración con edge cases. Requiere que los type hints y strategies de Spec-60 estén listos para que los edge case tests sean type-safe.
- **Spec-62 tercero:** Mide latencia y valida flujos E2E. Depende de que la integración completa funcione (validado por Spec-61).
- **Spec-63 último:** Valida seguridad. Requiere que todos los endpoints y validaciones estén completos (validado por Spec-60/61/62).

> **Nota:** Los specs se implementan secuencialmente porque cada uno construye sobre la confianza del anterior. Spec-60 añade type safety → Spec-61 valida contra DB real → Spec-62 mide rendimiento → Spec-63 valida seguridad.

## Success Criteria

### Spec-60: Tests Unitarios — Hypothesis + mypy strict
- [ ] Hypothesis añadido a `requirements.txt` y `pyproject.toml`
- [ ] `tests/unit/strategies.py` con strategies reutilizables para Quantity, SKU, MovementType
- [ ] Property-based tests para: `Quantity` (boundary), `SKU` (regex), `calculate_stock_delta` (signo), `validate_stock_not_negative` (dominio)
- [ ] Edge cases añadidos en use cases: producto inexistente, categoría duplicada, movimiento con metadata inválida, stock=0, fecha futura, offset>total
- [ ] `mypy src/ --strict` pasa sin errores
- [ ] `pyproject.toml` actualizado: `strict = true`, overrides para `tests.*`
- [ ] Coverage `domain/` ≥90%, `application/` ≥85%
- [ ] 0 regresiones en tests existentes (291 → 291+)
- [ ] `make lint` pasa sin errores
- [ ] `--hypothesis-seed=0` configurado en `addopts` para reproducibilidad

### Spec-61: Tests de Integración — Edge Cases
- [ ] Edge cases en repositorios: producto sin movimientos, stock_at_date con fecha futura, paginación con offset > total, get_by_id not found, count=0
- [ ] Edge cases en API: content-type inválido, body vacío, campos extra, query params inválidos, IDs inexistentes, fechas inválidas, duplicados
- [ ] Tests de MV: refresh con datos masivos (100+ movimientos), consistencia MV vs cálculo directo, lectura durante refresh
- [ ] Tests de UoW: rollback en segundo repositorio, conexión compartida, conexión liberada tras excepción
- [ ] Coverage `infrastructure/` ≥70%
- [ ] 0 regresiones en 97 tests de integración existentes
- [ ] Todos los edge case tests pasan contra testcontainers PostgreSQL real
- [ ] `make lint` pasa sin errores

### Spec-62: Tests E2E & Latencia <100ms
- [ ] `pytest-benchmark` añadido a `requirements.txt` y `pyproject.toml`
- [ ] `tests/e2e/conftest.py` con fixture `api_client` + benchmark config + SLA gate hook
- [ ] Tests de latencia: `/v1/stock/{id}/current` p95 < 100ms
- [ ] Tests de latencia: `/v1/stock/{id}/at-date` p95 < 100ms
- [ ] Tests de latencia: producto sin movimientos también < 100ms
- [ ] Tests de flujos completos: categoría → producto → movimiento → stock
- [ ] Tests de flujos completos: OUT con stock insuficiente → 409
- [ ] Tests de flujos completos: consistencia histórica entre fechas
- [ ] Tests de contratos OpenAPI: respuestas validan contra Pydantic DTOs
- [ ] SLA gate falla si p95 > 100ms en benchmarks de stock
- [ ] 0 regresiones en tests existentes
- [ ] `make lint` pasa sin errores

### Spec-63: Pruebas de Seguridad
- [ ] `tests/security/` directory con 3 archivos de test + conftest + __init__
- [ ] SQL injection tests: path params, query params, body fields, repository-level
- [ ] SQL injection tests: payloads OWASP Testing Guide v4 (mínimo 7 path payloads, 13 string payloads)
- [ ] SQL injection tests: ningún payload causa SQL syntax error o data modification
- [ ] Input validation tests: tipos incorrectos, rangos, campos requeridos, campos extra, metadata anidada
- [ ] Input validation tests: payloads malformados (JSON inválido, body vacío, content-type incorrecto, null, array)
- [ ] Input validation tests: Unicode edge cases (null bytes, emojis, strings largos)
- [ ] Error leakage tests: ningún error expone stack trace, SQL, rutas de archivos, versiones internas
- [ ] Immutability enforcement: PUT/PATCH/DELETE en /v1/movements/ → 405
- [ ] 0 regresiones en tests existentes
- [ ] `make lint` pasa sin errores

### Aggregate
- [ ] `make lint` sin errores en todos los archivos nuevos
- [ ] `make test` pasa todos los tests (no rompe tests existentes de F0-F5)
- [ ] `make typecheck` pasa (mypy strict en src/)
- [ ] Coverage global ≥80%
- [ ] `pyproject.toml` actualizado con Hypothesis + mypy config
- [ ] `requirements.txt` actualizado con +hypothesis +pytest-benchmark
- [ ] `Makefile` actualizado con +typecheck command
- [ ] 0 regresiones en 291 tests existentes

## Resolved Questions

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| F6-Q1 | ¿Herramienta de benchmark? | **pytest-benchmark** | In-process, sin servidor externo. Determinista. Se integra con pytest. Locust/k6 son para load testing externo |
| F6-Q2 | ¿Percentil SLA? | **p95 < 100ms** | Permite 5% de outliers por overhead de testcontainers. max y p99 son demasiado estrictos para CI con contenedores |
| F6-Q3 | ¿Hypothesis max_examples en CI? | **100** | Balance cobertura vs velocidad. 100 ejemplos detecta la mayoría de bugs. Profile dev con 1000 para local |
| F6-Q4 | ¿Hypothesis seed fijo? | **Sí, `--hypothesis-seed=0`** | Reproducibilidad total en CI. Si falla, se reproduce localmente con el mismo seed |
| F6-Q5 | ¿mypy strict scope? | **Solo `src/`** | Tests usan mocks, AsyncMock, fixtures dinámicas. Strict en tests añade fricción sin beneficio claro |
| F6-Q6 | ¿Scope de seguridad? | **SQL injection + input validation** | No hay auth en el sistema. Rate limiting y CORS son de F7+. Timing attacks requieren infraestructura fuera de scope |
| F6-Q7 | ¿Timing attack tests? | **No** | Requieren miles de muestras, análisis estadístico, y control del entorno de ejecución |
| F6-Q8 | ¿Nuevas dependencias de producción? | **Ninguna** | Solo dev dependencies (hypothesis, pytest-benchmark). Cero impacto en producción |
| F6-Q9 | ¿Coverage domain/ threshold? | **≥90%** (subido de >85%) | Con Hypothesis se generan más caminos de código; el umbral sube para reflejar mayor confianza |
| F6-Q10 | ¿Modificar tests existentes? | **No** — crear archivos `*_edge.py` | Los 291 tests existentes son happy paths validados. Modificarlos arriesga regresiones |
| F6-Q11 | ¿`type: ignore` permitido? | **Solo con justificación** | `# type: ignore[xxx] # Reason: ...` — nunca sin comentario explicativo |
| F6-Q12 | ¿Usar `sqlmap` para security tests? | **No** — tests manuales con pytest | `sqlmap` requiere servidor corriendo y es no-determinista. Los tests de pytest son deterministas, reproducibles, y se integran en CI |
| F6-Q13 | ¿Error leakage como test de seguridad? | **Sí** | Exponer stack traces o SQL en errores es una vulnerabilidad de información que facilita ataques |
| F6-Q14 | ¿Contratos OpenAPI con schema JSON o Pydantic? | **Pydantic model_validate()** | Los DTOs ya existen. Validar contra ellos es más directo y mantiene una sola fuente de verdad |

---

# Spec: stock-historial — F7: Despliegue & Documentación

## Objective

Preparar el sistema para producción con tres entregables complementarios: (1) **Dockerfile optimizado + `docker-compose.prod.yml`** self-contained con PostgreSQL persistente para despliegue local/demo (Spec-70); (2) **Documentación técnica completa** — reescribir todos los stubs (`ARCHITECTURE.md`, `API_REFERENCE.md`, `SETUP.md`), actualizar `README.md` a v1.0.0, y crear un **demo script funcional** que ejercite el flujo completo del sistema (Spec-71); (3) **CI/CD pipeline robusto** — extender `ci.yml` con mypy strict, Docker build validation, y quality gates completos (Spec-72).

**Usuarios objetivo:** Desarrolladores que despliegan localmente, equipos de ops que configuran el entorno, y evaluadores que necesitan una demo funcional del sistema.

**F7 success criteria:**
- `docker compose -f docker-compose.prod.yml up` levanta app + PostgreSQL con datos persistidos y healthchecks verdes
- `make demo` ejecuta el script de demostración completo end-to-end (categoría → producto → movimiento → stock)
- `docs/ARCHITECTURE.md` documenta Clean Architecture con diagramas Mermaid, reglas de importación, y justificación técnica
- `docs/API_REFERENCE.md` documenta los 10 endpoints con ejemplos `curl`, tablas de parámetros, y códigos de error
- `docs/SETUP.md` documenta setup paso a paso (prerequisitos → install → dev → prod → demo)
- `README.md` actualizado a v1.0.0 con badges, tabla de features, y links a documentación
- `.env.example` actualizado con todas las variables de F0-F7
- CI/CD pipeline: lint → typecheck → test → coverage → Docker build (5 gates, 0 deploy)
- `make lint` pasa con 0 errores
- Version 1.0.0 en `main.py`

## Tech Stack

| Componente | Tecnología | Notas |
|-----------|-----------|-------|
| Containerización | Docker + Docker Compose | Dockerfile multi-stage (ya existe), `docker-compose.prod.yml` nuevo |
| CI/CD | GitHub Actions | Extender `ci.yml` existente con typecheck + Docker build |
| Documentación | Markdown + Mermaid | Diagramas de arquitectura en `docs/ARCHITECTURE.md` |
| Demo Script | Bash + `curl` | `scripts/demo.sh` — flujo completo contra API local |
| **Nuevas dependencias** | Ninguna | F7 no añade deps de producción ni de desarrollo |

## Commands

```
Install: pip install -r requirements.txt
Dev: make dev
Lint: make lint
Typecheck: make typecheck
Format: make format
Test: make test
Test (cov): make test-cov
Build: make build
Docker up (dev): make docker-up
Docker down: make docker-down
Docker up (prod): docker compose -f docker-compose.prod.yml up -d
Docker down (prod): docker compose -f docker-compose.prod.yml down
Demo: make demo
Clean: make clean
```

## Project Structure

**Archivos nuevos que F7 crea:**

```
docker-compose.prod.yml # NEW: producción self-contained (app + PostgreSQL persistente)
scripts/demo.sh # NEW: demo script — flujo completo curl contra API

docs/
├── ARCHITECTURE.md # REWRITE: Clean Architecture + diagramas Mermaid + reglas de importación
├── API_REFERENCE.md # REWRITE: 10 endpoints documentados con ejemplos curl
└── SETUP.md # REWRITE: setup paso a paso (prereqs → install → dev → prod → demo)
```

**Archivos existentes que F7 modifica:**

```
Dockerfile # UPDATE: optimización (non-root user, .dockerignore, labels)
.dockerignore # NEW: excluir archivos innecesarios del contexto Docker
README.md # UPDATE: v1.0.0, badges, features, links a docs
.env.example # UPDATE: todas las variables F0-F7
.github/workflows/ci.yml # UPDATE: +typecheck job, +Docker build job
Makefile # UPDATE: +demo, +docker-prod-up/down commands
src/main.py # UPDATE: version 1.0.0
WORKFLOW.md # UPDATE: F7 completada, versión 1.0.0
AGENTS.md # UPDATE: F7 completada
CHANGELOG.md # UPDATE: entrada v1.0.0
docs/workflow/spec-tracking.md # UPDATE: Spec-70/71/72 completados
```

**Archivos de spec detallados:**

- [SPEC-70](specs/SPEC-70.md) — Dockerfile & Docker Compose Prod
- [SPEC-71](specs/SPEC-71.md) — README Técnico & Demo Script & Documentación Completa
- [SPEC-72](specs/SPEC-72.md) — CI/CD Pipeline

## Code Style

```bash
#!/usr/bin/env bash
# scripts/demo.sh — Demo script del sistema Stock Historial
# Ejecuta el flujo completo: categoría → producto → movimiento → stock
#
# Uso: make demo
# Con URL custom: DEMO_BASE_URL=http://staging:8000 make demo
# Prerequisitos: servidor corriendo en localhost:8000

set -euo pipefail

BASE_URL="${DEMO_BASE_URL:-http://localhost:8000}"
HEALTH_URL="${BASE_URL}/v1/health"

# 1. Verificar que el servidor está vivo
echo "🔍 Verificando salud del servidor..."
curl -sf "${HEALTH_URL}" | python3 -m json.tool

# 2. Crear categoría
echo "\n📦 Creando categoría 'Electrónica'..."
CATEGORY=$(curl -sf -X POST "${BASE_URL}/v1/categories" \
  -H "Content-Type: application/json" \
  -d '{"name": "Electrónica", "description": "Dispositivos electrónicos"}')
echo "$CATEGORY" | python3 -m json.tool
CATEGORY_ID=$(echo "$CATEGORY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. Crear producto
echo "\n📱 Creando producto 'Monitor 27\"'..."
PRODUCT=$(curl -sf -X POST "${BASE_URL}/v1/products" \
  -H "Content-Type: application/json" \
  -d "{
    \"sku\": \"MON-27-4K\",
    \"name\": \"Monitor 27 4K\",
    \"description\": \"Monitor IPS 4K 27 pulgadas\",
    \"unit_of_measure\": \"unit\",
    \"category_id\": ${CATEGORY_ID},
    \"min_stock_threshold\": 5
  }")
echo "$PRODUCT" | python3 -m json.tool
PRODUCT_ID=$(echo "$PRODUCT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 4. Registrar entrada de stock
echo "\n📥 Registrando IN de 50 unidades..."
MOVEMENT=$(curl -sf -X POST "${BASE_URL}/v1/movements" \
  -H "Content-Type: application/json" \
  -d "{
    \"product_id\": ${PRODUCT_ID},
    \"movement_type\": \"IN\",
    \"quantity\": 50,
    \"reference\": \"PO-2026-001\"
  }")
echo "$MOVEMENT" | python3 -m json.tool

# 5. Consultar stock actual
echo "\n📊 Consultando stock actual..."
STOCK=$(curl -sf "${BASE_URL}/v1/stock/${PRODUCT_ID}/current")
echo "$STOCK" | python3 -m json.tool

# 6. Registrar salida
echo "\n📤 Registrando OUT de 10 unidades..."
OUT=$(curl -sf -X POST "${BASE_URL}/v1/movements" \
  -H "Content-Type: application/json" \
  -d "{
    \"product_id\": ${PRODUCT_ID},
    \"movement_type\": \"OUT\",
    \"quantity\": 10,
    \"reference\": \"SO-2026-001\"
  }")
echo "$OUT" | python3 -m json.tool

# 7. Consultar stock actualizado
echo "\n📊 Stock después de la salida..."
STOCK2=$(curl -sf "${BASE_URL}/v1/stock/${PRODUCT_ID}/current")
echo "$STOCK2" | python3 -m json.tool

echo "\n✅ Demo completada exitosamente!"
```

**Convenciones específicas de F7:**
- Demo script: `set -euo pipefail`, `curl -sf`, `python3 -m json.tool` para formateo, `DEMO_BASE_URL` env var para URL base
- Docker compose prod: variables de entorno en `.env`, no hardcodeadas en YAML
- Documentación: diagramas Mermaid embebidos, ejemplos `curl` ejecutables, tablas de referencia
- `.dockerignore`: excluir `.venv/`, `.git/`, `__pycache__/`, `.mypy_cache/`, `htmlcov/`, `docs/ai-agent-setup/`, `.opencode/`, `skills/`, `agents/`, `references/`, `specs/`
- CI/CD: cada job independiente, Docker build cacheado vía GitHub Actions cache (`type=gha`)

## Testing Strategy

| Level | Location | Framework | Scope |
|-------|----------|-----------|-------|
| Docker Build | CI (GitHub Actions) | Docker | Validar que `docker build .` completa sin errores |
| Demo Script | Local | Bash + curl | Flujo E2E contra API local (manual) |

**F7 no añade tests unitarios ni de integración nuevos** — el objetivo es validar que la infraestructura de despliegue funciona, no añadir lógica de negocio. Los 205+ tests existentes (F0-F6) deben seguir pasando sin regresiones.

**Patrones de validación F7:**
- Docker build: `docker build -t stock-historial:latest .` en CI — exit code 0 = pass
- Docker compose prod: `docker compose -f docker-compose.prod.yml up -d` → `curl -sf http://localhost:8000/v1/health` → `{"status": "ok"}` → `docker compose -f docker-compose.prod.yml down`
- Demo script: `make demo` ejecuta sin errores contra servidor local
- CI: los 5 gates pasan (lint → typecheck → test → coverage → Docker build)

## Boundaries

### Always do
- Dockerfile usa multi-stage build con `python:3.12-slim` (ya existe, optimizar)
- `docker-compose.prod.yml` es self-contained (app + PostgreSQL + volumen persistente)
- `.env.example` documenta TODAS las variables del sistema (F0-F7)
- Demo script usa `set -euo pipefail` y `curl -sf` para fallo rápido
- CI/CD: cada job es independiente (sin acoplamiento entre gates)
- Documentación usa diagramas Mermaid (embebidos, sin herramientas externas)

### Ask first
- Añadir deploy automático (staging/prod) al CI/CD — fuera de scope F7 pero se puede añadir después
- Cambiar la imagen base de Docker (`python:3.12-slim` → `python:3.12-alpine` u otra)
- Añadir autenticación/API keys — la infraestructura está preparada pero no se implementa en F7
- Añadir reverse proxy (nginx/traefik) al stack de producción
- Cambiar el registry de Docker (Docker Hub → GHCR → ECR)
- Añadir monitoreo (Prometheus, Grafana) al stack de producción

### Never do
- Hardcodear credenciales en `docker-compose.prod.yml` (usar `.env`)
- Añadir dependencias de producción nuevas en F7
- Exponer puertos de PostgreSQL en producción (remover `ports: - "5432:5432"`)
- Ejecutar contenedor como root — usar `USER app` en Dockerfile runtime
- Modificar tests existentes (205+ tests de F0-F6)
- Añadir lógica de negocio nueva — F7 es solo infraestructura y documentación
- Incluir archivos de desarrollo en el contexto Docker (usar `.dockerignore`)

## Implementation Order

```
Spec-70 (Dockerfile & Docker Compose Prod)
↓ (dependencia: contenedor funcional para demo y CI)
Spec-71 (README + Documentación + Demo Script)
↓ (dependencia: demo script necesita API documentada)
Spec-72 (CI/CD Pipeline)
```

- **Spec-70 primero:** Optimiza el Dockerfile y crea `docker-compose.prod.yml`. Es la base que valida que el contenedor funciona. Spec-71 necesita un stack funcional para el demo script, y Spec-72 necesita un Dockerfile que compile para el Docker build gate.
- **Spec-71 segundo:** Reescribe la documentación y crea el demo script. Requiere que el stack Docker funcione (validado por Spec-70) para probar el demo script contra una instancia real.
- **Spec-72 tercero:** Extiende el CI/CD pipeline. Requiere que el Dockerfile compile (validado por Spec-70) para que el Docker build gate funcione en CI.

## Success Criteria

### Spec-70: Dockerfile & Docker Compose Prod
- [ ] Dockerfile optimizado: non-root user `app`, `.dockerignore` excluye archivos de desarrollo
- [ ] `docker build -t stock-historial:latest .` completa sin errores
- [ ] `docker-compose.prod.yml` incluye servicios `app` + `db` con volumen persistente y `restart: unless-stopped`
- [ ] `docker compose -f docker-compose.prod.yml up -d` levanta ambos servicios
- [ ] Healthcheck de app pasa: `curl -sf http://localhost:8000/v1/health` retorna `{"status": "ok"}`
- [ ] Puerto de PostgreSQL NO expuesto al host en producción (sin `ports: - "5432:5432"`)
- [ ] Variables de entorno en `.env`, no hardcodeadas en YAML
- [ ] Contenedor runtime ejecuta como usuario `app` (no root)
- [ ] Dockerfile incluye `LABEL` metadata OCI (title, description, version, source, licenses)
- [ ] `.env.example` actualizado con todas las variables F0-F7 (incluyendo scheduler, logging, timeouts)

### Spec-71: README Técnico & Demo Script & Documentación Completa
- [ ] `README.md` actualizado a v1.0.0 con: badges (CI, coverage, Python version, license), tabla de features, arquitectura resumida, links a docs, comandos, y estado del proyecto
- [ ] `docs/ARCHITECTURE.md` documenta: Clean Architecture con diagrama Mermaid, capas (domain → application → infrastructure → adapters), reglas de importación, justificación técnica (SQL explícito, asyncpg, APScheduler), patrones (Repository, UoW, CQRS, MV), y decisiones clave
- [ ] `docs/API_REFERENCE.md` documenta: los 10 endpoints con método, ruta, descripción, parámetros, request body, response body, códigos de error, ejemplos `curl` ejecutables, y ejemplos de error por endpoint (400, 404, 409, 422, 405)
- [ ] `docs/SETUP.md` documenta: prerequisitos, instalación, desarrollo local, Docker dev, Docker prod, demo, troubleshooting, y variables de entorno
- [ ] `scripts/demo.sh` ejecuta flujo completo: health → categoría → producto → IN → stock → OUT → stock actualizado
- [ ] Demo script soporta `DEMO_BASE_URL` env var (default `http://localhost:8000`)
- [ ] `make demo` ejecuta `scripts/demo.sh`
- [ ] Demo script usa `set -euo pipefail` y falla si el servidor no está disponible
- [ ] Demo script muestra output formateado con `python3 -m json.tool`

### Spec-72: CI/CD Pipeline
- [ ] `ci.yml` tiene 5 gates secuenciales: lint → typecheck → test → coverage → Docker build
- [ ] Gate typecheck: `make typecheck` (mypy strict en `src/`)
- [ ] Gate Docker build: `docker build -t stock-historial:latest .` exit code 0 (con GitHub Actions cache `type=gha`)
- [ ] Coverage gate: `--cov-fail-under=80` (existente, mantener)
- [ ] Cada job usa `actions/setup-python@v5` con Python 3.12
- [ ] Docker build job usa `docker/build-push-action` con `cache_from: type=gha` y `cache_to: type=gha`
- [ ] Pipeline falla si cualquier gate falla (0 tolerancia a warnings en lint)
- [ ] No hay deploy automático — solo validación continua

### Aggregate
- [ ] `make lint` sin errores
- [ ] `make test` pasa sin regresiones (205+ tests)
- [ ] `make typecheck` pasa (mypy strict en `src/`)
- [ ] `make demo` ejecuta exitosamente contra servidor local
- [ ] `docker compose -f docker-compose.prod.yml up -d` funciona end-to-end
- [ ] CI/CD pipeline pasa en GitHub Actions
- [ ] Version 1.0.0 en `main.py`
- [ ] `WORKFLOW.md` actualizado a F7 completada
- [ ] `CHANGELOG.md` actualizado con entrada v1.0.0
- [ ] `AGENTS.md` actualizado a F7 completada
- [ ] `docs/workflow/spec-tracking.md` actualizado: Spec-70/71/72 en estado Completado

## Resolved Questions

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| F7-Q1 | ¿Objetivo de despliegue? | **Docker local + demo** | No se requiere cloud. El sistema se valida localmente con Docker Compose. |
| F7-Q2 | ¿CI/CD scope? | **Lint + Test + Typecheck + Docker Build** | 5 gates de validación continua sin deploy automático. Deploy es manual. |
| F7-Q3 | ¿Alcance de documentación? | **Completo: reescribir todos los stubs** | Los 3 stubs (ARCHITECTURE, API_REFERENCE, SETUP) deben tener contenido productivo. |
| F7-Q4 | ¿PostgreSQL en docker-compose.prod.yml? | **Self-contained** | Un solo comando levanta todo. Facilita demo y evaluación. |
| F7-Q5 | ¿Actualizar .env.example? | **Sí, completo** | Documentar todas las variables F0-F7 para que nuevos desarrolladores tengan referencia completa. |
| F7-Q6 | ¿Añadir autenticación? | **No** | El sistema permanece como API abierta. La infraestructura Docker/CI no depende de auth. |
| F7-Q7 | ¿Reverse proxy (nginx)? | **No en F7** | El contenedor uvicorn es suficiente para demo/local. Se puede añadir en el futuro. |
| F7-Q8 | ¿Ejecutar contenedor como root? | **No — usuario `app`** | Best practice de seguridad. El Dockerfile runtime usa `USER app`. |
| F7-Q9 | ¿Exponer puerto PostgreSQL en prod? | **No** | Solo comunicación interna entre contenedores app↔db. Exponer el puerto es riesgo de seguridad. |
| F7-Q10 | ¿Nuevas dependencias? | **Ninguna** | F7 es infraestructura y documentación. Cero impacto en requirements.txt. |
| F7-Q11 | ¿`restart: unless-stopped` en prod compose? | **Sí** | Los servicios se reinician automáticamente tras crash o reboot del host. Solo se detienen con `docker compose down`. |
| F7-Q12 | ¿Dockerfile con `LABEL` metadata OCI? | **Sí, labels completos** | org.opencontainers.image.* labels mejoran descubrimiento y auditoría en registries. |
| F7-Q13 | ¿Caché de Docker layers en CI? | **Sí, GitHub Actions cache (`type=gha`)** | Reduce build time de ~2min a ~30s en runs subsecuentes. Usar `docker/build-push-action` con `cache_from`/`cache_to`. |
| F7-Q14 | ¿URL base en demo.sh? | **Sí, via `DEMO_BASE_URL` env var** | Consistente con el patrón `.env` del proyecto. Default `http://localhost:8000`. |
| F7-Q15 | ¿Ejemplos de error en API_REFERENCE? | **Sí, errores por endpoint** | Cada endpoint muestra 1-2 ejemplos de error más comunes (400, 404, 409, 422, 405). Más útil para consumidores de la API. |

## Open Questions

_Ninguna — todas las preguntas de F7 han sido resueltas (F7-Q1 a F7-Q15)._

