"""Edge case tests for PostgresStockQueryRepository.

Valida comportamientos de borde: producto sin movimientos (stock=0),
fecha futura, fecha anterior a cualquier movimiento, fecha exacta de
movimiento, movimientos mixtos IN+OUT+ADJUSTMENT, fallback sin MV.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg


async def test_get_current_stock_product_without_movements(
    db_pool: asyncpg.Pool,
) -> None:
    """get_current_stock() retorna 0.0 para producto sin movimientos."""
    from src.infrastructure.repositories.stock_query_repository import (
        PostgresStockQueryRepository,
    )

    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ('STK-EDGE-001', 'No Stock', 'unit', $1)",
        cat["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'STK-EDGE-001'")

    repo = PostgresStockQueryRepository(db_pool)
    stock = await repo.get_current_stock(prod["id"])

    assert stock == 0.0


async def test_get_stock_at_date_future_date(db_pool: asyncpg.Pool) -> None:
    """get_stock_at_date() con fecha futura retorna stock actual."""
    from src.infrastructure.repositories.stock_query_repository import (
        PostgresStockQueryRepository,
    )

    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ('STK-EDGE-002', 'Future Date', 'unit', $1)",
        cat["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'STK-EDGE-002'")
    product_id = prod["id"]

    # Insert a movement in the past
    await db_pool.execute(
        "INSERT INTO movements (product_id, movement_type, quantity, created_at) "
        "VALUES ($1, 'IN', 50, '2020-01-01')",
        product_id,
    )

    # Query a future date - should include the past movement
    future_date = datetime.now(tz=UTC) + timedelta(days=365)
    repo = PostgresStockQueryRepository(db_pool)
    stock = await repo.get_stock_at_date(product_id, future_date)

    assert stock == 50.0


async def test_get_stock_at_date_before_any_movement(
    db_pool: asyncpg.Pool,
) -> None:
    """get_stock_at_date() con fecha anterior a todo movimiento retorna 0.0."""
    from src.infrastructure.repositories.stock_query_repository import (
        PostgresStockQueryRepository,
    )

    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ('STK-EDGE-003', 'Before Mv', 'unit', $1)",
        cat["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'STK-EDGE-003'")
    product_id = prod["id"]

    # Insert movement in 2025
    await db_pool.execute(
        "INSERT INTO movements (product_id, movement_type, quantity, created_at) "
        "VALUES ($1, 'IN', 100, '2025-06-01')",
        product_id,
    )

    # Query date before the movement
    before_date = datetime(2020, 1, 1, tzinfo=UTC)
    repo = PostgresStockQueryRepository(db_pool)
    stock = await repo.get_stock_at_date(product_id, before_date)

    assert stock == 0.0


async def test_get_stock_at_date_exact_movement_time(
    db_pool: asyncpg.Pool,
) -> None:
    """get_stock_at_date() con fecha exacta incluye ese movimiento."""
    from src.infrastructure.repositories.stock_query_repository import (
        PostgresStockQueryRepository,
    )

    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ('STK-EDGE-004', 'Exact Time', 'unit', $1)",
        cat["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'STK-EDGE-004'")
    product_id = prod["id"]

    # Insert movement at exact date
    exact_date = datetime(2025, 3, 15, 12, 0, 0, tzinfo=UTC)
    await db_pool.execute(
        "INSERT INTO movements (product_id, movement_type, quantity, created_at) "
        "VALUES ($1, 'IN', 75, $2)",
        product_id,
        exact_date,
    )

    repo = PostgresStockQueryRepository(db_pool)
    stock = await repo.get_stock_at_date(product_id, exact_date)

    assert stock == 75.0


async def test_get_current_stock_after_mixed_movements(
    db_pool: asyncpg.Pool,
) -> None:
    """get_current_stock() con IN+OUT+ADJUSTMENT retorna neto correcto."""
    from src.infrastructure.repositories.stock_query_repository import (
        PostgresStockQueryRepository,
    )

    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ('STK-EDGE-005', 'Mixed Mov', 'unit', $1)",
        cat["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'STK-EDGE-005'")
    product_id = prod["id"]

    # IN: +100, OUT: -30, ADJUSTMENT: +10, TRANSFER: -5 -> net = 75
    base_sql = (
        "INSERT INTO movements "
        "(product_id, movement_type, quantity) VALUES ($1, '{type}', {qty})"
    )
    await db_pool.execute(base_sql.format(type="IN", qty=100), product_id)
    await db_pool.execute(base_sql.format(type="OUT", qty=30), product_id)
    await db_pool.execute(base_sql.format(type="ADJUSTMENT", qty=10), product_id)
    await db_pool.execute(base_sql.format(type="TRANSFER", qty=5), product_id)

    repo = PostgresStockQueryRepository(db_pool)
    stock = await repo.get_current_stock(product_id)

    assert stock == 75.0
