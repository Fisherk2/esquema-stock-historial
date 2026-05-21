"""Gestión del pool de conexiones a PostgreSQL.

Administra el ciclo de vida del pool de conexiones asyncpg: creación,
obtención y cierre. El pool se inicializa y cierra desde el lifespan
de FastAPI (``src/main.py``).

Patrón aplicado: Dependency Injection — ``init_pool()`` recibe ``Settings``
inyectado en lugar de crear la configuración internamente.

Ejemplo de uso como FastAPI dependency::

    from fastapi import Depends
    from src.infrastructure.db.connection import get_db

    @router.get("/items")
    async def list_items(pool=Depends(get_db)):
        row = await pool.fetchrow("SELECT 1")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import asyncpg

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from src.core.config import Settings

logger = logging.getLogger(__name__)

# Singleton a nivel de módulo: gestionado por el lifespan de FastAPI
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool | None:
    """Obtiene la instancia actual del pool de conexiones.

    Returns:
        asyncpg.Pool | None: El pool activo o None si no se ha inicializado.
    """
    return _pool


async def init_pool(settings: Settings) -> None:
    """Inicializa el pool de conexiones asyncpg.

    Crea un pool con tamaño configurable via Settings
    (``db_pool_min_size`` y ``db_pool_max_size``, por defecto 2 y 10).
    En ``development`` permite un fallback graceful si la DB no está lista.
    En ``production`` falla explícitamente para evitar startup silencioso.

    Args:
        settings: Configuración con el DSN de conexión.

    Raises:
        RuntimeError: Si la DB no está disponible en producción.

    Ejemplo::

        settings = Settings()
        await init_pool(settings)
        pool = await get_pool()  # asyncpg.Pool activo
    """
    global _pool

    # Guard: cerrar pool existente antes de crear uno nuevo
    if _pool is not None:
        logger.warning(
            "Pool already initialized — closing existing pool before re-init"
        )
        await close_pool()

    try:
        timeout_ms = settings.api_statement_timeout_seconds * 1000
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            # server_settings aplica statement_timeout a TODAS las conexiones
            # del pool — correccion del bug donde SET solo afectaba una conexion
            server_settings={"statement_timeout": str(timeout_ms)},
        )
        logger.info("Database pool initialized (statement_timeout=%dms)", timeout_ms)
    except Exception as exc:
        # En producción, fallar hard — no permitir startup sin DB
        if settings.environment == "production":
            logger.error(
                "Database pool initialization FAILED in production. "
                "Application cannot start without database."
            )
            raise RuntimeError(
                "Database connection required in production but not available"
            ) from exc
        # En development, fallback graceful: la DB puede no estar lista
        logger.warning(
            "Database pool initialization failed (DB may not be available yet)"
        )
        _pool = None


async def close_pool() -> None:
    """Cierra el pool de conexiones activas.

    Libera todas las conexiones del pool y resetea la referencia global.
    Se invoca durante el shutdown de la aplicación.
    """
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


async def get_db() -> AsyncGenerator[asyncpg.Pool, None]:
    """Dependency de FastAPI para inyectar el pool en endpoints.

    Yields:
        asyncpg.Pool: El pool de conexiones activo.

    Raises:
        RuntimeError: Si el pool no ha sido inicializado.

    Ejemplo::

        @router.get("/items")
        async def list_items(pool=Depends(get_db)):
            rows = await pool.fetch("SELECT * FROM products")
    """
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    yield _pool
