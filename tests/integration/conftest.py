"""Fixtures compartidos para tests de integracion.

Proporciona dos fixtures de base de datos:

- ``db_pool``: fixture con scope ``session`` — levanta **un solo**
  contenedor PostgreSQL con testcontainers al inicio de la sesion de
  tests, ejecuta migraciones + seed data, y lo destruye al final.
  Reutilizable por cualquier test de integracion que no necesite datos
  limpios (p.ej. tests de esquema, triggers, indices).

- ``db_clean``: fixture con scope ``function`` — ejecuta TRUNCATE CASCADE
  + re-seed antes de cada test, garantizando aislamiento de datos sin
  recrear el contenedor. Ideal para tests de repositorios y API que
  insertan/consultan datos.

El ahorro es significativo: de ~88 contenedores por sesion (1 por test)
a **1 solo contenedor**, reduciendo el tiempo de tests de integracion de
~20 minutos a ~3 minutos.

Ejemplo de uso::

    # Tests que solo verifican estructura (no necesitan datos limpios)
    async def test_table_exists(db_pool: asyncpg.Pool) -> None:
        ...

    # Tests que insertan/consultan datos (necesitan estado limpio)
    async def test_create_category(db_clean: asyncpg.Pool) -> None:
        ...
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import asyncpg
import pytest_asyncio
from testcontainers.postgres import PostgresContainer

from src.infrastructure.db.migrate import run_migrations
from src.infrastructure.db.refresh import refresh_stock_view
from src.infrastructure.db.seed import run_seed

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

# ── SQL helpers ─────────────────────────────────────────────────────────

_TRUNCATE_SQL = """
    TRUNCATE TABLE movements, products, categories CASCADE
"""

_RESET_SEQUENCES_SQL = """
    ALTER SEQUENCE movements_id_seq RESTART WITH 1;
    ALTER SEQUENCE products_id_seq RESTART WITH 1;
    ALTER SEQUENCE categories_id_seq RESTART WITH 1;
"""

# ── Session-scoped: container + pool (se crea 1 vez) ──────────────────────


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Fixture session-scoped: 1 contenedor PostgreSQL para toda la sesion.

    Levanta un contenedor PostgreSQL 16 con testcontainers, crea un pool
    de conexiones asyncpg, ejecuta todas las migraciones (001-008),
    inserta seed data y refresca la vista materializada. El contenedor
    se mantiene vivo durante toda la sesion de tests y se destruye al final.

    Yields:
        asyncpg.Pool: Pool de conexiones con migraciones + seed aplicados.
    """
    with PostgresContainer("postgres:16-alpine") as postgres:
        dsn = postgres.get_connection_url()
        dsn = dsn.replace("postgresql+psycopg2://", "postgresql://")
        pool = await asyncpg.create_pool(dsn=dsn, min_size=2, max_size=10)

        try:
            logger.info("Applying migrations (session setup)...")
            await run_migrations(pool)

            logger.info("Inserting seed data (session setup)...")
            await run_seed(pool)

            logger.info("Refreshing materialized view (session setup)...")
            await refresh_stock_view(pool)

            logger.info("Test database ready (1 container, session-scoped)")
            yield pool
        finally:
            await pool.close()


# ── Function-scoped: clean data before each test ──────────────────────────


async def _reset_test_data(pool: asyncpg.Pool) -> None:
    """Trunca datos de prueba y re-ejecuta seed para estado limpio.

    Ejecuta TRUNCATE CASCADE en las tablas de datos (movements, products,
    categories), reinicia las secuencias de IDs, re-inserta seed data y
    refresca la vista materializada.

    Args:
        pool: Pool de conexiones asyncpg con migraciones aplicadas.
    """
    await pool.execute(_TRUNCATE_SQL)
    await pool.execute(_RESET_SEQUENCES_SQL)
    await run_seed(pool)
    await refresh_stock_view(pool)


@pytest_asyncio.fixture(scope="function")
async def db_clean(db_pool: asyncpg.Pool) -> AsyncGenerator[asyncpg.Pool, None]:
    """Fixture function-scoped: datos limpios antes de cada test.

    Ejecuta TRUNCATE CASCADE + re-seed + refresh MV usando el contenedor
    compartido de ``db_pool``. Garantiza que cada test comience con el
    estado base del seed data, sin recrear el contenedor.

    Args:
        db_pool: Pool session-scoped del contenedor compartido.

    Yields:
        asyncpg.Pool: Pool de conexiones con datos reiniciados.
    """
    await _reset_test_data(db_pool)
    yield db_pool
