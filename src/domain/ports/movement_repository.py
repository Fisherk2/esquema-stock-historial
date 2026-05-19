"""IMovementRepository port — interfaz para persistencia de movimientos.

Define el contrato que cualquier implementacion de repositorio de
movimientos debe cumplir. No incluye update ni delete porque los
movimientos son inmutables (Source of Truth).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.domain.entities.movement import Movement


@runtime_checkable
class IMovementRepository(Protocol):
    """Contrato para repositorios de movimientos.

    Los movimientos son inmutables: solo se permite crear y leer.
    No existen metodos de update ni delete.
    """

    async def create(self, movement: Movement) -> Movement:
        """Persiste un nuevo movimiento.

        Args:
            movement: Entidad Movement a persistir.

        Returns:
            Movement persistido con id asignado.
        """
        ...

    async def get_by_id(self, movement_id: int) -> Movement | None:
        """Recupera un movimiento por su ID.

        Args:
            movement_id: ID del movimiento.

        Returns:
            Movement si existe, None en caso contrario.
        """
        ...

    async def list_by_product(
        self,
        product_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Movement]:
        """Lista movimientos de un producto con paginacion.

        Args:
            product_id: ID del producto.
            limit: Maximo de resultados (default 100).
            offset: Desplazamiento para paginacion (default 0).

        Returns:
            Lista de movimientos ordenados por created_at descendente.
        """
        ...

    async def count_by_product(self, product_id: int) -> int:
        """Cuenta el total de movimientos de un producto.

        Args:
            product_id: ID del producto.

        Returns:
            Total de movimientos del producto.
        """
        ...
