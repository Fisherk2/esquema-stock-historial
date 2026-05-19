"""QueryStockAtDateUseCase — consulta stock historico en una fecha.

Delega al repositorio de stock el calculo directo sobre la tabla
de movimientos. La vista materializada solo contiene stock actual.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from src.domain.ports.stock_query_repository import IStockQueryRepository


class QueryStockAtDateUseCase:
    """Consulta el stock de un producto en una fecha historica.

    Args:
        stock_query_repo: Repositorio de consultas de stock.
    """

    def __init__(
        self,
        stock_query_repo: IStockQueryRepository,
    ) -> None:
        self._stock_query_repo = stock_query_repo

    async def execute(self, product_id: int, date: datetime) -> float:
        """Ejecuta la consulta de stock historico.

        Args:
            product_id: ID del producto.
            date: Fecha/hora de referencia (timezone-aware).

        Returns:
            float: Stock del producto en la fecha (0 si no hay movimientos anteriores).
        """
        return await self._stock_query_repo.get_stock_at_date(product_id, date)
