# Implementation Plan: F3 — Adaptadores de Datos

## Overview

F3 connects the pure domain (F2) with PostgreSQL (F1) by implementing:
- **4 concrete repositories** using `asyncpg` with explicit SQL and positional parameters (`$1`, `$2`)
- **3 pure mapper functions** (`asyncpg.Record` → domain entities)
- **Materialized view** (`mv_stock_historical`) with migration 008, 3 indexes, and refresh function
- **Unit of Work** pattern (`PostgresUnitOfWork`) for multi-repository transactions
- **IUnitOfWork protocol** in the domain layer

No new external dependencies. Zero ORM. SQL explicit always.

## Architecture Decisions (9 Resolved Questions)

| # | Decision | Impact |
|---|----------|--------|
| F3-Q1 | `get_current_stock()` → `float` | Maintain F2 port contract; explicit `float()` conversion |
| F3-Q2 | No batch `get_stock_for_multiple_products()` | YAGNI — defer to F5/F6 if needed |
| F3-Q3 | Mappers assume DB valid, validate types only | DB has CHECK/FK/trigger; mappers only transform types |
| F3-Q4 | No `category_id` in MV | Minimum viable; add later if needed |
| F3-Q5 | No timeout in `refresh_stock_view()` | Use PostgreSQL `statement_timeout` if needed |
| F3-Q6 | No admin refresh endpoint in F3 | Manual refresh via Python function; APScheduler in F5 |
| F3-Q7 | UoW: auto-only commit/rollback | Context manager only; no explicit `commit()`/`rollback()` |
| F3-Q8 | IUnitOfWork: only `connection` property | Minimal protocol contract |
| F3-Q9 | No UnitOfWorkFactory | Caller instantiates repos with `uow.connection` directly |

## Implementation Order

```
Spec-30 (Repositorios + Mappers)
    ↓
Spec-31 (Vistas Materializadas)
    ↓
Spec-32 (Unit of Work + IUnitOfWork Protocol)
```

## Dependency Graph

```
Domain Ports (F2, existing)
├── IMovementRepository ──────────────────────────────┐
├── IProductRepository ───────────────────────────────┤
├── ICategoryRepository ──────────────────────────────┤
├── IStockQueryRepository ────────────────────────────┤
│                                                      │
▼                                                      ▼
Mappers (pure functions)                    PostgresRepositories
├── map_category_row() ──────────────────► PostgresCategoryRepository
├── map_product_row()  ──────────────────► PostgresProductRepository
├── map_movement_row() ──────────────────► PostgresMovementRepository
│                                        │
│                                        └──► PostgresStockQueryRepository
│                                               (Spec-30: direct calc)
│                                               (Spec-31: MV + fallback)
│
├── Migration 008 ──► mv_stock_historical + 3 indexes
│       │
│       └──► refresh_stock_view() (refresh.py)
│
├── IUnitOfWork Protocol (new port in domain/ports/)
│       │
│       └──► PostgresUnitOfWork (uow.py)
│               │
│               └──► Repos share uow.connection for transactions
```

## Vertical Slicing Strategy

Slice work into testable vertical paths. Each slice delivers mappers + repo + tests:

```
Slice 1 (Category):  Mapper → CategoryRepo → Integration tests
Slice 2 (Product):   Mapper → ProductRepo  → Integration tests
Slice 3 (Movement):  Mapper → MovementRepo → Integration tests
Slice 4 (Stock):     StockQueryRepo (direct calc) → Integration tests
Slice 5 (UoW):       IUnitOfWork → PostgresUnitOfWork → Integration tests
Slice 6 (MV):        Migration 008 → refresh → StockQueryRepo (MV) → Tests
Slice 7 (Final):     make build, coverage, docs update
```

Slices 1-4 implement Spec-30. Slice 6 implements Spec-31. Slice 5 implements Spec-32.

---

## Phase 1: Spec-30 — Repositories + Mappers

### Task 1: Create mapper functions
- **Description:** Pure functions in `mappers.py` that transform `asyncpg.Record` → domain entities. No state, no I/O, fully deterministic. Mappers assume DB valid (CHECK constraints protect integrity) but throw domain exceptions on type mismatches.
- **Acceptance criteria:**
  - [ ] `map_category_row(record)` → `Category(id, name, description, created_at)`
  - [ ] `map_product_row(record)` → `Product` with `SKU(record["sku"])` VO construction
  - [ ] `map_movement_row(record)` → `Movement` with `MovementType(record["movement_type"])` and `Quantity(record["quantity"])`
  - [ ] `map_movement_row()` defaults `metadata` to `{}` when DB returns `None`
  - [ ] Invalid `movement_type` string raises `ValueError` (native Enum behavior)
  - [ ] Invalid SKU format raises `InvalidSKUError` (from SKU VO constructor)
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.infrastructure.repositories.mappers import map_category_row; print('OK')"`
- **Dependencies:** Domain entities and VOs from F2 (already exist)
- **Files:** `src/infrastructure/repositories/mappers.py`
- **Scope:** S (1 file, 3 functions)
- **Spec reference:** SPEC-30 § Mappers

### Task 2: Create PostgresCategoryRepository
- **Description:** Implements `ICategoryRepository` with explicit SQL. Simplest repo (3 methods, no pagination). Pattern: constructor accepts `pool` + optional `connection`, `_get_conn()` returns active connection.
- **Acceptance criteria:**
  - [ ] `PostgresCategoryRepository(pool, connection=None)` implements `ICategoryRepository`
  - [ ] `isinstance(repo, ICategoryRepository)` → `True`
  - [ ] `create()` inserts and returns entity with assigned `id`
  - [ ] `get_by_id()` returns `Category | None`
  - [ ] `list_all()` returns all categories ordered by name (no pagination)
  - [ ] All SQL uses positional parameters (`$1`, `$2`)
  - [ ] `make lint` passes
- **Verification:** Import + isinstance check; lint pass
- **Dependencies:** Task 1 (mappers)
- **Files:** `src/infrastructure/repositories/category_repository.py`
- **Scope:** S (1 file)
- **Spec reference:** SPEC-30 § PostgresCategoryRepository

### Task 3: Create PostgresProductRepository
- **Description:** Implements `IProductRepository` with 5 methods. Includes `list_below_threshold()` with CASE/SUM query against movements table (will be optimized in Spec-31 with MV but uses direct calculation for now).
- **Acceptance criteria:**
  - [ ] `PostgresProductRepository(pool, connection=None)` implements `IProductRepository`
  - [ ] `isinstance(repo, IProductRepository)` → `True`
  - [ ] `create()` inserts and returns entity with assigned `id`
  - [ ] `get_by_id(product_id)` → `Product | None`
  - [ ] `get_by_sku(sku: str)` → `Product | None` (accepts string, not VO)
  - [ ] `list_all(limit, offset)` with pagination
  - [ ] `list_below_threshold(limit)` uses CASE/SUM query against movements
  - [ ] All SQL uses positional parameters
  - [ ] `make lint` passes
- **Verification:** Import + isinstance check; lint pass
- **Dependencies:** Task 1 (mappers)
- **Files:** `src/infrastructure/repositories/product_repository.py`
- **Scope:** S (1 file)
- **Spec reference:** SPEC-30 § PostgresProductRepository

### Task 4: Create PostgresMovementRepository
- **Description:** Implements `IMovementRepository` with 3 methods (create, get_by_id, list_by_product). NO update/delete — movements are immutable. Metadata passed as dict to JSONB column.
- **Acceptance criteria:**
  - [ ] `PostgresMovementRepository(pool, connection=None)` implements `IMovementRepository`
  - [ ] `isinstance(repo, IMovementRepository)` → `True`
  - [ ] `create()` inserts and returns entity with assigned `id`
  - [ ] `get_by_id(movement_id)` → `Movement | None`
  - [ ] `list_by_product(product_id, limit, offset)` with pagination, ordered by `created_at DESC`
  - [ ] Repository has NO `update()` or `delete()` methods
  - [ ] All SQL uses positional parameters
  - [ ] `make lint` passes
- **Verification:** Import + isinstance check; verify no update/delete methods; lint pass
- **Dependencies:** Task 1 (mappers)
- **Files:** `src/infrastructure/repositories/movement_repository.py`
- **Scope:** S (1 file)
- **Spec reference:** SPEC-30 § PostgresMovementRepository

### Task 5: Create PostgresStockQueryRepository (direct calculation)
- **Description:** Implements `IStockQueryRepository` with direct CASE/SUM calculation against `movements` table. `get_current_stock()` returns `float`. `get_stock_at_date()` also uses direct calculation (MV only optimizes current stock, not historical).
- **Acceptance criteria:**
  - [ ] `PostgresStockQueryRepository(pool, connection=None)` implements `IStockQueryRepository`
  - [ ] `isinstance(repo, IStockQueryRepository)` → `True`
  - [ ] `get_current_stock(product_id)` → `float` (via `float(row["stock"])`)
  - [ ] `get_stock_at_date(product_id, datetime)` → `float` (via `float(row["stock"])`)
  - [ ] Returns `0.0` for products with no movements
  - [ ] All SQL uses positional parameters
  - [ ] `make lint` passes
- **Verification:** Import + isinstance check; lint pass
- **Dependencies:** Task 1 (mappers not needed — returns raw float, not entities)
- **Files:** `src/infrastructure/repositories/stock_query_repository.py`
- **Scope:** S (1 file)
- **Spec reference:** SPEC-30 § PostgresStockQueryRepository

### Task 6: Update repositories `__init__.py`
- **Description:** Re-export all 4 repositories and 3 mapper functions from `src/infrastructure/repositories/__init__.py`.
- **Acceptance criteria:**
  - [ ] `from src.infrastructure.repositories import PostgresMovementRepository` works
  - [ ] `from src.infrastructure.repositories import PostgresProductRepository` works
  - [ ] `from src.infrastructure.repositories import PostgresCategoryRepository` works
  - [ ] `from src.infrastructure.repositories import PostgresStockQueryRepository` works
  - [ ] `from src.infrastructure.repositories.mappers import map_movement_row` works
  - [ ] `make lint` passes
- **Verification:** Import smoke test
- **Dependencies:** Tasks 1-5
- **Files:** `src/infrastructure/repositories/__init__.py`
- **Scope:** XS (1 file)
- **Spec reference:** SPEC-30 § Files

### Task 7: Unit tests for mappers
- **Description:** Test mapper functions in isolation using mock `asyncpg.Record`-like objects (dicts with `__getitem__` access). Validate type transformations.
- **Acceptance criteria:**
  - [ ] `test_map_category_row` — valid record → Category with correct fields
  - [ ] `test_map_product_row` — valid record → Product with SKU VO constructed
  - [ ] `test_map_product_row_invalid_sku` — invalid SKU string → `InvalidSKUError`
  - [ ] `test_map_movement_row` — valid record → Movement with MovementType Enum and Quantity VO
  - [ ] `test_map_movement_row_metadata_none` — `None` metadata → defaults to `{}`
  - [ ] `test_map_movement_row_invalid_type` — invalid movement_type string → `ValueError`
  - [ ] `make lint` passes
- **Verification:** `pytest tests/unit/infrastructure/repositories/test_mappers.py -v`
- **Dependencies:** Tasks 1 (mappers)
- **Files:** `tests/unit/infrastructure/repositories/test_mappers.py`
- **Scope:** S (1 file)
- **Spec reference:** SPEC-30 § Testing Strategy

### Task 8: Integration tests for repositories
- **Description:** Integration tests for all 4 repositories using `testcontainers.postgres`. Reuse the existing `db_pool` fixture pattern from `tests/integration/test_db_schema.py`. Tests 4 files — split into separate test files for clarity.
- **Acceptance criteria:**
  - [ ] `test_category_repository.py` — create, get_by_id, get_by_id (not found), list_all
  - [ ] `test_product_repository.py` — create, get_by_id, get_by_sku, list_all (pagination), list_below_threshold (insert movements to push stock below threshold)
  - [ ] `test_movement_repository.py` — create, get_by_id, get_by_id (not found), list_by_product (pagination, ordering DESC)
  - [ ] `test_stock_query_repository.py` — get_current_stock (no movements → 0.0, with movements → correct value), get_stock_at_date
  - [ ] All tests use `db_pool` fixture with testcontainers + migrations
  - [ ] Repositories satisfy their respective Protocol interfaces
  - [ ] `make lint` passes
- **Verification:** `pytest tests/integration/repositories/ -v`
- **Dependencies:** Tasks 1-6 (all repos + mappers)
- **Files:** `tests/integration/repositories/test_category_repository.py`, `tests/integration/repositories/test_product_repository.py`, `tests/integration/repositories/test_movement_repository.py`, `tests/integration/repositories/test_stock_query_repository.py`
- **Scope:** M (4 files)
- **Spec reference:** SPEC-30 § Testing Strategy

### Checkpoint: Spec-30 Complete
- [ ] All 4 repositories implement their respective protocols
- [ ] All SQL uses positional parameters (`$1`, `$2`) — zero string concatenation
- [ ] Mappers are pure functions (stateless, no I/O, testable in isolation)
- [ ] Constructor accepts optional `connection` for UoW support
- [ ] `PostgresMovementRepository` has no `update()` or `delete()`
- [ ] `make lint` passes on all new files
- [ ] `pytest tests/unit/infrastructure/ tests/integration/repositories/ -v` passes
- [ ] Coverage for `src/infrastructure/repositories/` > 70%

---

## Phase 2: Spec-31 — Vistas Materializadas

### Task 9: Create migration 008 for materialized view
- **Description:** SQL migration creating `mv_stock_historical` with 3 indexes. View precalculates stock per product using the same CASE/SUM logic. Unique index on `product_id` is required for `REFRESH CONCURRENTLY`.
- **Acceptance criteria:**
  - [ ] `migrations/008_create_mv_stock_historical.sql` creates the view
  - [ ] View columns: `product_id`, `sku`, `product_name`, `current_stock`, `last_movement_at`, `calculated_at`
  - [ ] No `category_id` column in view (F3-Q4)
  - [ ] Unique index `ix_mv_stock_historical_product` on `product_id`
  - [ ] Index `ix_mv_stock_historical_stock` on `current_stock`
  - [ ] Index `ix_mv_stock_historical_last_movement` on `last_movement_at DESC`
  - [ ] Migration runs idempotently via `run_migrations()` (uses `IF NOT EXISTS` / `CREATE ... IF NOT EXISTS`)
  - [ ] `make migrate` applies migration successfully
- **Verification:** `make migrate` → check view and indexes exist in DB
- **Dependencies:** Phase 1 (repos exist but migration is independent SQL)
- **Files:** `migrations/008_create_mv_stock_historical.sql`
- **Scope:** S (1 file)
- **Spec reference:** SPEC-31 § Migration SQL

### Task 10: Create refresh_stock_view() function
- **Description:** Standalone function in `refresh.py` that executes `REFRESH MATERIALIZED VIEW CONCURRENTLY`. Handles `UndefinedTableError` gracefully (view not yet created). No timeout parameter (F3-Q5).
- **Acceptance criteria:**
  - [ ] `refresh_stock_view(pool)` executes `REFRESH MATERIALIZED VIEW CONCURRENTLY mv_stock_historical`
  - [ ] `UndefinedTableError` → logs warning, no exception raised
  - [ ] Other exceptions → logged and re-raised
  - [ ] Uses `logging.getLogger(__name__)` for structured logging
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.infrastructure.db.refresh import refresh_stock_view; print('OK')"`
- **Dependencies:** Task 9 (migration creates the view)
- **Files:** `src/infrastructure/db/refresh.py`
- **Scope:** XS (1 file)
- **Spec reference:** SPEC-31 § Function: refresh_stock_view()

### Task 11: Update PostgresStockQueryRepository to use MV
- **Description:** Update `get_current_stock()` to query `mv_stock_historical` instead of direct calculation. `get_stock_at_date()` remains unchanged (still uses direct calculation since MV only has current stock). Falls back to direct calculation if view doesn't exist.
- **Acceptance criteria:**
  - [ ] `get_current_stock()` queries `mv_stock_historical` via `SELECT current_stock FROM mv_stock_historical WHERE product_id = $1`
  - [ ] Falls back to direct calculation if view doesn't exist (catch `UndefinedTableError`)
  - [ ] `get_stock_at_date()` unchanged — still uses direct CASE/SUM against movements
  - [ ] Both methods return `float`
  - [ ] Returns `0.0` for products with no movements
  - [ ] `make lint` passes
- **Verification:** `make lint` passes; integration test validates consistency
- **Dependencies:** Tasks 9, 10 (migration + refresh), Task 5 (existing StockQueryRepo)
- **Files:** `src/infrastructure/repositories/stock_query_repository.py` (modification)
- **Scope:** S (1 file, modification)
- **Spec reference:** SPEC-31 § Integration with PostgresStockQueryRepository

### Task 12: Integration tests for materialized view
- **Description:** Tests for migration 008, refresh function, MV consistency with direct calculation, and fallback behavior.
- **Acceptance criteria:**
  - [ ] MV exists after migrations run (verify via `information_schema`)
  - [ ] Unique index exists (required for REFRESH CONCURRENTLY)
  - [ ] `refresh_stock_view()` executes without error after inserting movements
  - [ ] `get_current_stock()` returns same value as direct calculation (consistency test)
  - [ ] `get_stock_at_date()` works with direct calculation (not affected by MV)
  - [ ] Fallback: if view doesn't exist, `get_current_stock()` still works (direct calc)
  - [ ] `make lint` passes
- **Verification:** `pytest tests/integration/test_mv_stock.py -v`
- **Dependencies:** Tasks 9, 10, 11
- **Files:** `tests/integration/test_mv_stock.py`
- **Scope:** S (1 file)
- **Spec reference:** SPEC-31 § Testing Strategy

### Checkpoint: Spec-31 Complete
- [ ] `mv_stock_historical` view exists after migration 008
- [ ] Unique index `ix_mv_stock_historical_product` exists
- [ ] `refresh_stock_view()` executes without error
- [ ] `get_current_stock()` uses MV, returns same value as direct calculation
- [ ] `get_stock_at_date()` still uses direct calculation
- [ ] `make lint` passes
- [ ] Integration tests pass

---

## Phase 3: Spec-32 — Unit of Work

### Task 13: Create IUnitOfWork protocol
- **Description:** Domain-level protocol defining the minimum contract for transaction management: only the `connection` property. `@runtime_checkable` for mock validation in tests.
- **Acceptance criteria:**
  - [ ] `src/domain/ports/unit_of_work.py` exists with `@runtime_checkable` Protocol
  - [ ] Protocol has only `connection` property returning `asyncpg.Connection | None`
  - [ ] No `commit()` or `rollback()` methods on protocol (F3-Q8)
  - [ ] `isinstance(mock, IUnitOfWork)` works with a mock implementation
  - [ ] `src/domain/ports/__init__.py` re-exports `IUnitOfWork`
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.domain.ports import IUnitOfWork; print('OK')"`
- **Dependencies:** None (protocol only, no implementation dependency)
- **Files:** `src/domain/ports/unit_of_work.py`, `src/domain/ports/__init__.py`
- **Scope:** XS (2 files)
- **Spec reference:** SPEC-32 § Protocol: IUnitOfWork

### Task 14: Create PostgresUnitOfWork
- **Description:** Async context manager implementing `IUnitOfWork`. Acquires connection from pool, starts transaction, auto-commits on clean exit, auto-rollbacks on exception, always releases connection.
- **Acceptance criteria:**
  - [ ] `PostgresUnitOfWork(pool)` implements `IUnitOfWork`
  - [ ] `__aenter__` acquires connection and starts transaction
  - [ ] `__aexit__` commits on clean exit, rollbacks on exception
  - [ ] `finally` block always releases connection to pool
  - [ ] `connection` property returns active connection (None outside context)
  - [ ] No explicit `commit()` or `rollback()` methods (F3-Q7)
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.infrastructure.db.uow import PostgresUnitOfWork; print('OK')"`
- **Dependencies:** Task 13 (IUnitOfWork protocol)
- **Files:** `src/infrastructure/db/uow.py`
- **Scope:** S (1 file)
- **Spec reference:** SPEC-32 § Implementation: PostgresUnitOfWork

### Task 15: Integration tests for Unit of Work
- **Description:** Tests for commit, rollback, connection sharing between repos, and isolation.
- **Acceptance criteria:**
  - [ ] **Commit test:** create movement inside UoW, verify it persists after context exit
  - [ ] **Rollback test:** raise exception inside UoW, verify no data persisted
  - [ ] **Connection sharing test:** create 2 repos with same `uow.connection`, verify both operate in same transaction
  - [ ] **Isolation test:** operations outside UoW don't see uncommitted changes
  - [ ] **Connection release test:** connection is released to pool even if `__aexit__` fails
  - [ ] All tests use `db_pool` fixture with testcontainers
  - [ ] `make lint` passes
- **Verification:** `pytest tests/integration/test_uow.py -v`
- **Dependencies:** Tasks 13, 14, Tasks 1-6 (repos from Spec-30)
- **Files:** `tests/integration/test_uow.py`
- **Scope:** S (1 file)
- **Spec reference:** SPEC-32 § Testing Strategy

### Checkpoint: Spec-32 Complete
- [ ] `PostgresUnitOfWork` works as async context manager
- [ ] Rollback automatic on exception
- [ ] Commit automatic on clean exit
- [ ] Connection shared between multiple repos
- [ ] Connection always released to pool
- [ ] `IUnitOfWork` verifiable as Protocol
- [ ] `make lint` passes
- [ ] Integration tests pass

---

## Phase 4: Final Validation

### Task 16: Full build validation
- **Description:** Run full build pipeline (`make build`) to validate lint, format, and all tests pass. Check coverage target.
- **Acceptance criteria:**
  - [ ] `make lint` passes with 0 errors across all F3 files
  - [ ] `make format` passes (no changes needed)
  - [ ] `make test` passes (all unit + integration tests green)
  - [ ] Coverage for `src/infrastructure/` > 70%
  - [ ] No ORM imports in infrastructure
  - [ ] No string concatenation in SQL queries
  - [ ] Domain layer unchanged (no new imports from infrastructure in domain/)
- **Verification:** `make build` exit code 0; `make test-cov` shows >70% infrastructure coverage
- **Dependencies:** All tasks
- **Scope:** XS (validation only)

### Task 17: Update project documentation
- **Description:** Update WORKFLOW.md, spec-tracking.md, and README.md to reflect F3 completion.
- **Acceptance criteria:**
  - [ ] WORKFLOW.md: F3 status updated
  - [ ] `docs/workflow/spec-tracking.md`: Spec-30/31/32 marked as implemented
  - [ ] README.md: F3 marked as implemented
- **Verification:** Review updated files
- **Dependencies:** Task 16
- **Files:** `WORKFLOW.md`, `docs/workflow/spec-tracking.md`, `README.md`
- **Scope:** XS (3 files, documentation only)

### Checkpoint: F3 Complete
- [ ] All SPEC-30/31/32 acceptance criteria met
- [ ] `make build` passes
- [ ] Coverage `src/infrastructure/` > 70%
- [ ] Documentation updated
- [ ] Ready for human review → F4

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `asyncpg.Record` dict-like access fails with `record["col"]` | Medium | asyncpg.Record supports `__getitem__`; tested in integration tests |
| `REFRESH CONCURRENTLY` fails without unique index | High | Migration 008 creates unique index before view creation; test validates index exists |
| MV stale data between inserts and query | Medium | Fallback to direct calculation; refresh scheduled in F5 |
| UoW connection leak if `__aexit__` throws | High | `finally` block always releases connection regardless of exception |
| `list_below_threshold` query slow on large datasets | Low | Optimized in Spec-31 via MV; acceptable for F3 phase |
| Testcontainers startup time slows CI | Low | Each integration test gets isolated container; acceptable tradeoff for correctness |

## Parallelization Opportunities

**Safe to parallelize (no shared files):**
- Tasks 2, 3, 4 (Category, Product, Movement repos) — each is a separate file, shares only mappers (Task 1)
- Tests for each repo (Task 8) — separate test files, share only `db_pool` fixture

**Must be sequential:**
- Task 1 (mappers) before Tasks 2-5 (repos)
- Task 5 (StockQueryRepo direct) before Task 11 (StockQueryRepo MV update)
- Task 9 (migration) before Task 10 (refresh) before Task 11 (MV usage)
- Task 13 (IUnitOfWork protocol) before Task 14 (PostgresUnitOfWork)
- Task 14 (UoW implementation) before Task 15 (UoW tests)
- All Phase 4 tasks after Phases 1-3
