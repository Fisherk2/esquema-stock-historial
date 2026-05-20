"""Edge case tests for PostgresProductRepository.

Valida comportamientos de borde: SKU inexistente, ID inexistente,
paginacion con offset > total, count=0, lista below threshold vacia.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg


async def test_get_by_sku_not_found(db_pool: asyncpg.Pool) -> None:
    """get_by_sku() retorna None para SKU inexistente."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    repo = PostgresProductRepository(db_pool)
    result = await repo.get_by_sku("NONEXISTENT-SKU-XYZ")

    assert result is None


async def test_get_by_id_not_found(db_pool: asyncpg.Pool) -> None:
    """get_by_id() retorna None para producto inexistente."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    repo = PostgresProductRepository(db_pool)
    result = await repo.get_by_id(99999)

    assert result is None


async def test_list_below_threshold_none(db_pool: asyncpg.Pool) -> None:
    """list_below_threshold() retorna lista vacia si todos superan umbral."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    # Create a product with threshold 0 and give it 100 units
    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, unit_of_measure, category_id, min_stock_threshold) "
        "VALUES ('THRESH-NONE', 'No Threshold', 'unit', $1, 0)",
        cat["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'THRESH-NONE'")
    await db_pool.execute(
        "INSERT INTO movements (product_id, movement_type, quantity) "
        "VALUES ($1, 'IN', 100)",
        prod["id"],
    )

    repo = PostgresProductRepository(db_pool)
    below = await repo.list_below_threshold(limit=100)

    # Product with threshold 0 and stock 100 should not be below threshold
    ids = [p.id for p in below]
    assert prod["id"] not in ids


async def test_list_products_pagination_offset_exceeds(
    db_pool: asyncpg.Pool,
) -> None:
    """list_all() con offset > total retorna lista vacia."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    repo = PostgresProductRepository(db_pool)
    results = await repo.list_all(limit=10, offset=99999)

    assert results == []


async def test_count_all_returns_positive(db_pool: asyncpg.Pool) -> None:
    """count_all() retorna total >= seed data count."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    repo = PostgresProductRepository(db_pool)
    count = await repo.count_all()

    assert count >= 3  # Seed data has at least 3 products
