# Implementation Plan: F6 — Testing Integral

## Overview

F6 adds a comprehensive testing layer on top of the existing 291 tests (194 unit + 97 integration). It introduces four complementary test capabilities: (1) **Hypothesis property-based testing** for domain value objects and rules, (2) **mypy `--strict`** as a CI quality gate on `src/`, (3) **integration edge cases** covering unhappy paths and boundary conditions across repositories, MV, UoW, and API, (4) **E2E benchmarks** measuring p95 < 100ms SLA on stock queries plus OpenAPI contract validation, and (5) **security regression tests** for SQL injection (OWASP payloads), input validation, error leakage, and immutability enforcement.

**What's done (baseline from F0–F5):**
- 291 tests passing (194 unit + 97 integration), `make lint` clean, version 0.5.0
- Domain: `Quantity`, `SKU`, `MovementType` value objects; `calculate_stock_delta`, `validate_stock_not_negative` rules
- 6 domain exceptions: `DomainError` base + `InvalidQuantityError`, `InvalidSKUError`, `InsufficientStockError`, `ImmutabilityViolationError`, `ConcurrencyConflictError`
- 6 use cases: `RecordMovement`, `CreateProduct`, `ListProducts`, `QueryCurrentStock`, `QueryStockAtDate`, `CreateCategory`
- 5 DTOs: `CreateMovementInput(strict=True)`, `MovementOutput`, `CurrentStockOutput`, `StockAtDateOutput`, `ProductOutput`, `CategoryOutput`
- Infrastructure: asyncpg parameterized queries (`$1`, `$2`), `PostgresStockQueryRepository` with MV + fallback
- API: 5 routers (health, movements, stock, products, categories) + error handler + request logging middleware
- `db_pool`/`db_clean`/`api_client` fixtures already in `tests/integration/conftest.py` and `tests/integration/api/conftest.py`

**What's missing (this plan):**
- `hypothesis` + `pytest-benchmark` in `requirements.txt`
- `tests/unit/strategies.py` — centralized Hypothesis strategies
- Property-based tests for `Quantity`, `SKU`, `calculate_stock_delta`, `validate_stock_not_negative`
- Use case edge case tests (10 scenarios across 6 use cases)
- `mypy --strict` activation on `src/` + type annotation fixes
- `Makefile` `typecheck` command
- Integration edge case test files (10 new files: 4 repos + MV + UoW + 4 API)
- `tests/integration/helpers.py` — batch insert helper
- E2E test directory: `tests/e2e/conftest.py`, 3 test files, SLA gate hook
- Security test directory: `tests/security/`, 3 test files + conftest
- `pyproject.toml` updates: Hypothesis config, benchmark markers, mypy strict, addopts seed

## Architecture Decisions (from Spec Approval)

| # | Decision | Rationale |
|---|----------|-----------|
| F6-D1 | Hypothesis `max_examples=100`, `--hypothesis-seed=0` | Balance coverage vs CI speed. Reproducible failures. |
| F6-D2 | mypy `strict=true` only on `src/`; `tests.*` override `strict=false` | Mocks/fixtures don't benefit from strict typing. |
| F6-D3 | Edge cases in separate `*_edge.py` files, not modifying existing tests | Zero regression risk on 291 existing tests. |
| F6-D4 | `pytest-benchmark` (not Locust/k6) for latency | In-process, CI-friendly, no separate server needed. |
| F6-D5 | SLA gate as pytest hook (`pytest_benchmark_compare_stats`) | Automatic failure if p95 > 100ms. No manual assertions. |
| F6-D6 | p95 (not p99 or max) for SLA | Allows 5% outlier tolerance for container jitter in CI. |
| F6-D7 | Pydantic `model_validate()` for OpenAPI contracts | DTOs are single source of truth; no separate JSON schema needed. |
| F6-D8 | SQL injection: 4-layer defense (path → query → body → repo) | Defense in depth validation at each entry point. |
| F6-D9 | OWASP Testing Guide v4 payloads (not invented) | Industry standard; reduces false positives. |
| F6-D10 | Error leakage: body-only checks (no header version disclosure) | FastAPI/uvicorn don't add version headers by default. |
| F6-D11 | Coverage: domain/ ≥90%, application/ ≥85%, infrastructure/ ≥70%, global ≥80% | Reflects Hypothesis confidence in domain layer. |
| F6-D12 | Implementation order: Spec-60 → 61 → 62 → 63 (sequential) | Each spec builds on the previous; no safe parallelization. |

## Dependency Graph

```
pyproject.toml + requirements.txt (Task 1)
│
├── tests/unit/strategies.py (Task 2) ←── hypothesis dep (T1)
│   ├── tests/unit/domain PBT tests (Task 3) ←── strategies (T2)
│   └── tests/unit/application use case edge tests (Task 4) ←── strategies (T2) partial
│
├── mypy strict activation (Task 5) ←── pyproject.toml changes (T1)
│   └── Makefile typecheck (Task 5)
│
├── tests/integration/helpers.py (Task 6) ←── db_pool fixture (existing)
│   ├── tests/integration/repositories/*_edge.py (Task 7) ←── helpers (T6)
│   ├── tests/integration/test_mv_stock_edge.py (Task 8) ←── helpers (T6)
│   ├── tests/integration/test_uow_edge.py (Task 9) ←── existing UoW (F3)
│   └── tests/integration/api/*_edge.py (Task 10) ←── api_client fixture (existing)
│
├── tests/e2e/conftest.py (Task 11) ←── pytest-benchmark dep (T1) + db_pool/db_clean (existing)
│   ├── tests/e2e/test_stock_latency.py (Task 12) ←── e2e conftest (T11)
│   ├── tests/e2e/test_full_flows.py (Task 13) ←── e2e conftest (T11)
│   └── tests/e2e/test_openapi_contracts.py (Task 14) ←── e2e conftest (T11) + DTOs (existing)
│
├── tests/security/conftest.py (Task 15) ←── api_client fixture (existing) + db_pool (existing)
│   ├── tests/security/test_sql_injection.py (Task 16) ←── security conftest (T15)
│   ├── tests/security/test_input_validation.py (Task 17) ←── security conftest (T15)
│   └── tests/security/test_error_leakage.py (Task 18) ←── security conftest (T15)
│
└── Full build validation (Task 19) ←── ALL PREVIOUS
    └── Documentation update (Task 20) ←── Task 19
```

## Vertical Slicing Strategy

Each slice delivers one complete, testable capability:

```
Slice 1:  Dev dependencies + config foundation (Task 1) — all 4 specs need this
Slice 2:  Hypothesis strategies module (Task 2) — shared foundation for PBT
Slice 3:  Domain PBT tests (Task 3) — complete property-based coverage for domain
Slice 4:  Use case edge cases (Task 4) — complete edge coverage for application layer
Slice 5:  mypy strict + typecheck (Task 5) — type safety gate
Slice 6:  Integration helpers (Task 6) — shared SQL helpers for edge cases
Slice 7:  Repository edge cases (Task 7) — complete repository unhappy paths
Slice 8:  MV edge cases (Task 8) — complete MV validation with batch data
Slice 9:  UoW edge cases (Task 9) — complete UoW transaction validation
Slice 10: API edge cases (Task 10) — complete API boundary validation
Slice 11: E2E conftest + SLA gate (Task 11) — E2E infrastructure
Slice 12: Stock latency benchmarks (Task 12) — SLA p95 < 100ms validation
Slice 13: Full flow E2E tests (Task 13) — end-to-end user flows
Slice 14: OpenAPI contract tests (Task 14) — API contract validation
Slice 15: Security conftest (Task 15) — security test infrastructure
Slice 16: SQL injection tests (Task 16) — OWASP 4-layer defense validation
Slice 17: Input validation tests (Task 17) — boundary + malformed payload validation
Slice 18: Error leakage + immutability tests (Task 18) — info security + 405 enforcement
Slice 19: Full build validation (Task 19) — quality gate
Slice 20: Documentation update (Task 20) — traceability
```

---

## Phase 1: Foundation — Dependencies & Config (SPEC-60 partial)

### Task 1: Add dev dependencies + pyproject.toml configuration

**Description:** Add `hypothesis` and `pytest-benchmark` to `requirements.txt` (dev section). Update `pyproject.toml` with Hypothesis configuration (`[tool.hypothesis]`), benchmark markers, `--hypothesis-seed=0` in `addopts`, and `--cov-branch` in coverage run. This task creates the foundation that all subsequent tasks depend on.

**Acceptance criteria:**
- [ ] `hypothesis` added to dev dependencies in `requirements.txt`
- [ ] `pytest-benchmark` added to dev dependencies in `requirements.txt`
- [ ] `pyproject.toml` `[tool.hypothesis]` section: `max_examples = 100`
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` addopts: `"--hypothesis-seed=0"` appended
- [ ] `pyproject.toml` `[tool.pytest.ini_options]` markers: `"benchmark"`, `"e2e"`, `"security"`
- [ ] `pyproject.toml` `[tool.coverage.run]` already has `branch = true` (verify, no change needed)
- [ ] `pip install -r requirements.txt` succeeds
- [ ] `make lint` passes
- [ ] All 291 existing tests pass

**Verification:**
- [ ] `pip install -r requirements.txt` — no errors
- [ ] `python -c "import hypothesis; import pytest_benchmark; print('OK')"` succeeds
- [ ] `pytest tests/unit/ -v --co -q` — collects tests, no import errors
- [ ] `pytest --co -q` — 291 tests collected

**Dependencies:** None

**Files likely touched:**
- `requirements.txt`
- `pyproject.toml`

**Estimated scope:** S (2 files, config only)

---

## Phase 2: SPEC-60 — Unit Tests + Hypothesis + mypy strict

### Task 2: Create Hypothesis strategies module

**Description:** Create `tests/unit/strategies.py` with centralized, reusable Hypothesis strategies for all domain value objects and rules. This module is the single source of truth for PBT data generation — all property-based tests import from here.

**Acceptance criteria:**
- [ ] `tests/unit/strategies.py` exists
- [ ] `valid_quantity_strategy`: `st.integers(min_value=1, max_value=999_999)`
- [ ] `invalid_quantity_strategy`: `st.one_of(st.integers(max_value=0), st.just(0))`
- [ ] `valid_sku_strategy`: `st.from_regex(r'[A-Za-z0-9\-_]{1,50}', fullmatch=True)`
- [ ] `invalid_sku_strategy`: `st.one_of(st.text(min_size=51), st.from_regex(r'[!@#$%^&*()]+'), st.just(""))`
- [ ] `movement_type_strategy`: `st.sampled_from(list(MovementType))`
- [ ] `stock_delta_strategy`: `st.tuples(movement_type_strategy, valid_quantity_strategy)`
- [ ] `product_id_strategy`: `st.integers(min_value=1, max_value=999_999)`
- [ ] `current_stock_strategy`: `st.integers(min_value=0, max_value=999_999)`
- [ ] Hypothesis profiles registered: `"ci"` (100 examples), `"dev"` (1000 examples)
- [ ] Default profile loads `"ci"`
- [ ] Module-level docstring with usage examples
- [ ] `make lint` passes

**Verification:**
- [ ] `python -c "from tests.unit.strategies import valid_quantity_strategy, movement_type_strategy; print('OK')"` succeeds
- [ ] `pytest tests/unit/ -v --co -q` — no import errors from strategies

**Dependencies:** Task 1 (hypothesis dependency)

**Files likely touched:**
- `tests/unit/strategies.py` (new)

**Estimated scope:** S (1 file, ~70 lines)

---

### Task 3: Add property-based tests for domain value objects + rules

**Description:** Add Hypothesis `@given` tests to existing domain test files: `test_quantity.py`, `test_sku.py`, `test_rules.py`. These are additions to existing files (not new files), appended at the end. Tests verify that domain invariants hold for all generated inputs.

**Acceptance criteria:**
- [ ] `tests/unit/domain/test_quantity.py` — 2 new Hypothesis tests:
  - `test_quantity_valid_values`: property — every positive int creates valid Quantity
  - `test_quantity_rejects_non_positive`: property — every int ≤ 0 raises InvalidQuantityError
- [ ] `tests/unit/domain/test_sku.py` — 2 new Hypothesis tests:
  - `test_sku_valid_format`: property — every regex-matching string creates valid SKU
  - `test_sku_rejects_invalid_format`: property — non-matching strings raise InvalidSKUError
- [ ] `tests/unit/domain/test_rules.py` — 3 new Hypothesis tests:
  - `test_calculate_stock_delta_sign`: property — IN/ADJUSTMENT → positive, OUT/TRANSFER → negative
  - `test_calculate_stock_delta_never_zero_for_valid_qty`: property — valid qty never produces delta=0
  - `test_validate_stock_not_negative_raises_for_insufficient`: property — OUT/TRANSFER with qty > stock raises InsufficientStockError
- [ ] All new tests use strategies from `tests/unit/strategies.py`
- [ ] All 194 existing unit tests still pass (zero regressions)
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/unit/domain/test_quantity.py tests/unit/domain/test_sku.py tests/unit/domain/test_rules.py -v` — all pass
- [ ] `pytest tests/unit/ -v` — 194 + 7 new = 201+ tests pass

**Dependencies:** Task 2 (strategies module)

**Files likely touched:**
- `tests/unit/domain/test_quantity.py` (modify — append PBT tests)
- `tests/unit/domain/test_sku.py` (modify — append PBT tests)
- `tests/unit/domain/test_rules.py` (modify — append PBT tests)

**Estimated scope:** S (3 files, ~80 lines total)

---

### Task 4: Add edge case tests for use cases

**Description:** Add example-based edge case tests to existing use case test files. These cover unhappy paths not tested in F2-F4: product not found, duplicate SKU, category not found, offset > total, limit=0, stock=0, future date, invalid metadata for TRANSFER/ADJUSTMENT.

**Acceptance criteria:**
- [ ] `tests/unit/application/use_cases/test_record_movement.py` — 3 new edge tests:
  - Product not found → `ProductNotFoundError` or `ValueError`
  - OUT with stock=0 → `InsufficientStockError`
  - TRANSFER without origin/destination metadata → `ValueError`
- [ ] `tests/unit/application/use_cases/test_create_product.py` — 2 new edge tests:
  - Duplicate SKU → `DuplicateSKUError` propagated
  - Nonexistent category_id → FK validation error
- [ ] `tests/unit/application/use_cases/test_list_products.py` — 2 new edge tests:
  - Offset > total products → empty list, correct total
  - Limit=0 → empty list, correct total
- [ ] `tests/unit/application/use_cases/test_query_current_stock.py` — 1 new edge test:
  - Product without movements → stock = 0.0
- [ ] `tests/unit/application/use_cases/test_query_stock_at_date.py` — 1 new edge test:
  - Future date → stock = 0.0 (no future movements)
- [ ] `tests/unit/application/use_cases/test_create_category.py` — 1 new edge test:
  - Duplicate name → `UniqueViolationError` propagated
- [ ] All existing unit tests still pass (zero regressions)
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/unit/application/use_cases/ -v` — all pass
- [ ] `pytest tests/unit/ -v` — 201 + 10 = 211+ tests pass

**Dependencies:** Task 2 (strategies for partial reuse in edge cases)

**Files likely touched:**
- `tests/unit/application/use_cases/test_record_movement.py` (modify)
- `tests/unit/application/use_cases/test_create_product.py` (modify)
- `tests/unit/application/use_cases/test_list_products.py` (modify)
- `tests/unit/application/use_cases/test_query_current_stock.py` (modify)
- `tests/unit/application/use_cases/test_query_stock_at_date.py` (modify)
- `tests/unit/application/use_cases/test_create_category.py` (modify)

**Estimated scope:** M (6 files, ~120 lines total)

---

### Task 5: Activate mypy strict on src/ + Makefile typecheck command

**Description:** Update `pyproject.toml` to set `strict = true` under `[tool.mypy]` and add an override for `tests.*` with `strict = false`. Fix all type annotation issues that `mypy --strict` surfaces in `src/`. Add `typecheck` command to `Makefile`.

**Acceptance criteria:**
- [ ] `pyproject.toml` `[tool.mypy]` strict = true
- [ ] `pyproject.toml` `[[tool.mypy.overrides]]` module = "tests.*", strict = false, disallow_untyped_defs = false, disallow_incomplete_defs = false
- [ ] `mypy src/ --strict` passes with 0 errors
- [ ] All `# type: ignore[xxx]` have explanatory comments
- [ ] `Makefile` has `typecheck: mypy src/ --strict` command
- [ ] `.PHONY` updated to include `typecheck`
- [ ] `make help` shows `typecheck` command
- [ ] `make lint` passes
- [ ] All existing tests pass

**Verification:**
- [ ] `mypy src/ --strict` — 0 errors
- [ ] `make typecheck` — exit code 0
- [ ] `mypy tests/` — no new errors (tests stay strict=false)
- [ ] `pytest tests/ -v` — 291+ tests pass

**Dependencies:** Task 1 (pyproject.toml changes)

**Files likely touched:**
- `pyproject.toml` (modify — mypy strict + overrides)
- `Makefile` (modify — add typecheck)
- `src/**/*.py` (modify — type annotations only, no logic changes)

**Estimated scope:** M (3-5 files expected for type fixes, typically: missing return types, `Any` in *args/**kwargs, dataclass annotations)

---

### Checkpoint: SPEC-60 Complete
- [ ] Hypothesis installed and configured (`--hypothesis-seed=0`, `max_examples=100`)
- [ ] Strategies module with 7 strategies + 2 profiles
- [ ] 7 property-based tests for domain value objects and rules
- [ ] 10 edge case tests for use cases
- [ ] `mypy src/ --strict` passes with 0 errors
- [ ] `make typecheck` available and passing
- [ ] Coverage domain/ ≥90%, application/ ≥85% (verify after)
- [ ] All 291 existing tests pass + 17+ new tests
- [ ] `make lint` passes

---

## Phase 3: SPEC-61 — Integration Edge Cases

### Task 6: Create integration test helpers module

**Description:** Create `tests/integration/helpers.py` with the `insert_batch_movements()` async function for efficient batch SQL inserts. This helper is shared by MV edge cases (Task 8) and any other tests needing mass data setup.

**Acceptance criteria:**
- [ ] `tests/integration/helpers.py` exists
- [ ] `insert_batch_movements(pool, product_id, count, movement_type, quantity)` async function
- [ ] Uses `pool.executemany()` for efficient batch insert
- [ ] Inserts with randomized `created_at` (past timestamps) for historical diversity
- [ ] Helper for creating test product: `_create_test_product(pool, sku, name, category_name)`
- [ ] Helper for creating test movement: `_create_test_movement(pool, product_id, movement_type, quantity)`
- [ ] Module docstring with usage examples
- [ ] `make lint` passes

**Verification:**
- [ ] `python -c "from tests.integration.helpers import insert_batch_movements; print('OK')"` succeeds
- [ ] `make lint` passes

**Dependencies:** Task 1 (dependencies installed), existing `db_pool` fixture

**Files likely touched:**
- `tests/integration/helpers.py` (new)

**Estimated scope:** S (1 file, ~50 lines)

---

### Task 7: Add repository edge case tests

**Description:** Create 4 new edge case test files for repositories: movement, product, category, and stock_query. Each tests unhappy paths and boundary conditions against real PostgreSQL via testcontainers.

**Acceptance criteria:**
- [ ] `tests/integration/repositories/test_movement_repository_edge.py` — 6 tests:
  - `test_create_movement_returns_id` — ID > 0, same data
  - `test_get_by_id_not_found` — returns `None`
  - `test_list_by_product_empty` — empty list, total=0
  - `test_list_by_product_pagination_offset_exceeds` — offset > total → empty, correct total
  - `test_list_by_product_pagination_limit_zero` — limit=0 → empty, correct total
  - `test_count_by_product_no_movements` — count=0
- [ ] `tests/integration/repositories/test_product_repository_edge.py` — 5 tests:
  - `test_get_by_sku_not_found` — returns `None`
  - `test_get_by_id_not_found` — returns `None`
  - `test_list_below_threshold_none` — all above threshold → empty
  - `test_list_products_pagination_offset_exceeds` — offset > total → empty
  - `test_count_all_empty` — count=0
- [ ] `tests/integration/repositories/test_category_repository_edge.py` — 3 tests:
  - `test_get_by_id_not_found` — returns `None`
  - `test_list_all_empty` — empty list
  - `test_create_duplicate_name` — `UniqueViolationError`
- [ ] `tests/integration/repositories/test_stock_query_repository_edge.py` — 6 tests:
  - `test_get_current_stock_product_without_movements` — stock = 0.0
  - `test_get_stock_at_date_future_date` — stock = current (movements exist)
  - `test_get_stock_at_date_exact_movement_time` — includes that movement
  - `test_get_stock_at_date_before_any_movement` — stock = 0.0
  - `test_get_current_stock_after_mixed_movements` — net stock correct
  - `test_get_current_stock_fallback_without_mv` — MV dropped → fallback works
- [ ] All use `db_clean` fixture for isolation
- [ ] 97 existing integration tests pass (zero regressions)
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/repositories/ -v` — all pass (97 existing + 20 new)
- [ ] `pytest tests/integration/ -v` — 117+ tests pass

**Dependencies:** Task 6 (helpers module)

**Files likely touched:**
- `tests/integration/repositories/test_movement_repository_edge.py` (new)
- `tests/integration/repositories/test_product_repository_edge.py` (new)
- `tests/integration/repositories/test_category_repository_edge.py` (new)
- `tests/integration/repositories/test_stock_query_repository_edge.py` (new)

**Estimated scope:** M (4 files, ~250 lines total)

---

### Task 8: Add materialized view edge case tests

**Description:** Create `tests/integration/test_mv_stock_edge.py` with tests for MV consistency under various data volumes and concurrent operations.

**Acceptance criteria:**
- [ ] `tests/integration/test_mv_stock_edge.py` — 5 tests:
  - `test_mv_consistency_with_100_movements` — 100 movements → refresh → MV == direct calculation
  - `test_mv_refresh_concurrently_does_not_block_reads` — read during CONCURRENT REFRESH → no error
  - `test_mv_data_after_partial_truncate` — TRUNCATE + refresh → MV reflects current data
  - `test_mv_stock_multiple_products` — 10 products × 10 movements → correct per-product stock
  - `test_mv_refresh_after_large_batch` — 500 movements + refresh → correct, no timeout
- [ ] Uses `insert_batch_movements()` from helpers (Task 6)
- [ ] Each test uses `db_clean` for isolation
- [ ] 30s timeout on large batch test
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/test_mv_stock_edge.py -v` — all 5 pass
- [ ] `pytest tests/integration/ -v` — 122+ tests pass

**Dependencies:** Task 6 (helpers module)

**Files likely touched:**
- `tests/integration/test_mv_stock_edge.py` (new)

**Estimated scope:** S (1 file, ~100 lines)

---

### Task 9: Add Unit of Work edge case tests

**Description:** Create `tests/integration/test_uow_edge.py` with tests for UoW transactional behavior under error conditions.

**Acceptance criteria:**
- [ ] `tests/integration/test_uow_edge.py` — 4 tests:
  - `test_uow_rollback_on_second_repo_error` — error in 2nd repo → no data persisted
  - `test_uow_shared_connection_between_repos` — 2 repos in same transaction → consistent data
  - `test_uow_nested_context_managers` — nested UoW → defined behavior (error or reuse connection)
  - `test_uow_connection_released_after_exception` — connection released to pool after exception
- [ ] Each test uses `db_clean` for isolation
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/test_uow_edge.py -v` — all 4 pass
- [ ] `pytest tests/integration/ -v` — 126+ tests pass

**Dependencies:** None (existing UoW infrastructure from F3)

**Files likely touched:**
- `tests/integration/test_uow_edge.py` (new)

**Estimated scope:** S (1 file, ~80 lines)

---

### Task 10: Add API endpoint edge case tests

**Description:** Create 4 new edge case test files for API endpoints: movements, stock, products, categories. Each tests invalid inputs, boundary conditions, and error responses via `httpx.AsyncClient`.

**Acceptance criteria:**
- [ ] `tests/integration/api/test_movements_api_edge.py` — 6 tests:
  - `test_create_movement_invalid_product_id` — non-numeric → 422
  - `test_create_movement_empty_body` — no body → 422
  - `test_create_movement_extra_fields` — extra fields → 422 (strict mode)
  - `test_get_movement_nonexistent_id` — 404
  - `test_list_movements_invalid_product_id` — product_id=abc → 422
  - `test_create_movement_negative_quantity` — quantity=-5 → 422
- [ ] `tests/integration/api/test_stock_api_edge.py` — 3 tests:
  - `test_current_stock_nonexistent_product` — 404
  - `test_stock_at_date_invalid_date_format` — date=not-a-date → 422
  - `test_stock_at_date_no_query_param` — missing ?date= → 422
- [ ] `tests/integration/api/test_products_api_edge.py` — 5 tests:
  - `test_create_product_invalid_sku_format` — special chars → 422
  - `test_create_product_duplicate_sku` — existing SKU → 409
  - `test_create_product_nonexistent_category` — category_id=99999 → FK error
  - `test_list_products_large_offset` — offset=99999 → 200, empty
  - `test_get_product_nonexistent_id` — 404
- [ ] `tests/integration/api/test_categories_api_edge.py` — 3 tests:
  - `test_create_category_duplicate_name` — existing name → 409
  - `test_create_category_empty_name` — name="" → 422
  - `test_create_category_name_too_long` — 500+ chars → 422 or accept
- [ ] All use `api_client` fixture from `tests/integration/api/conftest.py`
- [ ] 97 existing integration tests pass (zero regressions)
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/api/ -v` — all pass (existing + 17 new)
- [ ] `pytest tests/integration/ -v` — 143+ tests pass

**Dependencies:** Task 6 (helpers for product setup), existing `api_client` fixture

**Files likely touched:**
- `tests/integration/api/test_movements_api_edge.py` (new)
- `tests/integration/api/test_stock_api_edge.py` (new)
- `tests/integration/api/test_products_api_edge.py` (new)
- `tests/integration/api/test_categories_api_edge.py` (new)

**Estimated scope:** M (4 files, ~200 lines total)

---

### Checkpoint: SPEC-61 Complete
- [ ] Integration helpers module with batch insert
- [ ] 20 repository edge case tests (4 files)
- [ ] 5 MV edge case tests (1 file)
- [ ] 4 UoW edge case tests (1 file)
- [ ] 17 API edge case tests (4 files)
- [ ] Coverage infrastructure/ ≥70%
- [ ] 97 existing integration tests pass (zero regressions)
- [ ] All edge case tests pass against testcontainers PostgreSQL
- [ ] `make lint` passes

---

## Phase 4: SPEC-62 — E2E & Latency <100ms

### Task 11: Create E2E conftest + SLA gate hook

**Description:** Create `tests/e2e/conftest.py` with the `api_client` fixture (reusing the integration pattern) and the SLA gate pytest hook that automatically fails if p95 > 100ms on stock benchmarks.

**Acceptance criteria:**
- [ ] `tests/e2e/__init__.py` exists (already exists, verify)
- [ ] `tests/e2e/conftest.py` exists
- [ ] `api_client` fixture: same pattern as `tests/integration/api/conftest.py` — `httpx.AsyncClient` + `ASGITransport` + `db_pool` override
- [ ] `STOCK_SLA_MS = 100.0` constant
- [ ] `pytest_benchmark_compare_stats` hook: checks p95 for benchmarks with "stock" in bench_id
- [ ] `pytest_benchmark_update_machine_info` hook: adds `testcontainers: True`
- [ ] Hook only fails for stock benchmarks (not other benchmark groups)
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/e2e/ --co -q` — no import errors
- [ ] `python -c "from tests.e2e.conftest import STOCK_SLA_MS; print(STOCK_SLA_MS)"` → 100.0

**Dependencies:** Task 1 (pytest-benchmark dependency)

**Files likely touched:**
- `tests/e2e/conftest.py` (new)

**Estimated scope:** S (1 file, ~60 lines)

---

### Task 12: Create stock latency benchmark tests

**Description:** Create `tests/e2e/test_stock_latency.py` with `pytest-benchmark` tests that measure p95 latency for stock queries. These validate the core product promise: <100ms stock lookups.

**Acceptance criteria:**
- [ ] `tests/e2e/test_stock_latency.py` exists
- [ ] `test_current_stock_latency` — benchmark GET /v1/stock/{id}/current, p95 < 100ms
- [ ] `test_stock_at_date_latency` — benchmark GET /v1/stock/{id}/at-date, p95 < 100ms
- [ ] `test_current_stock_no_movements_latency` — product without movements also < 100ms
- [ ] Helper: `_setup_product_with_movements(client)` — creates category + product + 10 movements
- [ ] All tests marked with `@pytest.mark.benchmark`
- [ ] Benchmark groups: `"stock-current"`, `"stock-at-date"`
- [ ] Minimum 5 rounds (`--benchmark-min-rounds=5`)
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/e2e/test_stock_latency.py -v --benchmark-only` — all pass, p95 < 100ms
- [ ] `pytest tests/e2e/test_stock_latency.py -v --benchmark-only --benchmark-json=bench_results.json` — JSON output generated

**Dependencies:** Task 11 (E2E conftest + SLA gate)

**Files likely touched:**
- `tests/e2e/test_stock_latency.py` (new)

**Estimated scope:** S (1 file, ~90 lines)

---

### Task 13: Create full flow E2E tests

**Description:** Create `tests/e2e/test_full_flows.py` with tests that validate complete user journeys through the system: create → move → query, error paths, and historical consistency.

**Acceptance criteria:**
- [ ] `tests/e2e/test_full_flows.py` exists
- [ ] `test_create_and_query_stock` — full happy path: category → product → IN movement → current stock → OUT movement → updated stock
- [ ] `test_insufficient_stock_flow` — OUT with qty > stock → 409 with INSUFFICIENT_STOCK code
- [ ] `test_historical_stock_consistency` — stock at different dates is consistent (before movement = 0, after = correct)
- [ ] All tests use `api_client` fixture
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/e2e/test_full_flows.py -v` — all 3 pass

**Dependencies:** Task 11 (E2E conftest)

**Files likely touched:**
- `tests/e2e/test_full_flows.py` (new)

**Estimated scope:** S (1 file, ~100 lines)

---

### Task 14: Create OpenAPI contract validation tests

**Description:** Create `tests/e2e/test_openapi_contracts.py` with tests that validate API responses against their Pydantic DTO schemas using `model_validate()`. This ensures the API contract stays in sync with the code.

**Acceptance criteria:**
- [ ] `tests/e2e/test_openapi_contracts.py` exists
- [ ] `test_movement_response_contract` — POST /v1/movements response validates against `MovementOutput`
- [ ] `test_current_stock_response_contract` — GET /v1/stock/{id}/current validates against `CurrentStockOutput`
- [ ] `test_product_list_response_contract` — GET /v1/products validates against `ProductListOutput`
- [ ] `test_category_response_contract` — POST /v1/categories validates against `CategoryOutput`
- [ ] All validations use `ModelClass.model_validate(resp.json())`
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/e2e/test_openapi_contracts.py -v` — all 4 pass

**Dependencies:** Task 11 (E2E conftest), existing DTO classes

**Files likely touched:**
- `tests/e2e/test_openapi_contracts.py` (new)

**Estimated scope:** S (1 file, ~80 lines)

---

### Checkpoint: SPEC-62 Complete
- [ ] E2E conftest with SLA gate hook (p95 < 100ms)
- [ ] 3 benchmark tests for stock latency — all p95 < 100ms
- [ ] 3 full flow E2E tests
- [ ] 4 OpenAPI contract validation tests
- [ ] SLA gate fails automatically if p95 > 100ms
- [ ] All existing tests pass (zero regressions)
- [ ] `make lint` passes

---

## Phase 5: SPEC-63 — Security Tests

### Task 15: Create security test conftest

**Description:** Create `tests/security/conftest.py` with shared fixtures for security tests. Reuses `db_pool` and `api_client` fixtures from integration, providing the same testcontainers infrastructure.

**Acceptance criteria:**
- [ ] `tests/security/__init__.py` exists
- [ ] `tests/security/conftest.py` exists
- [ ] Reuses `api_client` fixture (same pattern as integration)
- [ ] `db_pool` and `db_clean` accessible via `conftest.py` import or pytest plugin order
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/security/ --co -q` — no import errors

**Dependencies:** Task 1 (dependencies installed), existing integration fixtures

**Files likely touched:**
- `tests/security/__init__.py` (new — empty)
- `tests/security/conftest.py` (new)

**Estimated scope:** XS (2 files, ~30 lines)

---

### Task 16: Create SQL injection tests (OWASP 4-layer)

**Description:** Create `tests/security/test_sql_injection.py` with tests validating the system's immunity to SQL injection across 4 layers: path params, query params, body fields, and repository-level parameterized queries. Uses OWASP Testing Guide v4 payloads.

**Acceptance criteria:**
- [ ] `tests/security/test_sql_injection.py` exists
- [ ] `SQL_INJECTION_PATH_PARAMS` — 7 payloads: `1 OR 1=1`, `1; DROP TABLE`, `1 UNION SELECT`, `1' OR '1'='1`, etc.
- [ ] `SQL_INJECTION_STRING_FIELDS` — 13 payloads: `' OR '1'='1;--`, `'; DROP TABLE`, `<script>`, `${7*7}`, etc.
- [ ] `TestSQLInjectionPathParams` — 4 parametrized tests (stock current, stock at-date, movement get, product get) × 7 payloads
- [ ] `TestSQLInjectionQueryParams` — 4 tests (date injection, product_id injection, limit overflow, negative offset)
- [ ] `TestSQLInjectionBodyFields` — 2 parametrized tests (movement reference, product SKU) × 13 payloads
- [ ] `TestSQLInjectionRepositoryLevel` — 3 tests (movement repo type error, stock repo type error, parameterized literal storage)
- [ ] No payload causes SQL syntax error or data modification in responses
- [ ] No `"syntax error"` or `"sql"` in response bodies
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/security/test_sql_injection.py -v` — all pass
- [ ] Verify `movements` table still exists after tests (no DROP executed)

**Dependencies:** Task 15 (security conftest)

**Files likely touched:**
- `tests/security/test_sql_injection.py` (new)

**Estimated scope:** M (1 file, ~200 lines)

---

### Task 17: Create input validation tests

**Description:** Create `tests/security/test_input_validation.py` with boundary tests for Pydantic DTOs, malformed payloads, and Unicode edge cases.

**Acceptance criteria:**
- [ ] `tests/security/test_input_validation.py` exists
- [ ] `TestCreateMovementInputValidation` — 12 tests:
  - Missing required fields → 422
  - Extra fields rejected → 422 (strict mode)
  - Negative quantity → 422
  - Zero quantity → 422
  - Negative product_id → 422
  - Zero product_id → 422
  - Invalid movement_type → 422
  - Quantity as string → 422
  - Product_id as string → 422
  - Quantity overflow → 422 or 500
  - Reference too long → 422
  - TRANSFER without metadata → 422
  - ADJUSTMENT without reason → 422
  - Metadata with nested objects → 422
- [ ] `TestCreateProductInputValidation` — 4 tests:
  - Empty SKU → 422
  - SKU with special characters → 422
  - Nonexistent category_id → FK error
  - Negative min_stock_threshold → 422
- [ ] `TestCreateCategoryInputValidation` — 3 tests:
  - Empty name → 422
  - Name with only spaces → 201 or 422
  - Missing name field → 422
- [ ] `TestMalformedPayloads` — 5 tests:
  - Invalid JSON body → 422
  - Empty body → 422
  - Wrong content-type → 422 or 200
  - Null body → 422
  - Array body → 422
- [ ] `TestUnicodeEdgeCases` — 3 tests:
  - Null byte in reference → 422 or 500
  - Emoji in name → 201 (valid Unicode)
  - Very long metadata value → 201 or 422
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/security/test_input_validation.py -v` — all pass

**Dependencies:** Task 15 (security conftest)

**Files likely touched:**
- `tests/security/test_input_validation.py` (new)

**Estimated scope:** M (1 file, ~250 lines)

---

### Task 18: Create error leakage + immutability tests

**Description:** Create `tests/security/test_error_leakage.py` with tests that verify error responses don't expose internal information (stack traces, SQL, file paths) and that movement modification/deletion endpoints return 405.

**Acceptance criteria:**
- [ ] `tests/security/test_error_leakage.py` exists
- [ ] `LEAKAGE_PATTERNS` — 8 patterns: `traceback`, `stack trace`, `file "`, `line `, `.py"`, `asyncpg`, `psycopg`, `internal server error`
- [ ] `SQL_LEAKAGE_PATTERNS` — 9 patterns: `select `, `insert `, `update `, `delete `, `drop `, `from movements`, `from products`, `where `, `syntax error`
- [ ] `TestNoErrorLeakage` — 3 tests:
  - Validation errors (422) — no leakage patterns in body
  - 404 errors — no leakage patterns in body
  - Server errors — no stack trace in body
- [ ] `TestImmutabilityEnforcement` — 3 tests:
  - PUT /v1/movements/1 → 405
  - PATCH /v1/movements/1 → 405
  - DELETE /v1/movements/1 → 405
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/security/test_error_leakage.py -v` — all 6 pass

**Dependencies:** Task 15 (security conftest)

**Files likely touched:**
- `tests/security/test_error_leakage.py` (new)

**Estimated scope:** S (1 file, ~80 lines)

---

### Checkpoint: SPEC-63 Complete
- [ ] Security test directory with 3 test files + conftest + __init__
- [ ] SQL injection: 4 layers (path, query, body, repo) — OWASP payloads
- [ ] Input validation: 27 tests covering types, ranges, malformed, Unicode
- [ ] Error leakage: 6 tests — no stack traces, SQL, or file paths in errors
- [ ] Immutability: PUT/PATCH/DELETE → 405
- [ ] All existing tests pass (zero regressions)
- [ ] `make lint` passes

---

## Phase 6: Validation & Documentation

### Task 19: Full build validation + coverage gates

**Description:** Run the complete build pipeline. Verify all existing F0-F5 tests pass, all new F6 tests pass, coverage targets are met, mypy strict passes, and no regressions exist.

**Acceptance criteria:**
- [ ] `make lint` passes with 0 errors
- [ ] `make typecheck` passes with 0 errors
- [ ] `make test` passes (all F0-F6 tests)
- [ ] Coverage `src/domain/` ≥90%
- [ ] Coverage `src/application/` ≥85%
- [ ] Coverage `src/infrastructure/` ≥70%
- [ ] Coverage global ≥80%
- [ ] Total test count: 291 existing + 80+ new F6 tests = 370+ tests
- [ ] No import violations (domain never imports infrastructure)
- [ ] `make build` exit code 0
- [ ] Version is 0.5.0 (no version bump in F6 — testing phase only)

**Verification:**
- [ ] `make build` — exit code 0
- [ ] `make test-cov` — coverage targets met
- [ ] `pytest tests/unit/ -v` — all unit tests pass
- [ ] `pytest tests/integration/ -v` — all integration tests pass
- [ ] `pytest tests/e2e/ -v` — all E2E tests pass
- [ ] `pytest tests/security/ -v` — all security tests pass

**Dependencies:** All previous tasks

**Files likely touched:** None (validation only)

**Estimated scope:** XS (validation only)

---

### Task 20: Update project documentation

**Description:** Update project documentation files to reflect F6 completion. Update WORKFLOW.md, spec-tracking.md (SPEC-60/61/62/63 checklists), and SPEC.md (F6 success criteria checkboxes).

**Acceptance criteria:**
- [ ] `WORKFLOW.md` — F6 status updated to "Completada"
- [ ] `docs/workflow/spec-tracking.md` — SPEC-60/61/62/63 checklists fully verified
- [ ] `SPEC.md` — F6 success criteria checkboxes verified
- [ ] `AGENTS.md` — Phase updated to F6 completed

**Verification:**
- [ ] Review updated files for accuracy

**Dependencies:** Task 19

**Files likely touched:**
- `WORKFLOW.md`
- `docs/workflow/spec-tracking.md`
- `SPEC.md` (F6 success criteria section only)
- `AGENTS.md`

**Estimated scope:** S (4 files, documentation only)

---

### Checkpoint: F6 Complete
- [ ] All SPEC-60/61/62/63 acceptance criteria met
- [ ] `make build` passes
- [ ] Coverage targets met for all layers
- [ ] 80+ new tests pass (unit + integration + E2E + security)
- [ ] No regressions in existing F0-F5 tests (291 → 291)
- [ ] `mypy src/ --strict` passes
- [ ] SLA p95 < 100ms validated
- [ ] Security regression suite passing
- [ ] Documentation accurate and up-to-date
- [ ] Ready for human review → F7

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| mypy strict surfaces many type issues in `src/` | Medium | Fix incrementally; `# type: ignore[xxx] # Reason: ...` for legitimate cases. Pre-scan with `mypy src/ --strict` before starting Task 5. |
| `pytest-benchmark` + testcontainers p95 > 100ms in CI | High | Use p95 (not max) to allow 5% outliers. Increase `--benchmark-min-rounds` if flaky. Warmup round helps. |
| `db_clean` fixture not accessible from `tests/security/` | Medium | Security conftest imports from integration conftest, or pytest fixture discovery walks up directories. |
| `CreateMovementInput(strict=True)` rejects some OWASP payloads that are valid strings | Low | Expected behavior — payloads that pass Pydantic should be stored literally (not executed as SQL). Test asserts literal storage. |
| MV edge case tests (500 movements) slow in CI | Low | Uses `executemany()` (efficient). 30s timeout. CI typically runs faster than local. |
| Hypothesis `max_examples=100` not enough for some properties | Low | Dev profile with 1000 examples for local exploration. CI uses 100 for speed. |

## Parallelization Opportunities

**Safe to parallelize (no shared files):**
- Tasks 3 and 4 (domain PBT + use case edges) — after T2
- Tasks 7 and 8 and 9 (repo edges + MV edges + UoW edges) — after T6
- Tasks 12, 13, 14 (latency + flows + contracts) — after T11
- Tasks 16, 17, 18 (SQLi + input + leakage) — after T15

**Must be sequential:**
- Task 1 → Task 2 → Tasks 3/4 (dependency chain)
- Task 5 (mypy strict) — can run parallel with Tasks 2-4 but must complete before Task 19
- Task 6 → Task 7/8/9/10 (helpers dependency)
- Task 11 → Tasks 12/13/14 (conftest dependency)
- Task 15 → Tasks 16/17/18 (conftest dependency)
- Task 19 → Task 20 (validation before documentation)

## Implementation Order Reference

```
Task 1 (dependencies + config)
↓
Task 2 (strategies) ←── also Task 5 (mypy) can start here
↓
Tasks 3, 4 (parallel: domain PBT + use case edges)
↓
Task 6 (integration helpers)
↓
Tasks 7, 8, 9, 10 (parallel: repo + MV + UoW + API edges)
↓
Task 11 (E2E conftest)
↓
Tasks 12, 13, 14 (parallel: latency + flows + contracts)
↓
Task 15 (security conftest)
↓
Tasks 16, 17, 18 (parallel: SQLi + input + leakage)
↓
Task 19 (full build validation)
↓
Task 20 (documentation)
```
