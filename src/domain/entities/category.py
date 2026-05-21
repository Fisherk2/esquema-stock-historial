"""Category entity — clasificacion de productos.

Representa una categoria de productos en el sistema de inventario.
Es la entidad mas simple del dominio: solo valida que el nombre
no sea vacio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class Category:
    """Clasificacion de productos.

    Entidad inmutable: una vez construida, no puede modificarse.
    Las actualizaciones se realizan creando una nueva categoria
    desde la base de datos.

    Args:
        id: Identificador unico (None antes de persistir).
        name: Nombre de la categoria (no vacio).
        description: Descripcion opcional de la categoria.
        created_at: Marca de tiempo UTC de creacion.

    Raises:
        ValueError: Si name es vacio.
    """

    id: int | None
    name: str
    description: str | None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __post_init__(self) -> None:
        """Valida que el nombre no sea vacio.

        Raises:
            ValueError: Si name es vacio.
        """
        if not self.name:
            raise ValueError("Category name cannot be empty")

    __hash__ = None  # type: ignore[assignment]
