"""ListProductsUseCase — lista productos con paginacion y conteo exacto.

Retorna una tupla (items, total) donde total se obtiene de
count_all() para paginacion precisa.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.product import Product
    from src.domain.ports.product_repository import IProductRepository


class ListProductsUseCase:
    """Lista productos del inventario con paginacion.

    Args:
        product_repo: Repositorio de productos.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
    ) -> None:
        self._product_repo = product_repo

    async def execute(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Product], int]:
        """Ejecuta la lista de productos.

        Args:
            limit: Maximo de resultados (default 100).
            offset: Desplazamiento para paginacion (default 0).

        Returns:
            tuple[list[Product], int]: Lista de productos ordenados por ID
                y el total de productos disponibles.
        """
        items = await self._product_repo.list_all(limit=limit, offset=offset)
        total = await self._product_repo.count_all()
        return items, total
