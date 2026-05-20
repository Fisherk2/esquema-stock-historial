"""Edge case tests for PostgresUnitOfWork.

Valida rollback en segundo repositorio, conexion liberada tras excepcion,
y aislamiento entre transacciones.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import asyncpg


async def _get_category_id(pool: asyncpg.Pool) -> int:
    """Obtiene el ID de la categoria 'General' del seed data."""
    row = await pool.fetchrow(
        "SELECT id FROM categories WHERE name = 'General' LIMIT 1"
    )
    assert row is not None
    return row["id"]


async def _count_products(pool: asyncpg.Pool) -> int:
    """Cuenta productos actuales."""
    row = await pool.fetchrow("SELECT COUNT(*) as cnt FROM products")
    assert row is not None
    return row["cnt"]


async def test_uow_rollback_on_second_repo_error(
    db_pool: asyncpg.Pool,
) -> None:
    """Error en segundo repositorio dentro de UoW → rollback total."""
    from src.infrastructure.db.uow import PostgresUnitOfWork
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    initial_count = await _count_products(db_pool)
    category_id = await _get_category_id(db_pool)

    with pytest.raises(ValueError, match="abort"):
        async with PostgresUnitOfWork(db_pool) as uow:
            assert uow.connection is not None
            product_repo = PostgresProductRepository(db_pool, uow.connection)
            from src.domain.entities.product import Product
            from src.domain.value_objects.sku import SKU
            from datetime import UTC, datetime

            await product_repo.create(
                Product(
                    id=None,
                    sku=SKU("UOW-ROLLBACK-TEST"),
                    name="Should Rollback",
                    description=None,
                    unit_of_measure="unit",
                    category_id=category_id,
                    created_at=datetime.now(tz=UTC),
                )
            )
            raise ValueError("abort")

    # Nothing should be persisted
    final_count = await _count_products(db_pool)
    assert final_count == initial_count


async def test_uow_connection_released_after_exception(
    db_pool: asyncpg.Pool,
) -> None:
    """Conexion se libera al pool incluso con excepcion."""
    from src.infrastructure.db.uow import PostgresUnitOfWork

    uow = PostgresUnitOfWork(db_pool)

    # Before: connection is None
    assert uow.connection is None

    # Enter and exit with exception
    with pytest.raises(RuntimeError):
        async with uow:
            raise RuntimeError("test error")

    # After: connection should be released (None)
    assert uow.connection is None


async def test_uow_successful_commit_persists_all(
    db_pool: asyncpg.Pool,
) -> None:
    """UoW con commit exitoso persiste todos los cambios."""
    import json
    from src.infrastructure.db.uow import PostgresUnitOfWork

    product_id_row = await db_pool.fetchrow("SELECT id FROM products LIMIT 1")
    assert product_id_row is not None
    product_id = product_id_row["id"]

    async with PostgresUnitOfWork(db_pool) as uow:
        assert uow.connection is not None
        await uow.connection.execute(
            "INSERT INTO movements "
            "(product_id, movement_type, quantity, metadata) "
            "VALUES ($1, 'IN', 42, $2)",
            product_id,
            json.dumps({"uow_edge": "commit_test"}),
        )

    # Verify persisted
    row = await db_pool.fetchrow(
        "SELECT quantity FROM movements WHERE metadata->>'uow_edge' = 'commit_test'"
    )
    assert row is not None
    assert row["quantity"] == 42
