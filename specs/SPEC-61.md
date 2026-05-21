# SPEC-61: Integration Tests — Edge Cases & Extended Scenarios

**Phase:** F6 — Integral Testing
**Dependencies:** Spec-30 (Repositories) ✅ Completed, Spec-31 (Materialized Views) ✅ Completed, Spec-60 (Unit Tests) — Immediate prerequisite
**Priority:** High
**Status:** Approved

---

## Objective

Extend the existing integration test suite (97 tests) with edge cases and uncovered scenarios that validate the real behavior of repositories, the materialized view, the Unit of Work, and API endpoints against real PostgreSQL via testcontainers. The existing integration tests validate happy paths; Spec-61 adds unhappy paths, boundary conditions, and large data scenarios.

**Design principles:**
- **Reuse existing fixtures** — `db_pool` (session), `db_clean` (function), `api_client` (function) without modification
- **Zero regressions** — the 97 existing integration tests are not modified
- **Edge cases per layer** — repositories, MV, UoW, API endpoints each with their own edge cases
- **Large data** — test with 100+ movements to validate MV performance and pagination
- **Guaranteed isolation** — each test uses `db_clean` for clean state

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| Reuse `db_pool`/`db_clean` without changes | Existing fixtures are robust (1 container, ~20s). Modifying them risks regressions in 97 tests |
| Edge cases in separate files | Do not modify existing files. Create `test_*_edge_cases.py` for each module |
| Large data with SQL batch insert | 100+ movements inserted with `executemany` or `unnest` for efficiency. Do not use the API to create 100 movements |
| MV tests with and without refresh | Validate consistency between MV and direct calculation with different data volumes |
| API edge cases against `httpx.AsyncClient` | Same infrastructure as existing integration tests |

---

## Repository Edge Cases

### `tests/integration/repositories/test_movement_repository_edge.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_create_movement_returns_id` | Movement is created and returns auto-generated ID | ID > 0, same data |
| `test_get_by_id_not_found` | Search for non-existent movement | Returns `None` |
| `test_list_by_product_empty` | Product with no movements | Empty list, total=0 |
| `test_list_by_product_pagination_offset_exceeds` | Offset > total movements | Empty list, correct total |
| `test_list_by_product_pagination_limit_zero` | Limit=0 | Empty list, correct total |
| `test_count_by_product_no_movements` | Count movements for product with no movements | count=0 |

### `tests/integration/repositories/test_product_repository_edge.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_get_by_sku_not_found` | Search for non-existent SKU | Returns `None` |
| `test_get_by_id_not_found` | Search for non-existent product | Returns `None` |
| `test_list_below_threshold_none` | All products with stock > threshold | Empty list |
| `test_list_products_pagination_offset_exceeds` | Offset > total | Empty list, correct total |
| `test_count_all_empty` | Count products when there are none | count=0 |

### `tests/integration/repositories/test_category_repository_edge.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_get_by_id_not_found` | Search for non-existent category | Returns `None` |
| `test_list_all_empty` | List categories when there are none | Empty list |
| `test_create_duplicate_name` | Create category with duplicate name | `UniqueViolationError` from asyncpg |

### `tests/integration/repositories/test_stock_query_repository_edge.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_get_current_stock_product_without_movements` | Product with no movements | Stock = 0.0 |
| `test_get_stock_at_date_future_date` | Future date (no movements) | Stock = 0.0 |
| `test_get_stock_at_date_exact_movement_time` | Exact date of a movement | Includes that movement |
| `test_get_stock_at_date_before_any_movement` | Date before all movements | Stock = 0.0 |
| `test_get_current_stock_after_mixed_movements` | IN+OUT+ADJUSTMENT in sequence | Correct net stock |
| `test_get_current_stock_fallback_without_mv` | MV view dropped → fallback to direct calculation | Correct stock, no error |

---

## Materialized View Edge Cases

### `tests/integration/test_mv_stock_edge.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_mv_consistency_with_100_movements` | Insert 100 movements, refresh, compare MV vs direct calculation | Identical values |
| `test_mv_refresh_concurrently_does_not_block_reads` | Read during concurrent refresh | Read returns data (possibly stale), no error |
| `test_mv_data_after_partial_truncate` | TRUNCATE movements, refresh → MV updated | MV reflects current data |
| `test_mv_stock_multiple_products` | 10 products × 10 movements each | Correct stock per product |
| `test_mv_refresh_after_large_batch` | Batch insert of 500 movements + refresh | MV correct, no timeout with 30s |

### Batch Insert Helper

```python
# tests/integration/helpers.py
async def insert_batch_movements(
    pool: asyncpg.Pool,
    product_id: int,
    count: int,
    movement_type: str = "IN",
    quantity: int = 10,
) -> None:
    """Inserts N movements in batch for large data tests."""
    await pool.executemany(
        """
        INSERT INTO movements (product_id, movement_type, quantity, metadata, created_at)
        VALUES ($1, $2, $3, $4, now() - interval '1 minute' * (random() * 1000)::int)
        """,
        [(product_id, movement_type, quantity, "{}")] * count,
    )
```

---

## Unit of Work Edge Cases

### `tests/integration/test_uow_edge.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_uow_rollback_on_second_repo_error` | Error in second repository inside UoW | No data persisted |
| `test_uow_shared_connection_between_repos` | Two repos in same transaction share connection | Consistent data |
| `test_uow_nested_context_managers` | Nested UoW (if allowed) | Defined behavior (likely error or reuse connection) |
| `test_uow_connection_released_after_exception` | Connection released to pool even with exception | Pool size restored |

---

## API Endpoint Edge Cases

### `tests/integration/api/test_movements_api_edge.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_create_movement_invalid_product_id` | Non-numeric product_id in URL | 422 Unprocessable |
| `test_create_movement_empty_body` | POST without body | 422 Unprocessable |
| `test_create_movement_extra_fields` | POST with unknown extra fields | 422 (strict mode) or ignores |
| `test_get_movement_nonexistent_id` | GET /v1/movements/99999 | 404 Not Found |
| `test_list_movements_invalid_product_id` | product_id=abc in query param | 422 Unprocessable |
| `test_create_movement_negative_quantity` | quantity=-5 | 422 (Pydantic validation) |

### `tests/integration/api/test_stock_api_edge.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_current_stock_nonexistent_product` | GET /v1/stock/99999/current | 404 Not Found |
| `test_stock_at_date_invalid_date_format` | date=not-a-date | 422 Unprocessable |
| `test_stock_at_date_no_query_param` | GET /v1/stock/1/at-date without ?date= | 422 (missing required param) |

### `tests/integration/api/test_products_api_edge.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_create_product_invalid_sku_format` | SKU with special characters | 422 Unprocessable |
| `test_create_product_duplicate_sku` | SKU that already exists | 409 Conflict |
| `test_create_product_nonexistent_category` | category_id=99999 | FK error |
| `test_list_products_large_offset` | offset=99999 | 200, empty list |
| `test_get_product_nonexistent_id` | GET /v1/products/99999 | 404 Not Found |

### `tests/integration/api/test_categories_api_edge.py`

| Test | Description | Expected |
|------|-------------|----------|
| `test_create_category_duplicate_name` | Name that already exists | 409 Conflict |
| `test_create_category_empty_name` | name="" | 422 Unprocessable |
| `test_create_category_name_too_long` | name with 500+ characters | 422 or accepts (verify) |

---

## Files

| File | Description | Action |
|------|-------------|--------|
| `tests/integration/repositories/test_movement_repository_edge.py` | MovementRepository edge cases | NEW |
| `tests/integration/repositories/test_product_repository_edge.py` | ProductRepository edge cases | NEW |
| `tests/integration/repositories/test_category_repository_edge.py` | CategoryRepository edge cases | NEW |
| `tests/integration/repositories/test_stock_query_repository_edge.py` | StockQueryRepository edge cases | NEW |
| `tests/integration/test_mv_stock_edge.py` | MV edge cases with large data | NEW |
| `tests/integration/test_uow_edge.py` | Unit of Work edge cases | NEW |
| `tests/integration/api/test_movements_api_edge.py` | movements API edge cases | NEW |
| `tests/integration/api/test_stock_api_edge.py` | stock API edge cases | NEW |
| `tests/integration/api/test_products_api_edge.py` | products API edge cases | NEW |
| `tests/integration/api/test_categories_api_edge.py` | categories API edge cases | NEW |
| `tests/integration/helpers.py` | Helper for batch inserts | NEW |

---

## Acceptance Criteria

- [ ] Repository edge cases: product without movements, stock_at_date with future date, pagination with offset > total, get_by_id not found, count=0
- [ ] API edge cases: invalid content-type, empty body, extra fields, invalid query params, non-existent IDs, invalid dates, duplicates
- [ ] MV tests: refresh with large data (100+ movements), MV vs direct calculation consistency, read during refresh
- [ ] UoW tests: rollback on second repository, shared connection, connection released after exception
- [ ] Coverage `infrastructure/` ≥70%
- [ ] 0 regressions in 97 existing integration tests
- [ ] All edge case tests pass against real PostgreSQL testcontainers
- [ ] `make lint` passes without errors

---

## Testing Strategy

- **All tests use real PostgreSQL testcontainers** — no mocks for integration repositories
- **`db_clean` for each test** — clean data guarantees isolation
- **`api_client` for API tests** — httpx.AsyncClient with ASGITransport
- **Batch inserts for large data** — `executemany` for efficiency, not the API
- **MV vs direct calculation comparison** — insert → refresh → compare with manual SUM

### Example: Repository edge case test

```python
# tests/integration/repositories/test_stock_query_repository_edge.py
async def test_get_stock_at_date_future_date(db_clean: asyncpg.Pool) -> None:
    """Edge case: querying stock at a future date returns 0.0."""
    repo = PostgresStockQueryRepository(db_clean)

    # Create product and movement in the past
    product_id = await _create_test_product(db_clean)
    await _create_test_movement(db_clean, product_id, "IN", 100)

    # Query future date
    future_date = datetime.now(timezone.utc) + timedelta(days=365)
    stock = await repo.get_stock_at_date(product_id, future_date)

    # Future stock must be the same as current (future movements do not exist)
    assert stock == 100.0  # Existing movements count
```

---

## Resolved Questions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| F6-61-Q1 | Modify existing integration tests? | **No** — create separate `_edge.py` files | The 97 existing tests are validated happy paths. Modifying them risks regressions |
| F6-61-Q2 | Large data with API or direct SQL? | **Direct SQL (batch insert)** | Creating 100+ movements via API would be slow and fragile. Direct SQL is efficient and controlled |
| F6-61-Q3 | Test MV with large data (500+)? | **Yes, up to 500** | Validates that refresh does not timeout with 30s. Beyond 500 is for load testing (Spec-62) |
| F6-61-Q4 | Shared batch insert helper? | **Yes, `tests/integration/helpers.py`** | Avoids duplicating setup SQL between test files |
