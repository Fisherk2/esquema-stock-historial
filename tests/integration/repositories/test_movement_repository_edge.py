"""Edge case tests for PostgresMovementRepository.

Valida comportamientos de borde: producto sin movimientos, paginacion
con offset que excede el total, limit=0, count=0.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg


async def test_create_movement_returns_id(db_pool: asyncpg.Pool) -> None:
    """create() inserta y retorna un ID auto-generado > 0."""
    from src.domain.entities.movement import Movement
    from src.domain.value_objects.movement_type import MovementType
    from src.domain.value_objects.quantity import Quantity
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ('MVT-EDGE-001', 'Edge Test', 'unit', $1)",
        cat["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'MVT-EDGE-001'")

    repo = PostgresMovementRepository(db_pool)
    movement = Movement(
        id=None,
        product_id=prod["id"],
        movement_type=MovementType.IN,
        quantity=Quantity(10),
        metadata={},
        reference=None,
    )
    result = await repo.create(movement)

    assert result.id is not None
    assert result.id > 0
    assert result.product_id == prod["id"]


async def test_get_by_id_not_found(db_pool: asyncpg.Pool) -> None:
    """get_by_id(99999) retorna None para movimiento inexistente."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    repo = PostgresMovementRepository(db_pool)
    result = await repo.get_by_id(99999)

    assert result is None


async def test_list_by_product_empty(db_pool: asyncpg.Pool) -> None:
    """list_by_product() retorna lista vacia para producto sin movimientos."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ('MVT-EMPTY-001', 'No Movements', 'unit', $1)",
        cat["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'MVT-EMPTY-001'")

    repo = PostgresMovementRepository(db_pool)
    results = await repo.list_by_product(prod["id"], limit=10)

    assert results == []


async def test_list_by_product_pagination_offset_exceeds(
    db_pool: asyncpg.Pool,
) -> None:
    """list_by_product() con offset > total retorna lista vacia."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ('MVT-PAG-001', 'Pag Test', 'unit', $1)",
        cat["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'MVT-PAG-001'")
    product_id = prod["id"]

    # Insert 2 movements
    insert_sql = (
        "INSERT INTO movements "
        "(product_id, movement_type, quantity) VALUES ($1, 'IN', 10)"
    )
    await db_pool.execute(insert_sql, product_id)
    await db_pool.execute(
        "INSERT INTO movements "
        "(product_id, movement_type, quantity) VALUES ($1, 'IN', 5)",
        product_id,
    )

    repo = PostgresMovementRepository(db_pool)
    results = await repo.list_by_product(product_id, limit=10, offset=999)

    assert results == []


async def test_list_by_product_pagination_limit_zero(
    db_pool: asyncpg.Pool,
) -> None:
    """list_by_product() con limit=0 retorna lista vacia."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ('MVT-LIM0-001', 'Limit Zero', 'unit', $1)",
        cat["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'MVT-LIM0-001'")

    repo = PostgresMovementRepository(db_pool)
    results = await repo.list_by_product(prod["id"], limit=0)

    assert results == []


async def test_count_by_product_no_movements(db_pool: asyncpg.Pool) -> None:
    """count_by_product() retorna 0 para producto sin movimientos."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    cat = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ('MVT-CNT-001', 'Count Zero', 'unit', $1)",
        cat["id"],
    )
    prod = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'MVT-CNT-001'")

    repo = PostgresMovementRepository(db_pool)
    count = await repo.count_by_product(prod["id"])

    assert count == 0
