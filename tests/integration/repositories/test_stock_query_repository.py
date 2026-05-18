"""Integration tests for PostgresStockQueryRepository.

Valida el repositorio de consultas de stock contra un PostgreSQL real.
Usa calculo directo (SUM/CASE) contra la tabla movements.

Ejemplo de ejecucion::

    pytest tests/integration/repositories/test_stock_query_repository.py -v
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg


async def _get_product_id(pool: asyncpg.Pool) -> int:
    """Obtiene el ID de un producto del seed data."""
    row = await pool.fetchrow("SELECT id FROM products LIMIT 1")
    assert row is not None, "No seed product found"
    return row["id"]


# ── Tests ────────────────────────────────────────────────────────────────


async def test_stock_query_repo_implements_protocol(db_pool: asyncpg.Pool) -> None:
    """El repositorio satisface el protocolo IStockQueryRepository."""
    from src.infrastructure.repositories.stock_query_repository import (
        PostgresStockQueryRepository,
    )

    repo = PostgresStockQueryRepository(db_pool)
    from src.domain.ports.stock_query_repository import IStockQueryRepository

    assert isinstance(repo, IStockQueryRepository)


async def test_get_current_stock_zero_for_no_movements(
    db_pool: asyncpg.Pool,
) -> None:
    """get_current_stock() retorna 0.0 para producto sin movimientos."""
    from src.infrastructure.repositories.stock_query_repository import (
        PostgresStockQueryRepository,
    )

    # Create a fresh product with no movements
    cat_row = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, category_id) "
        "VALUES ('NOSTOCK-001', 'No Stock', $1)",
        cat_row["id"],
    )
    prod_row = await db_pool.fetchrow(
        "SELECT id FROM products WHERE sku = 'NOSTOCK-001'"
    )

    repo = PostgresStockQueryRepository(db_pool)

    result = await repo.get_current_stock(prod_row["id"])

    assert result == 0.0
    assert isinstance(result, float)


async def test_get_current_stock_with_movements(db_pool: asyncpg.Pool) -> None:
    """get_current_stock() calcula el stock correctamente."""
    from src.infrastructure.db.refresh import refresh_stock_view
    from src.infrastructure.repositories.stock_query_repository import (
        PostgresStockQueryRepository,
    )

    # Create a fresh product with no movements
    cat_row = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, category_id) "
        "VALUES ('STOCK-TEST-001', 'Stock Test', $1)",
        cat_row["id"],
    )
    prod_row = await db_pool.fetchrow(
        "SELECT id FROM products WHERE sku = 'STOCK-TEST-001'"
    )
    product_id = prod_row["id"]

    repo = PostgresStockQueryRepository(db_pool)

    # IN: +50, OUT: -10, ADJUSTMENT: +5 → stock = 45
    await db_pool.execute(
        "INSERT INTO movements (product_id, movement_type, quantity) "
        "VALUES ($1, 'IN', 50)",
        product_id,
    )
    await db_pool.execute(
        "INSERT INTO movements (product_id, movement_type, quantity) "
        "VALUES ($1, 'OUT', 10)",
        product_id,
    )
    await db_pool.execute(
        "INSERT INTO movements (product_id, movement_type, quantity) "
        "VALUES ($1, 'ADJUSTMENT', 5)",
        product_id,
    )

    # Refresh MV so it includes the new movements
    await refresh_stock_view(db_pool)

    result = await repo.get_current_stock(product_id)

    assert result == 45.0


async def test_get_stock_at_date(db_pool: asyncpg.Pool) -> None:
    """get_stock_at_date() calcula el stock hasta una fecha dada."""
    from src.infrastructure.repositories.stock_query_repository import (
        PostgresStockQueryRepository,
    )

    product_id = await _get_product_id(db_pool)
    repo = PostgresStockQueryRepository(db_pool)

    # Insert movements with specific dates
    await db_pool.execute(
        "INSERT INTO movements (product_id, movement_type, quantity, created_at) "
        "VALUES ($1, 'IN', 100, '2024-01-01')",
        product_id,
    )
    await db_pool.execute(
        "INSERT INTO movements (product_id, movement_type, quantity, created_at) "
        "VALUES ($1, 'OUT', 30, '2024-06-01')",
        product_id,
    )
    await db_pool.execute(
        "INSERT INTO movements (product_id, movement_type, quantity, created_at) "
        "VALUES ($1, 'OUT', 20, '2025-01-01')",
        product_id,
    )

    # Stock at mid-2024: only the IN (+100) and first OUT (-30) = 70
    mid_2024 = datetime(2024, 12, 31, tzinfo=UTC)
    result = await repo.get_stock_at_date(product_id, mid_2024)

    assert result == 70.0
