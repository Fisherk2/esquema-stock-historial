"""Funcion de refresh para la vista materializada mv_stock_historical.

Ejecuta ``REFRESH MATERIALIZED VIEW CONCURRENTLY`` para actualizar
la vista sin bloquear lecturas. Requiere que la vista tenga un indice
unico (creado en migracion 008).

Si la vista no existe aun (antes de ejecutar migracion 008), registra
un warning y continua sin error.

Ejemplo::

    from src.infrastructure.db.refresh import refresh_stock_view

    await refresh_stock_view(pool)
"""

from __future__ import annotations

import logging

import asyncpg

logger = logging.getLogger(__name__)

# REFRESH CONCURRENTLY no bloquea lecturas durante el refresh.
# Requiere indice unico en product_id (creado en migracion 008).
_REFRESH_SQL = "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_stock_historical"


async def refresh_stock_view(pool: asyncpg.Pool) -> None:
    """Refresca la vista materializada mv_stock_historical.

    Usa REFRESH CONCURRENTLY para no bloquear lecturas durante el
    refresh. Requiere que la vista tenga un indice unico (creado en
    migracion 008).

    Args:
        pool: Pool de conexiones asyncpg.

    Raises:
        asyncpg.UndefinedTableError: Si la vista no existe aun.

    Ejemplo::

        from src.infrastructure.db.refresh import refresh_stock_view

        await refresh_stock_view(pool)
    """
    try:
        await pool.execute(_REFRESH_SQL)
        logger.info("mv_stock_historical refreshed successfully")
    except asyncpg.UndefinedTableError:
        logger.warning("mv_stock_historical does not exist yet, skipping refresh")
    except Exception:
        logger.exception("Failed to refresh mv_stock_historical")
        raise
