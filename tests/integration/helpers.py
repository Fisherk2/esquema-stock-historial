"""Helper functions para tests de integracion.

Proporciona utilidades compartidas entre archivos de test de integracion:
- Batch insert de movimientos para tests de datos masivos.
- Creacion rapida de productos y categorias para tests aislados.

Ejemplo::

    from tests.integration.helpers import (
        create_test_product,
        create_test_movement,
        insert_batch_movements,
    )

    product_id = await create_test_product(pool)
    await insert_batch_movements(pool, product_id, count=100)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg


async def create_test_category(
    pool: asyncpg.Pool,
    name: str = "TestCategory",
    description: str | None = None,
) -> int:
    """Crea una categoria de prueba y retorna su ID.

    Args:
        pool: Pool de conexiones asyncpg.
        name: Nombre de la categoria.
        description: Descripcion opcional.

    Returns:
        int: ID de la categoria creada.
    """
    row = await pool.fetchrow(
        "INSERT INTO categories (name, description) VALUES ($1, $2) RETURNING id",
        name,
        description,
    )
    assert row is not None
    return row["id"]


async def create_test_product(
    pool: asyncpg.Pool,
    sku: str = "TEST-PROD-001",
    category_id: int | None = None,
) -> int:
    """Crea un producto de prueba y retorna su ID.

    Args:
        pool: Pool de conexiones asyncpg.
        sku: SKU del producto.
        category_id: ID de la categoria. Si no se proporciona,
            usa la categoria 'General' del seed data.

    Returns:
        int: ID del producto creado.
    """
    if category_id is None:
        cat_row = await pool.fetchrow(
            "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
        )
        assert cat_row is not None, "Seed category 'General' not found"
        category_id = cat_row["id"]

    row = await pool.fetchrow(
        "INSERT INTO products (sku, name, unit_of_measure, category_id) "
        "VALUES ($1, $2, $3, $4) RETURNING id",
        sku,
        "Test Product",
        "unit",
        category_id,
    )
    assert row is not None
    return row["id"]


async def create_test_movement(
    pool: asyncpg.Pool,
    product_id: int,
    movement_type: str = "IN",
    quantity: int = 10,
) -> int:
    """Crea un movimiento de prueba y retorna su ID.

    Args:
        pool: Pool de conexiones asyncpg.
        product_id: ID del producto.
        movement_type: Tipo de movimiento (IN, OUT, ADJUSTMENT, TRANSFER).
        quantity: Cantidad del movimiento.

    Returns:
        int: ID del movimiento creado.
    """
    row = await pool.fetchrow(
        "INSERT INTO movements (product_id, movement_type, quantity, metadata) "
        "VALUES ($1, $2, $3, $4) RETURNING id",
        product_id,
        movement_type,
        quantity,
        "{}",
    )
    assert row is not None
    return row["id"]


async def insert_batch_movements(
    pool: asyncpg.Pool,
    product_id: int,
    count: int,
    movement_type: str = "IN",
    quantity: int = 10,
) -> None:
    """Inserta N movimientos en batch para tests de datos masivos.

    Usa SQL directo para eficiencia. No usa la API.

    Args:
        pool: Pool de conexiones asyncpg.
        product_id: ID del producto al que afectan los movimientos.
        count: Numero de movimientos a insertar.
        movement_type: Tipo de movimiento (IN, OUT, ADJUSTMENT, TRANSFER).
        quantity: Cantidad por movimiento.
    """
    rows = [
        (product_id, movement_type, quantity, "{}")
        for _ in range(count)
    ]
    await pool.executemany(
        """
        INSERT INTO movements (product_id, movement_type, quantity, metadata)
        VALUES ($1, $2, $3, $4)
        """,
        rows,
    )
