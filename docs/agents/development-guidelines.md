# Development Guidelines

## Applied SOLID Principles

1. **SRP:** Each file has a single responsibility. `repositories.py` only handles data I/O. `use_cases.py` only orchestrates logic. `base_repository.py` centralizes connection management.
2. **OCP:** New movement types are added by extending classes or enums, not modifying existing conditionals.
3. **LSP:** Repository implementations must be substitutable by mocks without altering Pydantic contracts.
4. **DIP:** Use cases depend on protocols (`abc.ABC` or `typing.Protocol`), not on `asyncpg` directly.
5. **ISP:** Granular interfaces (`IMovementRepository`, `IStockQueryRepository`). `delete` methods are not exposed if the domain requires immutability.

## Design Patterns

- **Repository Pattern:** Abstracts PostgreSQL access. `create_movement()`, `get_stock_at_date()`. All repos inherit from `BasePostgresRepository`.
- **Unit of Work:** Explicit transactions via `asyncpg.transaction()`. Deterministic Commit/Rollback. If rollback fails with an active exception, the original exception is preserved.
- **Humble Object:** Complex logic in pure SQL. Python only validates, maps, and coordinates.
- **Strategy (Refresh):** Scheduler injects refresh policy. Allows future swapping without touching the domain.

## Conventions and Structure

```
src/
├── domain/          # Entities, exceptions, pure business rules, ports (protocols)
├── application/     # UseCases, DTOs (Pydantic Input/Output)
├── infrastructure/ # DB (connection, uow, migrations, seed), repositories (asyncpg wrappers), scheduler, logging
│ ├── db/ # connection.py, uow.py, migrate.py (non-transactional support), seed.py
│ ├── repositories/ # base_repository.py, movement_repository.py, product_repository.py, category_repository.py, stock_query_repository.py, mappers.py
│   ├── scheduler/   # APScheduler config
│   └── logging/     # Structured logging
├── adapters/        # FastAPI routers, controllers, dependency injection
└── main.py          # DI Container, setup, entrypoint
tests/
├── unit/            # Mocked protocols, pure business logic
├── integration/     # Testcontainers, real SQL, endpoints
└── e2e/             # Complete flows, basic load testing
```

## Pre-Commit Checklist

- [ ] Linter (`ruff`) without critical warnings.
- [ ] Format (`black`/`isort`) applied.
- [ ] Unit tests passing (`>80%` domain coverage).
- [ ] Migrations/queries validated with `EXPLAIN` on local staging.
- [ ] No hardcoded values, no `print()` in production, loggers configured.

## Error Handling and Fallbacks

- **Domain errors:** Specific exceptions (`ProductNotFoundError`, `CategoryNotFoundError`, `InsufficientStockError`) are mapped to HTTP status codes in middleware. Use cases raise domain exceptions (not generic `ValueError`).
- **DB errors:** `asyncpg.PostgresError` and `asyncpg.DataError` are caught in middleware → HTTP 500. Repositories do NOT wrap asyncpg errors in `ValueError`; they let them bubble up to the existing handler.
- **`ValueError` handler with origin verification:** The `handle_value_error` no longer catches all `ValueError` indiscriminately. It verifies the traceback to determine if the error originated in validation modules (`src/application/dtos`, `src/domain/value_objects`, `src/domain/entities`, `src/domain/rules`). Infrastructure errors are re-raised → HTTP 500. This prevents masking internal bugs as client errors.
- **Timeouts:** `statement_timeout` is configured via `server_settings` in `create_pool()`. The previous approach (`SET statement_timeout` post-creation) only affected the first connection, leaving the rest without a timeout.
- **Retries:** `@retry` decorator with exponential backoff for concurrency conflicts.
- **Mappers:** `JSONDecodeError` in JSONB metadata is handled with a fallback to `{}` and a warning log (no crash).
