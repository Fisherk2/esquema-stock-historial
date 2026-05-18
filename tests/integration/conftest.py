"""Fixtures compartidos para tests de integracion.

Proporciona el fixture ``db_pool`` que levanta un PostgreSQL real con
testcontainers, ejecuta todas las migraciones y devuelve el pool.
Reutilizable por cualquier test de integracion.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from src.infrastructure.db.migrate import run_migrations

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Fixture que crea un PostgreSQL aislado, ejecuta migraciones y limpia.

    Usa testcontainers para levantar un contenedor PostgreSQL 16, crea un
    pool de conexiones asyncpg, ejecuta todas las migraciones y devuelve
    el pool. Al finalizar el test, cierra el pool y el contenedor.

    Yields:
        asyncpg.Pool: Pool de conexiones con migraciones aplicadas.
    """
    with PostgresContainer("postgres:16-alpine") as postgres:
        dsn = postgres.get_connection_url()
        # testcontainers returns postgresql+psycopg2:// but asyncpg needs
        # postgresql://
        dsn = dsn.replace("postgresql+psycopg2://", "postgresql://")
        pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)

        try:
            await run_migrations(pool)
            yield pool
        finally:
            await pool.close()
