# SPEC-62: E2E Tests & Latency <100ms

**Phase:** F6 — Comprehensive Testing
**Dependencies:** Spec-42 (FastAPI Routes) ✅ Completed, Spec-61 (Integration Edge Cases) — Immediate prerequisite
**Priority:** High
**Status:** Approved

---

## Objective

Implement the E2E (end-to-end) test suite that validates the **core product promise** of the system: historical stock queries in **<100ms**. This phase introduces `pytest-benchmark` to measure latency of critical endpoints, tests for complete HTTP flows (create category → product → movement → query stock), and OpenAPI contract validation against Pydantic schemas. E2E tests use the same testcontainers infrastructure as integration tests, but focused on latency, cross-cutting flows, and API contracts.

**Design principles:**
- **SLA gate: p95 < 100ms** — 95% of stock queries must respond in under 100ms
- **In-process benchmark** — `pytest-benchmark` measures latency within the test process (no external network)
- **Cross-cutting flows** — not testing an isolated endpoint but the complete sequence of operations
- **OpenAPI contracts** — JSON responses must match the defined Pydantic schemas
- **Zero regressions** — all existing tests must pass

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| `pytest-benchmark` (not Locust/k6) | In-process, no external server. Deterministic. Integrates with pytest. Sufficient for measuring handler + DB latency |
| **p95 < 100ms** as gate | p95 allows 5% outliers (testcontainers overhead). max and p99 are too strict for CI with containers |
| `httpx.AsyncClient` + `ASGITransport` | Already used in integration. Same infrastructure, no separate server |
| E2E reuses `db_pool`/`db_clean` | Single PostgreSQL container for the entire session. Consistent with integration |
| Benchmark with `--benchmark-min-rounds=5` | Minimum 5 rounds for meaningful statistics. 1 round warmup |
| Custom pytest hook for SLA gate | Hook `pytest_benchmark_update_machine_info` or `conftest.py` that fails if p95 > 100ms |

---

## Benchmark Configuration

### `pyproject.toml` additions

```toml
[tool.pytest.ini_options]
# ... existing config ...
markers = [
    "benchmark: marks tests as benchmark (deselect with '-m \"not benchmark\"')",
    "e2e: marks tests as end-to-end",
]
```

### `tests/e2e/conftest.py`

```python
"""Shared fixtures for E2E tests.

Provides the ``api_client`` fixture reused from integration,
plus benchmark configuration for latency measurement.

The SLA gate is implemented as a custom pytest hook that verifies
that the p95 of stock benchmarks is under 100ms.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
from httpx import ASGITransport

from src.main import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    import asyncpg


@pytest.fixture
async def api_client(
    db_pool: asyncpg.Pool, db_clean: asyncpg.Pool
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """E2E fixture: async HTTP client against the app with clean data.

    Reuses the same infrastructure as integration tests:
    testcontainers PostgreSQL, migrations, seed data.
    """
    from src.adapters.api.dependencies import get_db_pool

    app = create_app()

    async def _override_db_pool() -> asyncpg.Pool:
        return db_pool

    app.dependency_overrides[get_db_pool] = _override_db_pool

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ── SLA Gate: p95 < 100ms for stock queries ─────────────────────────────

STOCK_SLA_MS = 100.0


def pytest_benchmark_update_machine_info(config, machine_info):
    """Hook: adds benchmark environment info."""
    machine_info["testcontainers"] = True


@pytest.hookimpl(hookwrapper=True)
def pytest_benchmark_compare_stats(config, bench_id, compare, current):
    """Hook: verifies SLA after each stock benchmark."""
    yield
    # Only verify SLA on stock benchmarks
    if "stock" in bench_id and current:
        stats = current.stats
        if stats and hasattr(stats, "p95"):
            p95_ms = stats.p95 * 1000  # Convert seconds to ms
            if p95_ms > STOCK_SLA_MS:
                pytest.fail(
                    f"SLA violation: {bench_id} p95={p95_ms:.1f}ms > {STOCK_SLA_MS}ms"
                )
```

---

## E2E Test: Stock Latency

### `tests/e2e/test_stock_latency.py`

```python
"""E2E latency tests for stock queries.

Validates the core system SLA: current and historical stock queries
must respond at p95 < 100ms. Uses pytest-benchmark for statistical
measurement with multiple rounds.

The SLA is measured in-process (httpx.AsyncClient + ASGITransport),
without network overhead. In production with network, latency is
expected to remain <100ms thanks to the materialized view.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx


# ── Helpers ──────────────────────────────────────────────────────────────

async def _setup_product_with_movements(client: httpx.AsyncClient) -> int:
    """Creates category, product and movements for latency tests."""
    # Create category
    resp = await client.post("/v1/categories", json={
        "name": f"bench-cat-{id(client)}",
        "description": "Benchmark category",
    })
    cat_id = resp.json()["id"]

    # Create product
    resp = await client.post("/v1/products", json={
        "sku": f"BENCH-{id(client)}",
        "name": "Benchmark Product",
        "unit_of_measure": "unit",
        "category_id": cat_id,
        "min_stock_threshold": 10,
    })
    product_id = resp.json()["id"]

    # Create movements
    for _ in range(10):
        await client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 50,
            "reference": "bench",
        })

    return product_id


# ── SLA Tests ────────────────────────────────────────────────────────────

class TestStockLatency:
    """SLA: stock queries at p95 < 100ms."""

    @pytest.mark.benchmark(group="stock-current")
    async def test_current_stock_latency(
        self, benchmark, api_client: httpx.AsyncClient
    ) -> None:
        """SLA: GET /v1/stock/{id}/current at p95 < 100ms."""
        product_id = await _setup_product_with_movements(api_client)

        # Benchmark: measure query latency
        result = benchmark(
            lambda: asyncio.run(
                api_client.get(f"/v1/stock/{product_id}/current")
            )
        )
        assert result.status_code == 200
        data = result.json()
        assert "current_stock" in data
        assert data["current_stock"] == 500.0  # 10 × 50 IN

    @pytest.mark.benchmark(group="stock-at-date")
    async def test_stock_at_date_latency(
        self, benchmark, api_client: httpx.AsyncClient
    ) -> None:
        """SLA: GET /v1/stock/{id}/at-date?date=... at p95 < 100ms."""
        from datetime import datetime, timezone

        product_id = await _setup_product_with_movements(api_client)
        now = datetime.now(timezone.utc).isoformat()

        result = benchmark(
            lambda: asyncio.run(
                api_client.get(f"/v1/stock/{product_id}/at-date?date={now}")
            )
        )
        assert result.status_code == 200
        data = result.json()
        assert "stock" in data

    @pytest.mark.benchmark(group="stock-current")
    async def test_current_stock_no_movements_latency(
        self, benchmark, api_client: httpx.AsyncClient
    ) -> None:
        """SLA: stock for product without movements also < 100ms."""
        # Create category and product without movements
        resp = await api_client.post("/v1/categories", json={
            "name": f"empty-cat-{id(api_client)}",
        })
        cat_id = resp.json()["id"]

        resp = await api_client.post("/v1/products", json={
            "sku": f"EMPTY-{id(api_client)}",
            "name": "No Movements Product",
            "unit_of_measure": "unit",
            "category_id": cat_id,
        })
        product_id = resp.json()["id"]

        result = benchmark(
            lambda: asyncio.run(
                api_client.get(f"/v1/stock/{product_id}/current")
            )
        )
        assert result.status_code == 200
        assert result.json()["current_stock"] == 0.0
```

---

## E2E Test: Full Flows

### `tests/e2e/test_full_flows.py`

```python
"""E2E tests for complete HTTP flows.

Validates the operation sequences that a real user would execute:
1. Create category → product → movement → query stock
2. Register OUT when stock is insufficient → error
3. Query stock on multiple dates → historical consistency
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx


class TestFullInventoryFlow:
    """Complete flow: category → product → movement → stock."""

    async def test_create_and_query_stock(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Happy path: create category, product, movement, query stock."""
        # 1. Create category
        resp = await api_client.post("/v1/categories", json={
            "name": "Electronics",
            "description": "Electronic devices",
        })
        assert resp.status_code == 201
        cat_id = resp.json()["id"]

        # 2. Create product
        resp = await api_client.post("/v1/products", json={
            "sku": "ELEC-001",
            "name": "Monitor 27\"",
            "unit_of_measure": "unit",
            "category_id": cat_id,
            "min_stock_threshold": 5,
        })
        assert resp.status_code == 201
        product_id = resp.json()["id"]

        # 3. Register stock entry
        resp = await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 100,
            "reference": "PO-2026-001",
        })
        assert resp.status_code == 201
        movement_id = resp.json()["id"]
        assert movement_id > 0

        # 4. Query current stock
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.status_code == 200
        assert resp.json()["current_stock"] == 100.0

        # 5. Register exit
        resp = await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "OUT",
            "quantity": 30,
            "reference": "SO-2026-001",
        })
        assert resp.status_code == 201

        # 6. Verify updated stock
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.status_code == 200
        assert resp.json()["current_stock"] == 70.0

    async def test_insufficient_stock_flow(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Error flow: OUT with insufficient stock → 409."""
        # Setup: category + product with 10 units
        cat = await api_client.post("/v1/categories", json={"name": "Test"})
        product = await api_client.post("/v1/products", json={
            "sku": "TEST-INSUF",
            "name": "Test Product",
            "unit_of_measure": "unit",
            "category_id": cat.json()["id"],
        })
        product_id = product.json()["id"]

        await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 10,
        })

        # Attempt OUT of 20 (only 10 available)
        resp = await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "OUT",
            "quantity": 20,
        })
        assert resp.status_code == 409
        body = resp.json()
        assert "INSUFFICIENT_STOCK" in body["error"]["code"]

    async def test_historical_stock_consistency(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Historical flow: stock at different dates is consistent."""
        # Setup
        cat = await api_client.post("/v1/categories", json={"name": "Hist"})
        product = await api_client.post("/v1/products", json={
            "sku": "HIST-001",
            "name": "Historical Product",
            "unit_of_measure": "unit",
            "category_id": cat.json()["id"],
        })
        product_id = product.json()["id"]

        # Current stock = 0
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.json()["current_stock"] == 0.0

        # Register entry
        await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 50,
        })

        # Current stock now = 50
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.json()["current_stock"] == 50.0

        # Stock on past date (before the movement) = 0
        past_date = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        resp = await api_client.get(
            f"/v1/stock/{product_id}/at-date?date={past_date}"
        )
        assert resp.json()["stock"] == 0.0
```

---

## E2E Test: OpenAPI Contracts

### `tests/e2e/test_openapi_contracts.py`

```python
"""E2E tests for OpenAPI contract validation.

Verifies that JSON responses from endpoints match the Pydantic
schemas defined in src/application/dtos/.
Uses model_validate() to validate each response against its DTO.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from src.application.dtos.movement_dtos import MovementOutput, MovementListOutput
from src.application.dtos.stock_dtos import CurrentStockOutput, StockAtDateOutput
from src.application.dtos.product_dtos import ProductOutput, ProductListOutput
from src.application.dtos.category_dtos import CategoryOutput

if TYPE_CHECKING:
    import httpx


class TestOpenAPIContracts:
    """API responses must validate against their Pydantic DTOs."""

    async def test_movement_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """POST /v1/movements returns valid MovementOutput."""
        # Setup
        cat = await api_client.post("/v1/categories", json={"name": "Contract"})
        product = await api_client.post("/v1/products", json={
            "sku": "CONTRACT-001",
            "name": "Contract Product",
            "unit_of_measure": "unit",
            "category_id": cat.json()["id"],
        })
        product_id = product.json()["id"]

        resp = await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 25,
        })
        assert resp.status_code == 201
        # Validate against Pydantic model
        movement = MovementOutput.model_validate(resp.json())
        assert movement.id > 0
        assert movement.product_id == product_id
        assert movement.movement_type == "IN"
        assert movement.quantity == 25

    async def test_current_stock_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """GET /v1/stock/{id}/current returns valid CurrentStockOutput."""
        # Setup
        cat = await api_client.post("/v1/categories", json={"name": "Stock"})
        product = await api_client.post("/v1/products", json={
            "sku": "STOCK-CONTRACT",
            "name": "Stock Contract Product",
            "unit_of_measure": "unit",
            "category_id": cat.json()["id"],
        })
        product_id = product.json()["id"]

        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.status_code == 200
        stock = CurrentStockOutput.model_validate(resp.json())
        assert stock.product_id == product_id

    async def test_product_list_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """GET /v1/products returns valid ProductListOutput."""
        resp = await api_client.get("/v1/products")
        assert resp.status_code == 200
        product_list = ProductListOutput.model_validate(resp.json())
        assert isinstance(product_list.items, list)
        assert product_list.total >= 0

    async def test_category_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """POST /v1/categories returns valid CategoryOutput."""
        resp = await api_client.post("/v1/categories", json={
            "name": "Contract Category",
        })
        assert resp.status_code == 201
        category = CategoryOutput.model_validate(resp.json())
        assert category.id > 0
        assert category.name == "Contract Category"
```

---

## Files

| File | Description | Action |
|------|-------------|--------|
| `tests/e2e/conftest.py` | E2E fixtures + benchmark config + SLA gate | NEW |
| `tests/e2e/test_stock_latency.py` | SLA <100ms benchmark tests | NEW |
| `tests/e2e/test_full_flows.py` | Complete end-to-end HTTP flows | NEW |
| `tests/e2e/test_openapi_contracts.py` | Validation against Pydantic schemas | NEW |
| `pyproject.toml` | +pytest-benchmark, markers | MODIFY |
| `requirements.txt` | +pytest-benchmark | MODIFY |

---

## Acceptance Criteria

- [ ] `pytest-benchmark` added to `requirements.txt` and `pyproject.toml`
- [ ] `tests/e2e/conftest.py` with `api_client` fixture + benchmark config + SLA gate hook
- [ ] Latency tests: `/v1/stock/{id}/current` p95 < 100ms
- [ ] Latency tests: `/v1/stock/{id}/at-date` p95 < 100ms
- [ ] Latency tests: product without movements also < 100ms
- [ ] Full flow tests: category → product → movement → stock
- [ ] Full flow tests: OUT with insufficient stock → 409
- [ ] Full flow tests: historical consistency between dates
- [ ] OpenAPI contract tests: responses validate against Pydantic DTOs
- [ ] SLA gate fails if p95 > 100ms on stock benchmarks
- [ ] 0 regressions in existing tests
- [ ] `make lint` passes without errors

---

## Testing Strategy

- **Benchmark tests:** measure in-process latency with `pytest-benchmark`. Minimum 5 rounds, 1 warmup. SLA gate on p95
- **Full flow tests:** HTTP operation sequences that simulate real usage. Verify data consistency
- **OpenAPI contract tests:** validate JSON responses against Pydantic models with `model_validate()`
- **Execution:** `pytest tests/e2e/ -v` or `pytest tests/e2e/ --benchmark-only` for benchmarks only

### Benchmark Execution

```bash
# All E2E tests (includes benchmarks)
pytest tests/e2e/ -v

# Benchmarks only
pytest tests/e2e/ -v --benchmark-only

# Benchmarks with more rounds for analysis
pytest tests/e2e/ -v --benchmark-only --benchmark-min-rounds=20

# Save results for comparison
pytest tests/e2e/ -v --benchmark-only --benchmark-json=bench_results.json
```

---

## Resolved Questions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| F6-62-Q1 | Benchmark tool? | **pytest-benchmark** | In-process, no external server. Deterministic. Integrates with pytest. Locust/k6 are for external load testing |
| F6-62-Q2 | SLA percentile? | **p95 < 100ms** | Allows 5% outliers due to testcontainers overhead. max and p99 are too strict for CI with containers |
| F6-62-Q3 | Minimum rounds? | **5** (warmup=1) | Minimum meaningful statistics. 5 rounds × 2 endpoints × 2 cases = 20 total measurements in ~5s |
| F6-62-Q4 | SLA gate as pytest hook or assertion? | **Pytest hook** | Automatically fails if p95 > 100ms. No manual assertion required in each test. Cleaner |
| F6-62-Q5 | OpenAPI contracts with JSON schema or Pydantic? | **Pydantic model_validate()** | DTOs already exist. Validating against them is more direct and maintains a single source of truth |
