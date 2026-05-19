"""QueryCurrentStockUseCase — consulta stock actual de un producto.

Operacion de lectura pura que delega al repositorio de stock.
No requiere Unit of Work ni transacciones.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.ports.stock_query_repository import IStockQueryRepository


class QueryCurrentStockUseCase:
    """Consulta el stock actual de un producto.

    Args:
        stock_query_repo: Repositorio de consultas de stock.
    """

    def __init__(
        self,
        stock_query_repo: IStockQueryRepository,
    ) -> None:
        self._stock_query_repo = stock_query_repo

    async def execute(self, product_id: int) -> float:
        """Ejecuta la consulta de stock actual.

        Args:
            product_id: ID del producto.

        Returns:
            float: Stock actual del producto (0 si no tiene movimientos).
        """
        return await self._stock_query_repo.get_current_stock(product_id)
