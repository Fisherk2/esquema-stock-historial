# TODO — F3: Adaptadores de Datos

## Progress: [17/17] ████████████████████ COMPLETADO

## Phase 1: Spec-30 — Repositorios + Mappers [8/8]

- [ ] **Task 1:** Create mapper functions
  - `src/infrastructure/repositories/mappers.py`
  - `map_category_row`, `map_product_row`, `map_movement_row`
  - Verify: `python -c "from src.infrastructure.repositories.mappers import map_category_row"`

- [ ] **Task 2:** Create PostgresCategoryRepository
  - `src/infrastructure/repositories/category_repository.py`
  - Implements `ICategoryRepository`: create, get_by_id, list_all
  - Verify: `isinstance(repo, ICategoryRepository)`

- [ ] **Task 3:** Create PostgresProductRepository
  - `src/infrastructure/repositories/product_repository.py`
  - Implements `IProductRepository`: create, get_by_id, get_by_sku, list_all, list_below_threshold
  - Verify: `isinstance(repo, IProductRepository)`

- [ ] **Task 4:** Create PostgresMovementRepository
  - `src/infrastructure/repositories/movement_repository.py`
  - Implements `IMovementRepository`: create, get_by_id, list_by_product (NO update/delete)
  - Verify: no update/delete methods

- [ ] **Task 5:** Create PostgresStockQueryRepository (direct calculation)
  - `src/infrastructure/repositories/stock_query_repository.py`
  - Implements `IStockQueryRepository`: get_current_stock (float), get_stock_at_date (float)
  - Verify: returns 0.0 for products with no movements

- [ ] **Task 6:** Update repositories `__init__.py`
  - `src/infrastructure/repositories/__init__.py`
  - Re-export all 4 repos + 3 mappers
  - Verify: `from src.infrastructure.repositories import PostgresMovementRepository`

- [ ] **Task 7:** Unit tests for mappers
  - `tests/unit/infrastructure/repositories/test_mappers.py`
  - Test: valid records, invalid SKU, None metadata, invalid movement_type
  - Verify: `pytest tests/unit/infrastructure/repositories/test_mappers.py -v`

- [ ] **Task 8:** Integration tests for repositories
  - `tests/integration/repositories/test_category_repository.py`
  - `tests/integration/repositories/test_product_repository.py`
  - `tests/integration/repositories/test_movement_repository.py`
  - `tests/integration/repositories/test_stock_query_repository.py`
  - Verify: `pytest tests/integration/repositories/ -v`

### Checkpoint: Spec-30 Complete [ ]
- [ ] All 4 repos implement their protocols
- [ ] All SQL uses `$1`, `$2` — zero string concatenation
- [ ] Mappers are pure functions
- [ ] Constructor accepts optional `connection`
- [ ] Movement repo has no update/delete
- [ ] `make lint` passes
- [ ] All repo tests pass
- [ ] Coverage `src/infrastructure/repositories/` > 70%

---

## Phase 2: Spec-31 — Vistas Materializadas [4/4]

- [ ] **Task 9:** Create migration 008 (MV + 3 indexes)
  - `migrations/008_create_mv_stock_historical.sql`
  - View: product_id, sku, product_name, current_stock, last_movement_at, calculated_at
  - Indexes: unique on product_id, on current_stock, on last_movement_at DESC
  - Verify: `make migrate` applies successfully

- [ ] **Task 10:** Create refresh_stock_view()
  - `src/infrastructure/db/refresh.py`
  - `REFRESH MATERIALIZED VIEW CONCURRENTLY` with UndefinedTableError handling
  - Verify: `from src.infrastructure.db.refresh import refresh_stock_view`

- [ ] **Task 11:** Update StockQueryRepo to use MV
  - `src/infrastructure/repositories/stock_query_repository.py` (modification)
  - `get_current_stock()` queries MV, fallback to direct calc if view missing
  - `get_stock_at_date()` unchanged (direct calc)
  - Verify: consistency test passes — MV value == direct calculation

- [ ] **Task 12:** Integration tests for MV
  - `tests/integration/test_mv_stock.py`
  - Test: MV exists, refresh works, consistency, fallback
  - Verify: `pytest tests/integration/test_mv_stock.py -v`

### Checkpoint: Spec-31 Complete [ ]
- [ ] `mv_stock_historical` exists after migration 008
- [ ] Unique index exists (REFRESH CONCURRENTLY)
- [ ] `refresh_stock_view()` executes without error
- [ ] `get_current_stock()` uses MV, matches direct calculation
- [ ] `get_stock_at_date()` uses direct calculation
- [ ] All MV tests pass

---

## Phase 3: Spec-32 — Unit of Work [3/3]

- [ ] **Task 13:** Create IUnitOfWork protocol
  - `src/domain/ports/unit_of_work.py`
  - `src/domain/ports/__init__.py` (update)
  - Only `connection` property, @runtime_checkable
  - Verify: `from src.domain.ports import IUnitOfWork`

- [ ] **Task 14:** Create PostgresUnitOfWork
  - `src/infrastructure/db/uow.py`
  - Async context manager: auto-commit, auto-rollback, always release
  - No explicit commit()/rollback() methods
  - Verify: `from src.infrastructure.db.uow import PostgresUnitOfWork`

- [ ] **Task 15:** Integration tests for UoW
  - `tests/integration/test_uow.py`
  - Test: commit, rollback, connection sharing, isolation, connection release
  - Verify: `pytest tests/integration/test_uow.py -v`

### Checkpoint: Spec-32 Complete [ ]
- [ ] PostgresUnitOfWork works as async context manager
- [ ] Rollback automatic on exception
- [ ] Commit automatic on clean exit
- [ ] Connection shared between repos
- [ ] Connection always released
- [ ] `IUnitOfWork` verifiable as Protocol
- [ ] All UoW tests pass

---

## Phase 4: Final Validation [2/2]

- [ ] **Task 16:** Full build validation
  - `make lint` → 0 errors
  - `make format` → no changes
  - `make test` → all green
  - `make test-cov` → infrastructure/ > 70%
  - Verify: `make build` exit code 0

- [ ] **Task 17:** Update project documentation
  - `WORKFLOW.md` — F3 status updated
  - `docs/workflow/spec-tracking.md` — Spec-30/31/32 marked implemented
  - `README.md` — F3 marked as implemented
  - Verify: review updated files

### Checkpoint: F3 Complete [ ]
- [ ] All SPEC-30/31/32 acceptance criteria met
- [ ] `make build` passes
- [ ] Coverage `src/infrastructure/` > 70%
- [ ] Documentation updated
- [ ] Ready for human review → F4

---

## Summary

| Phase | Tasks | Completed |
|-------|-------|-----------|
| Phase 1: Spec-30 (Repos + Mappers) | 8 | 8/8 |
| Phase 2: Spec-31 (MV) | 4 | 4/4 |
| Phase 3: Spec-32 (UoW) | 3 | 3/3 |
| Phase 4: Final Validation | 2 | 2/2 |
| **Total** | **17** | **17/17** |

---

## Implementation Order Reference

```
Task 1 (Mappers)
    ↓
Tasks 2, 3, 4, 5 (Repos — can be parallelized)
    ↓
Task 6 (__init__.py) → Task 7 (Mapper tests) → Task 8 (Repo tests)
    ↓
Task 9 (Migration 008) → Task 10 (Refresh) → Task 11 (MV usage) → Task 12 (MV tests)
    ↓
Task 13 (IUnitOfWork) → Task 14 (PostgresUnitOfWork) → Task 15 (UoW tests)
    ↓
Task 16 (Build validation) → Task 17 (Docs)
```

## Resolved Decisions (F3-Q1 through F3-Q9)

All 9 decisions are resolved and reflected in the specs. Key highlights:
- `get_current_stock()` → `float` (F3-Q1)
- No batch method (F3-Q2)
- Mappers assume DB valid, validate types only (F3-Q3)
- No category_id in MV (F3-Q4)
- No timeout in refresh (F3-Q5)
- No admin endpoint (F3-Q6)
- UoW: auto-only commit/rollback (F3-Q7)
- IUnitOfWork: only `connection` (F3-Q8)
- No UnitOfWorkFactory (F3-Q9)
