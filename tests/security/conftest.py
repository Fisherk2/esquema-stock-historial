"""Fixtures compartidos para tests de seguridad.

Proporciona el fixture api_client para tests contra la API.
Los fixtures de base de datos (db_pool, db_clean) vienen de tests/conftest.py.
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
    db_pool: asyncpg.Pool,
    db_clean: asyncpg.Pool,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Fixture: cliente HTTP async contra la app con datos limpios."""
    from src.adapters.api.dependencies import get_db_pool

    app = create_app()

    async def _override_db_pool() -> asyncpg.Pool:
        return db_pool

    app.dependency_overrides[get_db_pool] = _override_db_pool

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
