"""Fixtures compartidos para tests E2E.

Reutiliza los fixtures de integracion (db_pool, db_clean) y proporciona
el fixture api_client con la app FastAPI para tests end-to-end.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest
from httpx import ASGITransport

# Re-importar fixtures de integracion para que pytest los encuentre
from tests.integration.conftest import db_clean, db_pool  # noqa: F401
from src.main import create_app

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    import asyncpg


@pytest.fixture
async def api_client(
    db_pool: asyncpg.Pool, db_clean: asyncpg.Pool
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Fixture E2E: cliente HTTP async contra la app con datos limpios.

    Reutiliza la misma infraestructura que los tests de integracion:
    testcontainers PostgreSQL, migraciones, seed data.
    """
    from src.adapters.api.dependencies import get_db_pool

    app = create_app()

    async def _override_db_pool() -> asyncpg.Pool:
        return db_pool

    app.dependency_overrides[get_db_pool] = _override_db_pool

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
