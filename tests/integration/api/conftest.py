"""Fixtures para tests de integracion de la API.

Proporciona el fixture ``api_client`` que levanta la aplicacion FastAPI
con el pool de testcontainers PostgreSQL, permitiendo tests HTTP reales
contra endpoints completos con base de datos real.

Se usa ``httpx.AsyncClient`` con ``ASGITransport`` para evitar conflictos
de event loop entre TestClient (que corre en un thread) y asyncpg pool
(que corre en el event loop principal del test).

El fixture ``api_client`` depende de ``db_clean`` para garantizar datos
limpios antes de cada test, mientras usa ``db_pool`` (session-scoped)
para el override de la dependencia ``get_db_pool``.

Ejemplo de uso::

    async def test_categories(api_client: httpx.AsyncClient) -> None:
        response = await api_client.get("/v1/categories")
        assert response.status_code == 200
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
from httpx import ASGITransport

from src.main import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    import asyncpg


@pytest.fixture
async def api_client(
    db_pool: asyncpg.Pool, db_clean: asyncpg.Pool
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Fixture que crea un cliente HTTP async contra la app con datos limpios.

    Construye una instancia fresca de la aplicacion FastAPI, sobrescribe
    la dependencia ``get_db_pool`` para usar el pool de testcontainers
    (con migraciones aplicadas), y devuelve un ``httpx.AsyncClient`` con
    ``ASGITransport`` para hacer requests HTTP contra los endpoints.

    Antes de cada test, ``db_clean`` ejecuta TRUNCATE + re-seed para
    garantizar datos limpios sin recrear el contenedor.

    Args:
        db_pool: Pool session-scoped (contenedor compartido).
        db_clean: Pool function-scoped (datos limpios por test).

    Yields:
        httpx.AsyncClient: Cliente HTTP configurado con la app y pool.

    Ejemplo::

        async def test_health(api_client: httpx.AsyncClient) -> None:
            resp = await api_client.get("/v1/health")
            assert resp.status_code == 200
    """
    from src.adapters.api.dependencies import get_db_pool

    app = create_app()

    # Override: todos los repos y use cases reciben el pool de testcontainers
    # en lugar del pool del lifespan (que no existe en tests).
    async def _override_db_pool() -> asyncpg.Pool:
        return db_pool

    app.dependency_overrides[get_db_pool] = _override_db_pool

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
