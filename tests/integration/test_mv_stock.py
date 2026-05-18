"""Integration tests for materialized view mv_stock_historical.

Valida la creacion, refresh, consistencia y fallback de la vista
materializada contra un PostgreSQL real.

Ejemplo de ejecucion::

    pytest tests/integration/test_mv_stock.py -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.infrastructure.db.refresh import refresh_stock_view

if TYPE_CHECKING:
    import asyncpg


# ── Tests ────────────────────────────────────────────────────────────────


async def test_mv_exists_after_migration(db_pool: asyncpg.Pool) -> None:
    """La vista materializada existe tras ejecutar las migraciones."""
    row = await db_pool.fetchrow(
        "SELECT matviewname FROM pg_matviews WHERE matviewname = $1",
        "mv_stock_historical",
    )
    assert row is not None, "mv_stock_historical not found"


async def test_mv_unique_index_exists(db_pool: asyncpg.Pool) -> None:
    """El indice unico existe (requerido para REFRESH CONCURRENTLY)."""
    row = await db_pool.fetchrow(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename = 'mv_stock_historical' "
        "AND indexname = 'ix_mv_stock_historical_product'"
    )
    assert row is not None, "Unique index not found"


async def test_mv_consistency_with_direct_calculation(
    db_pool: asyncpg.Pool,
) -> None:
    """get_current_stock() via MV retorna el mismo valor que calculo
    directo."""
    from src.infrastructure.repositories.stock_query_repository import (
        PostgresStockQueryRepository,
    )

    # Create a fresh product
    cat_row = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, category_id) "
        "VALUES ('MV-CONSIST-001', 'MV Consistency Test', $1)",
        cat_row["id"],
    )
    prod = await db_pool.fetchrow(
        "SELECT id FROM products WHERE sku = 'MV-CONSIST-001'"
    )
    product_id = prod["id"]

    # Insert movements: IN 100, OUT 25, TRANSFER 10 → stock = 65
    for mtype, qty in [("IN", 100), ("OUT", 25), ("TRANSFER", 10)]:
        await db_pool.execute(
            "INSERT INTO movements "
            "(product_id, movement_type, quantity) VALUES ($1, $2, $3)",
            product_id,
            mtype,
            qty,
        )

    # Refresh MV
    await refresh_stock_view(db_pool)

    # Query via repo (uses MV)
    repo = PostgresStockQueryRepository(db_pool)
    mv_stock = await repo.get_current_stock(product_id)

    # Direct calculation for comparison
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
    assert mv_stock == 65.0


async def test_refresh_stock_view_updates_data(
    db_pool: asyncpg.Pool,
) -> None:
    """refresh_stock_view() actualiza la vista con nuevos movimientos."""
    # Create a fresh product
    cat_row = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, category_id) "
        "VALUES ('MV-REFRESH-001', 'MV Refresh Test', $1)",
        cat_row["id"],
    )
    prod = await db_pool.fetchrow(
        "SELECT id FROM products WHERE sku = 'MV-REFRESH-001'"
    )
    product_id = prod["id"]

    # Add 30 units
    await db_pool.execute(
        "INSERT INTO movements "
        "(product_id, movement_type, quantity) VALUES ($1, 'IN', 30)",
        product_id,
    )

    # Refresh MV to include new product + movements
    await refresh_stock_view(db_pool)

    # After refresh: MV shows 30
    after_raw = await db_pool.fetchrow(
        "SELECT current_stock FROM mv_stock_historical WHERE product_id = $1",
        product_id,
    )
    assert after_raw is not None
    assert after_raw["current_stock"] == 30


async def test_mv_columns_expected(db_pool: asyncpg.Pool) -> None:
    """La vista tiene las columnas esperadas."""
    # Materialized views are not in information_schema; use pg_attribute
    columns = await db_pool.fetch(
        "SELECT attname FROM pg_attribute "
        "WHERE attrelid = 'mv_stock_historical'::regclass "
        "AND attnum > 0 "
        "AND NOT attisdropped "
        "ORDER BY attnum"
    )
    names = [c["attname"] for c in columns]
    expected = [
        "product_id",
        "sku",
        "product_name",
        "current_stock",
        "last_movement_at",
        "calculated_at",
    ]
    assert names == expected
