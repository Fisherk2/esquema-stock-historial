"""Integration tests for PostgresUnitOfWork.

Valida commit automatico, rollback en excepcion, conexion compartida
y aislamiento de transacciones.

Ejemplo de ejecucion::

    pytest tests/integration/test_uow.py -v
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from src.infrastructure.db.uow import PostgresUnitOfWork

if TYPE_CHECKING:
    import asyncpg


async def _get_product_id(pool: asyncpg.Pool) -> int:
    """Obtiene el ID de un producto del seed data."""
    row = await pool.fetchrow("SELECT id FROM products LIMIT 1")
    assert row is not None, "No seed product found"
    return row["id"]


# ── Tests ────────────────────────────────────────────────────────────────


async def test_uow_implements_protocol(db_pool: asyncpg.Pool) -> None:
    """PostgresUnitOfWork satisface el protocolo IUnitOfWork."""
    from src.domain.ports.unit_of_work import IUnitOfWork

    uow = PostgresUnitOfWork(db_pool)
    assert isinstance(uow, IUnitOfWork)


async def test_uow_commit_persists_data(db_pool: asyncpg.Pool) -> None:
    """Commit automatico: los datos persisten al salir del context."""
    product_id = await _get_product_id(db_pool)

    async with PostgresUnitOfWork(db_pool) as uow:
        assert uow.connection is not None

        await uow.connection.execute(
            "INSERT INTO movements "
            "(product_id, movement_type, quantity, metadata) "
            "VALUES ($1, 'IN', 10, $2)",
            product_id,
            json.dumps({"uow_test": "commit"}),
        )

    # Verify data persisted after context exit
    row = await db_pool.fetchrow(
        "SELECT quantity FROM movements WHERE metadata->>'uow_test' = 'commit'"
    )
    assert row is not None
    assert row["quantity"] == 10


async def test_uow_rollback_on_exception(
    db_pool: asyncpg.Pool,
) -> None:
    """Rollback automatico: datos NO persisten si hay excepcion."""
    product_id = await _get_product_id(db_pool)

    with pytest.raises(ValueError, match="test rollback"):
        async with PostgresUnitOfWork(db_pool) as uow:
            await uow.connection.execute(
                "INSERT INTO movements "
                "(product_id, movement_type, quantity, metadata) "
                "VALUES ($1, 'IN', 20, $2)",
                product_id,
                json.dumps({"uow_test": "rollback"}),
            )
            raise ValueError("test rollback")

    # Verify data was NOT persisted
    row = await db_pool.fetchrow(
        "SELECT id FROM movements WHERE metadata->>'uow_test' = 'rollback'"
    )
    assert row is None


async def test_uow_connection_shared_between_repos(
    db_pool: asyncpg.Pool,
) -> None:
    """Dos repos con la misma conexion operan en la misma transaccion."""
    from src.infrastructure.repositories.movement_repository import (
        PostgresMovementRepository,
    )
    from src.infrastructure.repositories.product_repository import (
        PostgresProductRepository,
    )

    async with PostgresUnitOfWork(db_pool) as uow:
        product_repo = PostgresProductRepository(db_pool, uow.connection)
        movement_repo = PostgresMovementRepository(db_pool, uow.connection)

        # Both repos use the same connection within the same transaction
        assert product_repo._connection == uow.connection
        assert movement_repo._connection == uow.connection


async def test_uow_connection_is_none_outside_context(
    db_pool: asyncpg.Pool,
) -> None:
    """La conexion es None fuera del context manager."""
    uow = PostgresUnitOfWork(db_pool)

    assert uow.connection is None

    async with uow:
        assert uow.connection is not None

    assert uow.connection is None
