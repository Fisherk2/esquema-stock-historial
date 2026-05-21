"""Fixtures compartidas para la suite de tests.

Proporciona fixtures reutilizables entre tests unitarios, de integración,
E2E y seguridad. Cada fixture sigue el principio SRP: una responsabilidad
por fixture.

Fixtures disponibles:
- ``client``: TestClient síncrono para tests unitarios de la API.
- ``db_pool``: fixture session-scoped con 1 contenedor PostgreSQL.
- ``db_clean``: fixture function-scoped con datos limpios por test.

Ejemplo de uso::

    def test_something(client: TestClient) -> None:
        response = client.get("/v1/health")
        assert response.status_code == 200

    async def test_create_category(db_clean: asyncpg.Pool) -> None:
        ...
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import asyncpg
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from src.core.config import Settings
from src.infrastructure.db.migrate import run_migrations
from src.infrastructure.db.refresh import refresh_stock_view
from src.infrastructure.db.seed import run_seed
from src.main import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

# ── Fixture autouse: DATABASE_URL por defecto para tests ────────────────


@pytest.fixture(autouse=True)
def _default_database_url_for_tests(monkeypatch):
    """Asegura DATABASE_URL valida en todos los tests.

    Desde v1.0.0 Settings requiere DATABASE_URL (no tiene default).
    Este fixture autouse provee un DSN de test para que los tests que
    instancian Settings() no fallen por validacion.
    """
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/stock_historial_test",
    )


# ── Fixtures de base de datos (session + function scoped) ────────────────

_TRUNCATE_SQL = """
    TRUNCATE TABLE movements, products, categories CASCADE
"""

_RESET_SEQUENCES_SQL = """
    ALTER SEQUENCE movements_id_seq RESTART WITH 1;
    ALTER SEQUENCE products_id_seq RESTART WITH 1;
    ALTER SEQUENCE categories_id_seq RESTART WITH 1;
"""


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Fixture session-scoped: 1 contenedor PostgreSQL para toda la sesion.

    Levanta un contenedor PostgreSQL 16 con testcontainers, crea un pool
    de conexiones asyncpg, ejecuta migraciones, seed data y refresca la
    vista materializada. El contenedor se mantiene vivo durante toda la
    sesion de tests y se destruye al final.

    Yields:
        asyncpg.Pool: Pool de conexiones con migraciones + seed aplicados.
    """
    with PostgresContainer("postgres:16-alpine") as postgres:
        dsn = postgres.get_connection_url()
        dsn = dsn.replace("postgresql+psycopg2://", "postgresql://")
        settings = Settings(database_url=dsn)
        pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
        )

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


async def _reset_test_data(pool: asyncpg.Pool) -> None:
    """Trunca datos de prueba y re-ejecuta seed para estado limpio."""
    await pool.execute(_TRUNCATE_SQL)
    await pool.execute(_RESET_SEQUENCES_SQL)
    await run_seed(pool)
    await refresh_stock_view(pool)


@pytest_asyncio.fixture(scope="function")
async def db_clean(db_pool: asyncpg.Pool) -> AsyncGenerator[asyncpg.Pool, None]:
    """Fixture function-scoped: datos limpios antes de cada test.

    Ejecuta TRUNCATE CASCADE + re-seed + refresh MV usando el contenedor
    compartido de ``db_pool``.

    Args:
        db_pool: Pool session-scoped del contenedor compartido.

    Yields:
        asyncpg.Pool: Pool de conexiones con datos reiniciados.
    """
    await _reset_test_data(db_pool)
    yield db_pool


# ── Cliente HTTP síncrono (tests unitarios) ──────────────────────────────


@pytest.fixture
def client() -> TestClient:
    """Crea un cliente de test para la aplicación FastAPI.

    Construye una instancia fresca de la app en cada test para garantizar
    aislamiento entre tests.

    Returns:
        TestClient: Cliente HTTP síncrono para hacer requests a la app.

    Ejemplo::

        def test_health(client: TestClient) -> None:
            resp = client.get("/v1/health")
            assert resp.status_code == 200
    """
    app = create_app()
    return TestClient(app)
