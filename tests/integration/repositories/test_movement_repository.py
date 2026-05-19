"""Integration tests for PostgresMovementRepository.

Valida el repositorio de movimientos contra un PostgreSQL real mediante
testcontainers.

Ejemplo de ejecución::

    pytest tests/integration/repositories/test_movement_repository.py -v
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.domain.entities.movement import Movement
from src.domain.ports.movement_repository import IMovementRepository
from src.domain.value_objects.movement_type import MovementType
from src.domain.value_objects.quantity import Quantity

if TYPE_CHECKING:
    import asyncpg


_NOW = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)


# ── Helpers ──────────────────────────────────────────────────────────────


async def _get_product_id(pool: asyncpg.Pool) -> int:
    """Obtiene el ID de un producto del seed data."""
    row = await pool.fetchrow("SELECT id FROM products LIMIT 1")
    assert row is not None, "No seed product found"
    return row["id"]


def _make_movement(
    product_id: int,
    movement_type: MovementType,
    quantity: int = 10,
    metadata: dict | None = None,
    reference: str | None = None,
) -> Movement:
    """Crea un Movement sin id (antes de persistir)."""
    return Movement(
        id=None,
        product_id=product_id,
        movement_type=movement_type,
        quantity=Quantity(quantity),
        metadata=metadata or {},
        reference=reference,
        created_at=_NOW,
    )


# ── Tests ────────────────────────────────────────────────────────────────


async def test_movement_repo_implements_protocol(db_pool: asyncpg.Pool) -> None:
    """El repositorio satisface el protocolo IMovementRepository."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    repo = PostgresMovementRepository(db_pool)
    assert isinstance(repo, IMovementRepository)


async def test_create_movement_returns_entity_with_id(
    db_pool: asyncpg.Pool,
) -> None:
    """create() inserta y retorna la entidad con id asignado."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    product_id = await _get_product_id(db_pool)
    repo = PostgresMovementRepository(db_pool)
    movement = _make_movement(
        product_id, MovementType.IN, quantity=25, reference="PO-999"
    )

    result = await repo.create(movement)

    assert result.id is not None
    assert result.product_id == product_id
    assert result.movement_type == MovementType.IN
    assert result.quantity.value == 25
    assert result.reference == "PO-999"


async def test_get_by_id_returns_movement(db_pool: asyncpg.Pool) -> None:
    """get_by_id() retorna la entidad cuando existe."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    product_id = await _get_product_id(db_pool)
    repo = PostgresMovementRepository(db_pool)
    created = await repo.create(
        _make_movement(product_id, MovementType.OUT, quantity=5)
    )

    result = await repo.get_by_id(created.id)

    assert result is not None
    assert result.id == created.id
    assert result.movement_type == MovementType.OUT


async def test_get_by_id_returns_none_when_not_found(
    db_pool: asyncpg.Pool,
) -> None:
    """get_by_id() retorna None para un id inexistente."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    repo = PostgresMovementRepository(db_pool)

    result = await repo.get_by_id(99999)

    assert result is None


async def test_list_by_product_ordered_desc(db_pool: asyncpg.Pool) -> None:
    """list_by_product() retorna movimientos ordenados por created_at DESC."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    product_id = await _get_product_id(db_pool)
    repo = PostgresMovementRepository(db_pool)

    await repo.create(_make_movement(product_id, MovementType.IN, quantity=10))
    await repo.create(_make_movement(product_id, MovementType.OUT, quantity=3))
    await repo.create(
        _make_movement(
            product_id,
            MovementType.ADJUSTMENT,
            quantity=1,
            metadata={"reason": "correction"},
        )
    )

    results = await repo.list_by_product(product_id, limit=10)

    assert len(results) >= 3
    # Verify ordering: newest first
    assert results[0].created_at >= results[1].created_at


async def test_list_by_product_with_pagination(
    db_pool: asyncpg.Pool,
) -> None:
    """list_by_product() soporta paginacion."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    product_id = await _get_product_id(db_pool)
    repo = PostgresMovementRepository(db_pool)

    # Count existing movements
    before_count = len(await repo.list_by_product(product_id, limit=1000))

    # Add 3 more
    for _ in range(3):
        await repo.create(_make_movement(product_id, MovementType.IN, quantity=1))

    # First page
    page1 = await repo.list_by_product(product_id, limit=2, offset=0)
    assert len(page1) == 2

    # Total count
    total = await repo.list_by_product(product_id, limit=1000)
    assert len(total) == before_count + 3


async def test_list_by_product_returns_empty_for_no_movements(
    db_pool: asyncpg.Pool,
) -> None:
    """list_by_product() retorna lista vacia para producto sin movimientos."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    # Get a category and create a fresh product with id high enough to have
    # no movements
    cat_row = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, category_id) "
        "VALUES ('NOMOV-001', 'No Movements', $1)",
        cat_row["id"],
    )
    prod_row = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'NOMOV-001'")

    repo = PostgresMovementRepository(db_pool)

    results = await repo.list_by_product(prod_row["id"], limit=10)

    assert results == []


async def test_count_by_product_returns_correct_count(
    db_pool: asyncpg.Pool,
) -> None:
    """count_by_product() retorna el total exacto de movimientos de un producto."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    product_id = await _get_product_id(db_pool)
    repo = PostgresMovementRepository(db_pool)

    # Count existing movements before adding
    count_before = await repo.count_by_product(product_id)

    # Add 5 new movements
    for _ in range(5):
        await repo.create(_make_movement(product_id, MovementType.IN, quantity=1))

    count_after = await repo.count_by_product(product_id)

    assert count_after == count_before + 5


async def test_count_by_product_returns_zero_for_no_movements(
    db_pool: asyncpg.Pool,
) -> None:
    """count_by_product() retorna 0 para un producto sin movimientos."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )

    # Create a fresh product with no movements
    cat_row = await db_pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    await db_pool.execute(
        "INSERT INTO products (sku, name, category_id) "
        "VALUES ('COUNT-001', 'Count Test', $1)",
        cat_row["id"],
    )
    prod_row = await db_pool.fetchrow("SELECT id FROM products WHERE sku = 'COUNT-001'")

    repo = PostgresMovementRepository(db_pool)

    count = await repo.count_by_product(prod_row["id"])

    assert count == 0
