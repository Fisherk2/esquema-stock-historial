"""PostgresStockQueryRepository — implementacion concreta de IStockQueryRepository.

Repositorio de consultas de stock. Usa la vista materializada
mv_stock_historical como fuente primaria para get_current_stock(),
con fallback a calculo directo si la vista no existe.
get_stock_at_date() siempre usa calculo directo (la MV solo tiene
stock actual).

Ejemplo de uso sin transaccion::

    repo = PostgresStockQueryRepository(pool)
    stock = await repo.get_current_stock(product_id=1)

Ejemplo de uso con Unit of Work::

    async with PostgresUnitOfWork(pool) as uow:
        repo = PostgresStockQueryRepository(pool, connection=uow.connection)
        stock = await repo.get_current_stock(product_id=1)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import asyncpg

from src.domain.ports.stock_query_repository import IStockQueryRepository

if TYPE_CHECKING:
    from datetime import datetime

logger = logging.getLogger(__name__)


class PostgresStockQueryRepository(IStockQueryRepository):
    """Repositorio de consultas de stock con MV + fallback directo.

    Estrategia de dos niveles:

    1. **get_current_stock()**: Intenta primero la vista materializada
       ``mv_stock_historical`` (Index Scan, <1ms). Si la vista no existe
       (migracion 008 no aplicada o error), hace fallback automaticamente
       al calculo directo con CASE/SUM sobre la tabla ``movements``.

    2. **get_stock_at_date()**: Siempre usa calculo directo, ya que la
       vista materializada solo contiene el stock actual, no historico.

    Esta estrategia garantiza que las consultas funcionen tanto antes
    como despues de aplicar la migracion 008.
    """

    _MV_CURRENT_STOCK_SQL = """
        SELECT current_stock
        FROM mv_stock_historical
        WHERE product_id = $1
    """

    _CURRENT_STOCK_SQL = """
        SELECT COALESCE(
            SUM(
                CASE movement_type
                    WHEN 'IN' THEN quantity
                    WHEN 'OUT' THEN -quantity
                    WHEN 'ADJUSTMENT' THEN quantity
                    WHEN 'TRANSFER' THEN -quantity
                    ELSE 0
                END
            ), 0
        ) AS stock
        FROM movements
        WHERE product_id = $1
    """

    _STOCK_AT_DATE_SQL = """
        SELECT COALESCE(
            SUM(
                CASE movement_type
                    WHEN 'IN' THEN quantity
                    WHEN 'OUT' THEN -quantity
                    WHEN 'ADJUSTMENT' THEN quantity
                    WHEN 'TRANSFER' THEN -quantity
                    ELSE 0
                END
            ), 0
        ) AS stock
        FROM movements
        WHERE product_id = $1
          AND created_at <= $2
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        connection: asyncpg.Connection | None = None,
    ) -> None:
        """Inicializa el repositorio con pool y conexion opcional.

        Args:
            pool: Pool de conexiones asyncpg (requerido).
            connection: Conexion activa para transacciones (opcional).
        """
        self._pool = pool
        self._connection = connection

    def _get_conn(self) -> asyncpg.Pool | asyncpg.Connection:
        """Retorna la conexion activa o el pool."""
        return self._connection if self._connection else self._pool

    async def get_current_stock(self, product_id: int) -> float:
        """Obtiene el stock actual via vista materializada con fallback.

        Intenta primero consultar la vista materializada. Si no existe
        (migracion 008 no aplicada) o el producto no esta en la vista
        (producto nuevo sin refresh), usa calculo directo.
        """
        try:
            row = await self._get_conn().fetchrow(
                self._MV_CURRENT_STOCK_SQL, product_id
            )
            if row is not None:
                return float(row["current_stock"])
            # Producto no encontrado en MV (nuevo o no refrescado)
            return await self._get_stock_direct(product_id)
        except asyncpg.UndefinedTableError:
            logger.debug("mv_stock_historical not found, using direct calculation")
            return await self._get_stock_direct(product_id)

    async def _get_stock_direct(self, product_id: int) -> float:
        """Calculo directo de stock desde la tabla movements."""
        row = await self._get_conn().fetchrow(self._CURRENT_STOCK_SQL, product_id)
        return float(row["stock"]) if row else 0.0

    async def get_stock_at_date(self, product_id: int, date: datetime) -> float:
        """Calcula el stock en una fecha especifica."""
        row = await self._get_conn().fetchrow(self._STOCK_AT_DATE_SQL, product_id, date)
        return float(row["stock"]) if row else 0.0
