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
