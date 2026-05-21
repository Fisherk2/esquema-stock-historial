"""IStockQueryRepository port — interfaz para consultas de stock.

Define el contrato para consultar el stock actual e historico de
productos. Separado de IMovementRepository por ISP (Interface
Segregation Principle): las consultas de stock son un concepto
diferente al CRUD de movimientos.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime


@runtime_checkable
class IStockQueryRepository(Protocol):
    """Contrato para consultas de stock de productos.

    Separa las consultas de stock del CRUD de movimientos para
    cumplir con ISP.
    """

    async def get_current_stock(self, product_id: int) -> float:
        """Obtiene el stock actual de un producto.

        Args:
            product_id: ID del producto.

        Returns:
            Stock actual del producto.
        """
        ...

    async def get_stock_at_date(
        self,
        product_id: int,
        date: datetime,
    ) -> float:
        """Obtiene el stock de un producto en una fecha dada.

        Args:
            product_id: ID del producto.
            date: Fecha para la cual consultar el stock.

        Returns:
            Stock del producto en la fecha especificada.
        """
        ...

    async def get_current_stock_with_lock(self, product_id: int) -> float:
        """Obtiene stock con lock pessimista (SELECT FOR UPDATE).

        Serializa transacciones concurrentes del mismo producto y
        calcula el stock directamente desde movements (no MV).
        Solo debe usarse dentro de una transaccion activa (UoW).

        Args:
            product_id: ID del producto a bloquear y consultar.

        Returns:
            Stock actual calculado directamente.
        """
        ...
