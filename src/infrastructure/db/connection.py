from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import asyncpg

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from src.core.config import Settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool | None:
    return _pool


async def init_pool(settings: Settings) -> None:
    global _pool
    try:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=2,
            max_size=10,
        )
        logger.info("Database pool initialized")
    except Exception:
        logger.warning(
            "Database pool initialization failed " "(DB may not be available yet)"
        )
        _pool = None


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


async def get_db() -> AsyncGenerator[asyncpg.Pool, None]:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    yield _pool
