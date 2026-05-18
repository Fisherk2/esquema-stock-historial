"""PostgresStockQueryRepository — implementacion concreta de IStockQueryRepository.

Repositorio de consultas de stock con calculo directo desde la tabla
movements mediante CASE/SUM. En Spec-31 se optimizara con la vista
materializada mv_stock_historical.

Ejemplo de uso sin transaccion::

    repo = PostgresStockQueryRepository(pool)
    stock = await repo.get_current_stock(product_id=1)

Ejemplo de uso con Unit of Work::

    async with PostgresUnitOfWork(pool) as uow:
        repo = PostgresStockQueryRepository(pool, connection=uow.connection)
        stock = await repo.get_current_stock(product_id=1)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.ports.stock_query_repository import IStockQueryRepository

if TYPE_CHECKING:
    from datetime import datetime

    import asyncpg


class PostgresStockQueryRepository(IStockQueryRepository):
    """Repositorio de consultas de stock con calculo directo."""

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
        """Calcula el stock actual sumando todos los movimientos del producto."""
        row = await self._get_conn().fetchrow(
            self._CURRENT_STOCK_SQL, product_id
        )
        return float(row["stock"]) if row else 0.0

    async def get_stock_at_date(
        self, product_id: int, date: datetime
    ) -> float:
        """Calcula el stock en una fecha especifica."""
        row = await self._get_conn().fetchrow(
            self._STOCK_AT_DATE_SQL, product_id, date
        )
        return float(row["stock"]) if row else 0.0
