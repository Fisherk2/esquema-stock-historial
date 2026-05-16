"""IProductRepository port — interfaz para persistencia de productos.

Define el contrato que cualquier implementacion de repositorio de
productos debe cumplir.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.domain.entities.product import Product


@runtime_checkable
class IProductRepository(Protocol):
    """Contrato para repositorios de productos."""

    async def create(self, product: Product) -> Product:
        """Persiste un nuevo producto.

        Args:
            product: Entidad Product a persistir.

        Returns:
            Product persistido con id asignado.
        """
        ...

    async def get_by_id(self, product_id: int) -> Product | None:
        """Recupera un producto por su ID.

        Args:
            product_id: ID del producto.

        Returns:
            Product si existe, None en caso contrario.
        """
        ...

    async def get_by_sku(self, sku: str) -> Product | None:
        """Recupera un producto por su SKU.

        Args:
            sku: Codigo SKU del producto (string, no VO).

        Returns:
            Product si existe, None en caso contrario.
        """
        ...

    async def list_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Product]:
        """Lista todos los productos con paginacion.

        Args:
            limit: Maximo de resultados (default 100).
            offset: Desplazamiento para paginacion (default 0).

        Returns:
            Lista de productos.
        """
        ...

    async def list_below_threshold(self, *, limit: int = 100) -> list[Product]:
        """Lista productos con stock por debajo del umbral minimo.

        Args:
            limit: Maximo de resultados (default 100).

        Returns:
            Lista de productos con stock bajo.
        """
        ...
