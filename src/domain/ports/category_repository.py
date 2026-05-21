"""ICategoryRepository port — interfaz para persistencia de categorias.

Define el contrato que cualquier implementacion de repositorio de
categorias debe cumplir.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.domain.entities.category import Category


@runtime_checkable
class ICategoryRepository(Protocol):
    """Contrato para repositorios de categorias."""

    async def create(self, category: Category) -> Category:
        """Persiste una nueva categoria.

        Args:
            category: Entidad Category a persistir.

        Returns:
            Category persistida con id asignado.
        """
        ...

    async def get_by_id(self, category_id: int) -> Category | None:
        """Recupera una categoria por su ID.

        Args:
            category_id: ID de la categoria.

        Returns:
            Category si existe, None en caso contrario.
        """
        ...

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Category]:
        """Lista categorias con paginacion.

        Args:
            limit: Numero maximo de categorias a retornar.
            offset: Numero de categorias a saltar.

        Returns:
            Lista de categorias paginadas.
        """
        ...
