"""Tests E2E de latencia para consultas de stock.

Valida el SLA core del sistema: consultas de stock actual e historico
deben responder en p95 < 100ms. Usa medicion manual con perf_counter
dentro de tests async para evitar conflictos con el event loop.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg
    import httpx

STOCK_SLA_MS = 100.0
BENCHMARK_ITERATIONS = 20


# ── Helpers ──────────────────────────────────────────────────────────────


async def _create_product_with_stock(
    db_pool: asyncpg.Pool,
    product_sku: str,
    movement_type: str = "IN",
    quantity: int = 50,
    count: int = 10,
) -> int:
    """Crea categoria, producto y movimientos usando SQL directo."""
    cat_row = await db_pool.fetchrow(
        "INSERT INTO categories (name) VALUES ($1) RETURNING id",
        f"bench-cat-{product_sku}",
    )
    cat_id = cat_row["id"]

    prod_row = await db_pool.fetchrow(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ($1, $2, $3, $4) RETURNING id",
        product_sku,
        f"Benchmark Product {product_sku}",
        "unit",
        cat_id,
    )
    product_id = prod_row["id"]

    # Insert movements in batch
    rows = [(product_id, movement_type, quantity, "{}") for _ in range(count)]
    await db_pool.executemany(
        "INSERT INTO movements (product_id, movement_type, quantity, metadata) "
        "VALUES ($1, $2, $3, $4)",
        rows,
    )

    # Refresh MV
    from src.infrastructure.db.refresh import refresh_stock_view

    await refresh_stock_view(db_pool)

    return product_id


async def _create_product_without_stock(db_pool: asyncpg.Pool, product_sku: str) -> int:
    """Crea categoria y producto sin movimientos."""
    cat_row = await db_pool.fetchrow(
        "INSERT INTO categories (name) VALUES ($1) RETURNING id",
        f"bench-nostock-{product_sku}",
    )
    prod_row = await db_pool.fetchrow(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ($1, $2, $3, $4) RETURNING id",
        product_sku,
        "No Movements Product",
        "unit",
        cat_row["id"],
    )
    return prod_row["id"]


async def _measure_stock_latency(
    api_client: httpx.AsyncClient,
    product_id: int,
    endpoint: str,
    iterations: int = BENCHMARK_ITERATIONS,
) -> list[float]:
    """Mide latencia de endpoint de stock N veces. Retorna lista en ms."""
    latencies = []
    for _ in range(iterations):
        start = time.perf_counter()
        resp = await api_client.get(f"/v1/stock/{product_id}/{endpoint}")
        elapsed_ms = (time.perf_counter() - start) * 1000
        latencies.append(elapsed_ms)
        assert resp.status_code == 200, f"Request failed: {resp.json()}"
    return latencies


# ── SLA Tests ────────────────────────────────────────────────────────────


class TestStockLatency:
    """SLA: consultas de stock en p95 < 100ms."""

    async def test_current_stock_latency(
        self, api_client: httpx.AsyncClient, db_pool: asyncpg.Pool
    ) -> None:
        """SLA: GET /v1/stock/{id}/current en p95 < 100ms."""
        product_id = await _create_product_with_stock(db_pool, "LAT-CURRENT-001")

        latencies = await _measure_stock_latency(api_client, product_id, "current")

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 < STOCK_SLA_MS, (
            f"SLA violation: p95={p95:.1f}ms > {STOCK_SLA_MS}ms. "
            f"All latencies: {latencies}"
        )

        # Verify correctness
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.json()["current_stock"] == 500.0  # 10 x 50 IN

    async def test_stock_at_date_latency(
        self, api_client: httpx.AsyncClient, db_pool: asyncpg.Pool
    ) -> None:
        """SLA: GET /v1/stock/{id}/at-date en p95 < 100ms."""
        product_id = await _create_product_with_stock(db_pool, "LAT-DATE-001")
        now = datetime.now(tz=UTC).isoformat()

        latencies = []
        for _ in range(BENCHMARK_ITERATIONS):
            start = time.perf_counter()
            resp = await api_client.get(
                f"/v1/stock/{product_id}/at-date",
                params={"date": now},
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            assert resp.status_code == 200

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 < STOCK_SLA_MS, (
            f"SLA violation: p95={p95:.1f}ms > {STOCK_SLA_MS}ms. "
            f"All latencies: {latencies}"
        )

        # Verify correctness
        resp = await api_client.get(
            f"/v1/stock/{product_id}/at-date",
            params={"date": now},
        )
        assert "stock" in resp.json()

    async def test_current_stock_no_movements_latency(
        self, api_client: httpx.AsyncClient, db_pool: asyncpg.Pool
    ) -> None:
        """SLA: stock de producto sin movimientos tambien < 100ms."""
        product_id = await _create_product_without_stock(db_pool, "LAT-EMPTY-001")

        latencies = await _measure_stock_latency(api_client, product_id, "current")

        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        assert p95 < STOCK_SLA_MS, (
            f"SLA violation: p95={p95:.1f}ms > {STOCK_SLA_MS}ms. "
            f"All latencies: {latencies}"
        )

        # Verify correctness
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.json()["current_stock"] == 0.0
