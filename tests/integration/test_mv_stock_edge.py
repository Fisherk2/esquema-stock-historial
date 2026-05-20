"""Edge case tests for materialized view mv_stock_historical.

Valida la vista con datos masivos, consistencia MV vs calculo directo,
refresh con batches grandes, y multiples productos.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.infrastructure.db.refresh import refresh_stock_view

if TYPE_CHECKING:
    import asyncpg


async def test_mv_consistency_with_100_movements(db_pool: asyncpg.Pool) -> None:
    """ConsistenciaMV vs calculo directo con 100 movimientos."""
    from tests.integration.helpers import insert_batch_movements

    # Create a fresh product
    cat_row = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, category_id) "
        "VALUES ('MV-100-001', 'MV 100 Movements', $1)",
        cat_row["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'MV-100-001'")
    product_id = prod["id"]

    # Insert 100 movements of 10 units each → expected stock = 1000
    await insert_batch_movements(db_pool, product_id, count=100, quantity=10)

    # Refresh MV
    await refresh_stock_view(db_pool)

    # MV value
    mv_stock_raw = await db_pool.fetchrow(
        "SELECT current_stock FROM mv_stock_historical WHERE product_id = $1",
        product_id,
    )
    assert mv_stock_raw is not None
    mv_stock = float(mv_stock_raw["current_stock"])

    # Direct calculation
    direct_stock_raw = await db_pool.fetchrow(
        "SELECT COALESCE("
        "  SUM(CASE movement_type "
        "    WHEN 'IN' THEN quantity "
        "    WHEN 'OUT' THEN -quantity "
        "    WHEN 'ADJUSTMENT' THEN quantity "
        "    WHEN 'TRANSFER' THEN -quantity "
        "    ELSE 0 END), 0) AS stock "
        "FROM movements WHERE product_id = $1",
        product_id,
    )
    direct_stock = float(direct_stock_raw["stock"])

    assert mv_stock == direct_stock
    assert mv_stock == 1000.0


async def test_mv_stock_multiple_products(db_pool: asyncpg.Pool) -> None:
    """MV calcula stock correcto para 10 productos x 10 movimientos cada
    uno."""
    from tests.integration.helpers import insert_batch_movements

    cat_row = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )

    for i in range(10):
        await db_pool.execute(
            "INSERT INTO products (sku, name, category_id) "
            "VALUES ($1, $2, $3)",
            f"MV-MULTI-{i:02d}",
            f"Multi Product {i}",
            cat_row["id"],
        )

    prod_rows = await db_pool.fetch(
        "SELECT id FROM products WHERE sku LIKE 'MV-MULTI-%' ORDER BY id"
    )

    # Insert 10 movements per product
    for prod in prod_rows:
        await insert_batch_movements(db_pool, prod["id"], count=10, quantity=7)

    # Refresh MV
    await refresh_stock_view(db_pool)

    # Verify each product
    for prod in prod_rows:
        mv_stock_raw = await db_pool.fetchrow(
            "SELECT current_stock FROM mv_stock_historical WHERE product_id = $1",
            prod["id"],
        )
        assert mv_stock_raw is not None
        assert float(mv_stock_raw["current_stock"]) == 70.0  # 10 * 7


async def _get_product_id(pool: asyncpg.Pool) -> int:
    """Convenience: get first product id."""
    row = await pool.fetchrow("SELECT id FROM products LIMIT 1")
    assert row is not None
    return row["id"]
