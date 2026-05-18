"""Integration tests for PostgresProductRepository.

Valida el repositorio de productos contra un PostgreSQL real mediante
testcontainers.

Ejemplo de ejecución::

    pytest tests/integration/repositories/test_product_repository.py -v
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.domain.entities.product import Product
from src.domain.ports.product_repository import IProductRepository
from src.domain.value_objects.sku import SKU

if TYPE_CHECKING:
    import asyncpg


_NOW = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)


# ── Helpers ──────────────────────────────────────────────────────────────


async def _get_category_id(pool: asyncpg.Pool) -> int:
    """Obtiene el ID de la categoria 'General' del seed data."""
    row = await pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    assert row is not None, "Seed category 'General' not found"
    return row["id"]


def _make_product(
    sku: str,
    name: str,
    category_id: int,
    min_stock_threshold: int = 0,
) -> Product:
    """Crea un Product sin id (antes de persistir)."""
    return Product(
        id=None,
        sku=SKU(sku),
        name=name,
        description=None,
        unit_of_measure="unit",
        category_id=category_id,
        min_stock_threshold=min_stock_threshold,
        created_at=_NOW,
    )


# ── Tests ────────────────────────────────────────────────────────────────


async def test_product_repo_implements_protocol(db_pool: asyncpg.Pool) -> None:
    """El repositorio satisface el protocolo IProductRepository."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    repo = PostgresProductRepository(db_pool)
    assert isinstance(repo, IProductRepository)


async def test_create_product_returns_entity_with_id(
    db_pool: asyncpg.Pool,
) -> None:
    """create() inserta y retorna la entidad con id asignado."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    category_id = await _get_category_id(db_pool)
    repo = PostgresProductRepository(db_pool)
    product = _make_product("TEST-001", "Test Product", category_id)

    result = await repo.create(product)

    assert result.id is not None
    assert result.sku.value == "TEST-001"
    assert result.name == "Test Product"


async def test_get_by_id_returns_product(db_pool: asyncpg.Pool) -> None:
    """get_by_id() retorna la entidad cuando existe."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    category_id = await _get_category_id(db_pool)
    repo = PostgresProductRepository(db_pool)
    created = await repo.create(_make_product("TEST-002", "Laptop", category_id))

    result = await repo.get_by_id(created.id)

    assert result is not None
    assert result.id == created.id
    assert result.name == "Laptop"


async def test_get_by_id_returns_none_when_not_found(
    db_pool: asyncpg.Pool,
) -> None:
    """get_by_id() retorna None para un id inexistente."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    repo = PostgresProductRepository(db_pool)

    result = await repo.get_by_id(99999)

    assert result is None


async def test_get_by_sku_returns_product(db_pool: asyncpg.Pool) -> None:
    """get_by_sku() retorna la entidad cuando existe."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    category_id = await _get_category_id(db_pool)
    repo = PostgresProductRepository(db_pool)
    await repo.create(_make_product("SKU-TEST", "Monitor", category_id))

    result = await repo.get_by_sku("SKU-TEST")

    assert result is not None
    assert result.sku.value == "SKU-TEST"


async def test_get_by_sku_returns_none_when_not_found(
    db_pool: asyncpg.Pool,
) -> None:
    """get_by_sku() retorna None para un SKU inexistente."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    repo = PostgresProductRepository(db_pool)

    result = await repo.get_by_sku("NONEXISTENT")

    assert result is None


async def test_list_all_with_pagination(db_pool: asyncpg.Pool) -> None:
    """list_all() soporta paginacion con limit y offset."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    category_id = await _get_category_id(db_pool)
    repo = PostgresProductRepository(db_pool)

    # Count existing products before adding
    before_count = len(await repo.list_all())

    await repo.create(_make_product("PAG-001", "Product A", category_id))
    await repo.create(_make_product("PAG-002", "Product B", category_id))
    await repo.create(_make_product("PAG-003", "Product C", category_id))

    # First page (limit 2)
    page1 = await repo.list_all(limit=2, offset=0)
    assert len(page1) == 2

    # Second page (offset 2)
    page2 = await repo.list_all(limit=2, offset=2)
    assert len(page2) >= 1

    # Total should match
    total = await repo.list_all()
    assert len(total) == before_count + 3


async def test_list_below_threshold(db_pool: asyncpg.Pool) -> None:
    """list_below_threshold() retorna productos con stock bajo el umbral."""
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    category_id = await _get_category_id(db_pool)
    repo = PostgresProductRepository(db_pool)

    # Create product with threshold of 10
    product = await repo.create(
        _make_product(
            "THRESH-001", "Low Stock Item", category_id, min_stock_threshold=10
        )
    )

    # Add only 3 units (below threshold of 10)
    await db_pool.execute(
        "INSERT INTO movements "
        "(product_id, movement_type, quantity) VALUES ($1, 'IN', 3)",
        product.id,
    )

    below = await repo.list_below_threshold(limit=100)

    # Should include our product with stock 3 < threshold 10
    ids = [p.id for p in below]
    assert product.id in ids
