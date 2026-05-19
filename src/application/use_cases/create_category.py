"""CreateCategoryUseCase — crea una nueva categoria de productos.

Operacion simple que construye la entidad Category y la persiste.
La validacion de nombre no vacio ocurre en el __post_init__ de Category.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.domain.entities.category import Category

if TYPE_CHECKING:
    from src.domain.ports.category_repository import ICategoryRepository


class CreateCategoryUseCase:
    """Crea una nueva categoria de productos.

    Args:
        category_repo: Repositorio de categorias.
    """

    def __init__(
        self,
        category_repo: ICategoryRepository,
    ) -> None:
        self._category_repo = category_repo

    async def execute(
        self,
        name: str,
        description: str | None = None,
    ) -> Category:
        """Ejecuta la creacion de una categoria.

        Args:
            name: Nombre de la categoria (no vacio).
            description: Descripcion opcional.

        Returns:
            Category: La categoria persistida con id asignado.

        Raises:
            ValueError: Si name es vacio.
        """
        category = Category(
            id=None,
            name=name,
            description=description,
            created_at=datetime.now(tz=UTC),
        )

        return await self._category_repo.create(category)
