# Implementation Plan: F4 — Capa API (Casos de Uso + Endpoints)

## Overview

F4 implements the application layer (6 use cases + Pydantic DTOs) and the HTTP adapter layer (4 FastAPI routers, DI factories, error mapping middleware) that expose domain operations as a REST API. A **preliminary implementation** exists with all core code done (147 unit tests, `make lint` clean, version 0.4.0), but it lacks **integration tests for API endpoints** and **full validation**. This plan completes F4 by adding the missing integration test layer and finalizing documentation.

**What's done (preliminary):**
- 6 use cases with `async execute()` and DI in `__init__`
- 5 DTO files (Input strict mode, Output with examples, `ErrorResponse`)
- 4 routers (10 endpoints on `/v1/`)
- Error mapping middleware (6 exception handlers)
- 12 DI factory functions in `dependencies.py`
- Domain fixes: `validate_stock_not_negative(product_id=...)`, `count_by_product()`, `count_all()`
- 147 unit tests passing, `make lint` clean

**What's missing (this plan):**
- Integration tests for API endpoints (`tests/integration/api/` is empty)
- `count_by_product()` integration test in existing movement repo tests
- API test client fixture (`httpx.AsyncClient` with real DB)
- End-to-end validation of error mapping (domain exceptions → HTTP status codes)
- Coverage verification for `application/` (>85%) and `adapters/`
- Documentation finalization (WORKFLOW.md accuracy, spec-tracking completion)
- Cleanup of empty `application/interfaces/` directory

## Architecture Decisions (10 Resolved Questions from Preliminary)

| # | Decision | Impact |
|---|----------|--------|
| F4-Q1 | `count_by_product()` now, not later | Exact pagination totals from day one |
| F4-Q2 | Fix `validate_stock_not_negative()` with `product_id` now | Prevents misleading error messages |
| F4-Q3 | Append F4 spec to existing SPEC.md | Single source of truth pattern |
| F4-Q4 | Unit + Integration testing scope | Integration deferred to this plan |
| F4-Q5 | `ListProductsUseCase` returns `(items, total)` tuple | Precise pagination via `count_all()` |
| F4-Q6 | GET by ID goes direct to repo (CQRS) | No use case overhead for simple reads |
| F4-Q7 | Use cases as classes (not functions) | DI, immutability, testability |
| F4-Q8 | UoW only for OUT/TRANSFER | IN/ADJUSTMENT always increment stock |
| F4-Q9 | API snake_case (not camelCase) | Pythonic convention |
| F4-Q10 | Exception handlers (not middleware) | FastAPI idiomatic pattern |

## Dependency Graph

```
Domain (F2, existing) + Infrastructure (F3, existing)
│
├── Application Layer (DONE)
│   ├── Use Cases (6 classes) ──── DTOs (5 files)
│   │   ├── RecordMovementUseCase ←── IMovementRepo, IProductRepo, IStockQueryRepo, IUnitOfWork
│   │   ├── QueryCurrentStockUseCase ←── IStockQueryRepo
│   │   ├── QueryStockAtDateUseCase ←── IStockQueryRepo
│   │   ├── CreateProductUseCase ←── IProductRepo, ICategoryRepo
│   │   ├── ListProductsUseCase ←── IProductRepo
│   │   └── CreateCategoryUseCase ←── ICategoryRepo
│   │
│   └── DTOs ──── Pydantic models
│       ├── CreateMovementInput (strict, model_validator)
│       ├── MovementOutput, MovementListOutput
│       ├── CurrentStockOutput, StockAtDateOutput
│       ├── CreateProductInput, ProductOutput, ProductListOutput
│       ├── CreateCategoryInput, CategoryOutput
│       └── ErrorResponse, ErrorDetail
│
├── Adapter Layer (DONE)
│   ├── Routers (4) ──── DI Factories (12) ──── Error Handler (6)
│   │   ├── movements.py: POST, GET/{id}, GET?product_id=
│   │   ├── stock.py: GET/{id}/current, GET/{id}/at-date
│   │   ├── products.py: POST, GET, GET/{id}
│   │   └── categories.py: POST, GET
│   │
│   ├── dependencies.py ──── pool → repos → use cases
│   └── error_handler.py ──── DomainError → HTTP responses
│
└── Integration Tests (MISSING — this plan)
    ├── API client fixture (httpx.AsyncClient + real DB)
    ├── Endpoint tests (5 files)
    ├── Error mapping tests
    └── count_by_product() test
```

## Vertical Slicing Strategy

Each slice tests one complete feature path through the API:

```
Slice 1: API test client fixture (shared foundation)
Slice 2: count_by_product() integration test (independent)
Slice 3: Categories endpoints
Slice 4: Products endpoints
Slice 5: Movements endpoints
Slice 6: Stock endpoints
Slice 7: Error mapping end-to-end
Slice 8: Final validation, coverage, docs, cleanup
```

---

## Phase 1: Integration Test Foundation

### Task 1: Create API integration test client fixture

**Description:** Create an `httpx.AsyncClient` fixture in `tests/integration/api/conftest.py` that starts the FastAPI app with a real PostgreSQL (via testcontainers), overrides the pool dependency, and provides an async HTTP client for endpoint testing. This is the shared foundation all API integration tests depend on.

**Acceptance criteria:**
- [ ] `tests/integration/api/conftest.py` exists with `api_client` fixture
- [ ] Fixture uses `db_pool` from `tests/integration/conftest.py`
- [ ] Fixture overrides `get_db_pool` dependency in FastAPI app with the testcontainers pool
- [ ] Fixture yields `httpx.AsyncClient` using `ASGITransport` (not TestClient)
- [ ] Client connects to the real FastAPI app with real DB
- [ ] Migrations run before tests (via existing `db_pool` fixture)
- [ ] Seed data is available for read operations
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/api/conftest.py --co -q` collects fixture
- [ ] `python -c "from tests.integration.api.conftest import *; print('OK')"` succeeds

**Dependencies:** None (uses existing `db_pool` fixture)

**Files likely touched:**
- `tests/integration/api/conftest.py`

**Estimated scope:** S (1 file)

---

### Task 2: Add `count_by_product()` integration test

**Description:** Add tests for the newly added `count_by_product()` method to the existing `tests/integration/repositories/test_movement_repository.py`. This method was added during F4 but never integration-tested.

**Acceptance criteria:**
- [ ] `test_count_by_product_returns_correct_count` — create 3 movements for a product, verify count
- [ ] `test_count_by_product_returns_zero_for_no_movements` — product with no movements returns 0
- [ ] Tests appended to existing `test_movement_repository.py`
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/repositories/test_movement_repository.py -v -k count` passes

**Dependencies:** None (existing repo already has the method)

**Files likely touched:**
- `tests/integration/repositories/test_movement_repository.py`

**Estimated scope:** XS (1 file, 2 test functions)

---

### Checkpoint: Foundation Ready
- [ ] API client fixture works with real DB
- [ ] `count_by_product()` integration tests pass
- [ ] `make lint` passes
- [ ] Ready to write endpoint tests

---

## Phase 2: Endpoint Integration Tests

### Task 3: Categories endpoint integration tests

**Description:** Integration tests for `POST /v1/categories` and `GET /v1/categories`. This is the simplest vertical slice (2 endpoints, no pagination, no stock validation).

**Acceptance criteria:**
- [ ] `tests/integration/api/test_categories_api.py` exists
- [ ] `test_create_category_returns_201` — POST creates and returns category with `id` and `created_at`
- [ ] `test_create_category_empty_name_returns_422` — POST with empty name fails validation
- [ ] `test_list_categories_returns_200` — GET returns list of categories (seed data)
- [ ] `test_list_categories_after_create` — POST then GET shows new category
- [ ] All tests use `api_client` fixture
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/api/test_categories_api.py -v` passes

**Dependencies:** Task 1 (API client fixture)

**Files likely touched:**
- `tests/integration/api/test_categories_api.py`

**Estimated scope:** S (1 file, ~4 tests)

---

### Task 4: Products endpoint integration tests

**Description:** Integration tests for `POST /v1/products`, `GET /v1/products`, and `GET /v1/products/{id}`. Tests pagination, product creation with category validation, and 404 handling.

**Acceptance criteria:**
- [ ] `tests/integration/api/test_products_api.py` exists
- [ ] `test_create_product_returns_201` — POST creates product with valid data
- [ ] `test_create_product_invalid_sku_returns_422` — POST with bad SKU pattern fails
- [ ] `test_create_product_nonexistent_category_returns_400` — POST with invalid category_id raises ValueError → 400
- [ ] `test_list_products_returns_200_with_pagination` — GET returns paginated list with `total`
- [ ] `test_get_product_by_id_returns_200` — GET/{id} returns single product
- [ ] `test_get_product_by_id_not_found_returns_404` — GET/99999 returns 404
- [ ] `test_list_products_pagination_works` — GET with limit/offset returns correct page
- [ ] All tests use `api_client` fixture
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/api/test_products_api.py -v` passes

**Dependencies:** Task 1 (API client fixture)

**Files likely touched:**
- `tests/integration/api/test_products_api.py`

**Estimated scope:** M (1 file, ~7 tests)

---

### Task 5: Movements endpoint integration tests

**Description:** Integration tests for `POST /v1/movements`, `GET /v1/movements/{id}`, and `GET /v1/movements?product_id=`. This is the most complex slice — tests IN/OUT/ADJUSTMENT/TRANSFER creation, stock validation, metadata consistency, and pagination.

**Acceptance criteria:**
- [ ] `tests/integration/api/test_movements_api.py` exists
- [ ] `test_create_in_movement_returns_201` — POST with movement_type=IN succeeds
- [ ] `test_create_out_movement_with_stock_returns_201` — POST OUT when stock is sufficient
- [ ] `test_create_out_movement_insufficient_stock_returns_409` — POST OUT when stock < quantity → 409 with `INSUFFICIENT_STOCK` code
- [ ] `test_create_transfer_requires_metadata_returns_400` — POST TRANSFER without origin/destination → ValueError → 400
- [ ] `test_create_adjustment_requires_reason_returns_400` — POST ADJUSTMENT without reason → ValueError → 400
- [ ] `test_create_movement_invalid_product_returns_400` — POST with nonexistent product_id → ValueError → 400
- [ ] `test_get_movement_by_id_returns_200` — GET/{id} after POST returns same data
- [ ] `test_get_movement_not_found_returns_404` — GET/99999 returns 404
- [ ] `test_list_movements_by_product_returns_200` — GET?product_id= returns paginated list with `total`
- [ ] `test_list_movements_pagination` — GET?product_id=&limit=&offset= works correctly
- [ ] All tests use `api_client` fixture
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/api/test_movements_api.py -v` passes

**Dependencies:** Task 1 (API client fixture)

**Files likely touched:**
- `tests/integration/api/test_movements_api.py`

**Estimated scope:** M (1 file, ~10 tests)

---

### Task 6: Stock endpoint integration tests

**Description:** Integration tests for `GET /v1/stock/{product_id}/current` and `GET /v1/stock/{product_id}/at-date`. Tests stock calculation after movements and historical queries at specific dates.

**Acceptance criteria:**
- [ ] `tests/integration/api/test_stock_api.py` exists
- [ ] `test_get_current_stock_returns_200` — GET current returns stock after IN movements
- [ ] `test_get_current_stock_reflects_out_movements` — GET current after IN + OUT shows reduced stock
- [ ] `test_get_current_stock_no_movements_returns_zero` — GET current for product with no movements returns 0.0
- [ ] `test_get_stock_at_date_returns_200` — GET at-date with valid date returns historical stock
- [ ] `test_get_stock_at_date_with_iso8601_format` — GET at-date with ISO 8601 date string works
- [ ] All tests use `api_client` fixture
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/api/test_stock_api.py -v` passes

**Dependencies:** Task 1 (API client fixture)

**Files likely touched:**
- `tests/integration/api/test_stock_api.py`

**Estimated scope:** S (1 file, ~5 tests)

---

### Checkpoint: Endpoint Tests Complete
- [ ] All 4 router test files pass
- [ ] Categories: 4+ tests
- [ ] Products: 7+ tests
- [ ] Movements: 10+ tests
- [ ] Stock: 5+ tests
- [ ] `make lint` passes
- [ ] Ready for error mapping tests

---

## Phase 3: Error Mapping Integration Tests

### Task 7: Error mapping integration tests

**Description:** Integration tests that verify each domain exception maps to the correct HTTP status code and `ErrorResponse` format. These tests trigger domain exceptions through the API and validate the response body structure.

**Acceptance criteria:**
- [ ] `tests/integration/api/test_error_mapping_api.py` exists
- [ ] `test_insufficient_stock_returns_409` — OUT with quantity > stock → 409 with `{"error": {"code": "INSUFFICIENT_STOCK", ...}}`
- [ ] `test_insufficient_stock_includes_details` — 409 response includes `product_id`, `requested`, `available` in `details`
- [ ] `test_invalid_sku_returns_422` — Create product with bad SKU → 422 with `INVALID_SKU` code (Pydantic catches it first)
- [ ] `test_immutability_violation_returns_403` — Attempt to UPDATE/DELETE movement via direct SQL → 403 from trigger (tested via handler registration)
- [ ] `test_validation_error_returns_400` — TRANSFER without metadata → 400 with `VALIDATION_ERROR` code
- [ ] `test_error_response_format` — All error responses follow `{"error": {"code": "...", "message": "..."}}` structure
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/api/test_error_mapping_api.py -v` passes

**Dependencies:** Tasks 1, 5 (API client fixture + movements tests as reference)

**Files likely touched:**
- `tests/integration/api/test_error_mapping_api.py`

**Estimated scope:** S (1 file, ~6 tests)

---

### Checkpoint: Error Mapping Complete
- [ ] All 6 exception handlers produce correct HTTP responses
- [ ] `ErrorResponse` format is consistent across all error types
- [ ] `make lint` passes

---

## Phase 4: Final Validation & Documentation

### Task 8: Full build validation with coverage

**Description:** Run the complete build pipeline including integration tests. Verify coverage targets for `application/` (>85%) and overall project quality.

**Acceptance criteria:**
- [ ] `make lint` passes with 0 errors
- [ ] `make test` passes (unit + integration)
- [ ] Coverage for `src/application/` > 85%
- [ ] Coverage for `src/adapters/` > 70%
- [ ] No import violations (domain never imports infrastructure)
- [ ] OpenAPI `/docs` shows all 10 endpoints with correct schemas
- [ ] Version is 0.4.0 in `main.py`

**Verification:**
- [ ] `make build` exit code 0
- [ ] `make test-cov` shows >85% application coverage

**Dependencies:** All previous tasks

**Files likely touched:** None (validation only)

**Estimated scope:** XS (validation only)

---

### Task 9: Update project documentation

**Description:** Update WORKFLOW.md, spec-tracking.md, and roadmap to accurately reflect F4 completion. The current docs say "F4 completada" but that was premature — this task makes it accurate with integration test counts and final metrics.

**Acceptance criteria:**
- [ ] `WORKFLOW.md` — F4 status updated with accurate description including integration test counts
- [ ] `docs/workflow/spec-tracking.md` — Spec-40/41/42 checklists fully verified
- [ ] `docs/workflow/roadmap-phases.md` — F4 status changed from "En Progreso" to "Completado"
- [ ] `SPEC.md` F4 section — Success criteria checkboxes verified against actual implementation

**Verification:**
- [ ] Review updated files for accuracy

**Dependencies:** Task 8

**Files likely touched:**
- `WORKFLOW.md`
- `docs/workflow/spec-tracking.md`
- `docs/workflow/roadmap-phases.md`
- `SPEC.md` (F4 success criteria section only)

**Estimated scope:** S (4 files, documentation only)

---

### Task 10: Clean up empty `application/interfaces/` directory

**Description:** The `src/application/interfaces/` directory contains only an empty `__init__.py` with a placeholder comment. Remove it since no code references it and it adds no value (YAGNI).

**Acceptance criteria:**
- [ ] `src/application/interfaces/` directory removed
- [ ] No imports reference `src.application.interfaces` anywhere
- [ ] `make lint` passes
- [ ] `make test` passes

**Verification:**
- [ ] `grep -r "application.interfaces" src/ tests/` returns nothing
- [ ] `make lint` passes

**Dependencies:** None (independent cleanup)

**Files likely touched:**
- `src/application/interfaces/__init__.py` (deleted)
- `src/application/interfaces/` (directory deleted)

**Estimated scope:** XS (1 deletion)

---

### Checkpoint: F4 Complete
- [ ] All Spec-40/41/42 acceptance criteria met
- [ ] `make build` passes (lint + format + test)
- [ ] Coverage `src/application/` > 85%
- [ ] Integration tests for all 10 endpoints pass
- [ ] Error mapping validated end-to-end
- [ ] Documentation accurate and up-to-date
- [ ] No dead code (`application/interfaces/` cleaned)
- [ ] Ready for human review → F5

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `httpx.AsyncClient` with `ASGITransport` doesn't trigger lifespan | High | Override pool dependency manually in fixture; don't rely on lifespan |
| Testcontainers startup time (>120s) causes timeout | High | Run integration tests separately from unit tests; increase timeout |
| `InsufficientStockError` not triggered in integration (stock view stale) | Medium | Insert movements directly via pool before testing OUT; refresh MV if needed |
| `InvalidSKUError` caught by Pydantic before reaching domain | Low | Test both paths: Pydantic 422 for format, domain error for edge cases |
| `ImmutabilityViolationError` hard to trigger via API | Medium | Test via direct SQL attempt in a separate test, or verify handler is registered |
| Black formatter rejects `Annotated[..., Depends()]` after default params | Medium | Already fixed in preliminary — keep Depends params before Query params |

## Parallelization Opportunities

**Safe to parallelize (no shared files):**
- Tasks 2, 3, 4, 5, 6 (endpoint tests) — each is a separate file
- Task 10 (cleanup) — independent

**Must be sequential:**
- Task 1 (API client fixture) before Tasks 3-7 (all endpoint tests depend on it)
- Task 7 (error mapping tests) after Task 5 (uses movements patterns as reference)
- Task 8 (build validation) after all test tasks
- Task 9 (documentation) after Task 8 (needs final test counts)

## Open Questions

1. **`httpx.AsyncClient` vs `TestClient` for integration tests?** AsyncClient with `ASGITransport` is more realistic for async endpoints but TestClient is simpler. Recommendation: `httpx.AsyncClient` for parity with the async codebase.
2. **Should integration tests run as part of `make test` or separately?** Currently `make test` runs everything. Keep it that way unless testcontainers startup proves too slow.
3. **Remove `application/interfaces/` or keep as placeholder?** Recommendation: remove (YAGNI). No code references it.
