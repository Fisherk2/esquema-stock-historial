"""Product entity — articulo del inventario con SKU y umbrales.

Representa un producto en el sistema de inventario. Cada producto
tiene un SKU unico, nombre, unidad de medida y umbral minimo de stock
para alertas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.value_objects.sku import SKU


@dataclass
class Product:
    """Articulo del inventario.

    Args:
        id: Identificador unico (None antes de persistir).
        sku: Codigo SKU unico del producto.
        name: Nombre del producto (no vacio).
        description: Descripcion opcional del producto.
        unit_of_measure: Unidad de medida (e.g., "unit", "kg", "liter").
        category_id: ID de la categoria a la que pertenece.
        min_stock_threshold: Umbral minimo para alertas de stock bajo.
        created_at: Marca de tiempo UTC de creacion.

    Raises:
        ValueError: Si name o unit_of_measure son vacios, o si
            min_stock_threshold es negativo.
    """

    id: int | None
    sku: SKU
    name: str
    description: str | None
    unit_of_measure: str
    category_id: int
    min_stock_threshold: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __post_init__(self) -> None:
        """Valida invariantes del producto.

        Raises:
            ValueError: Si name o unit_of_measure son vacios, o si
                min_stock_threshold es negativo.
        """
        if not self.name:
            raise ValueError("Product name cannot be empty")
        if not self.unit_of_measure:
            raise ValueError("Product unit_of_measure cannot be empty")
        if self.min_stock_threshold < 0:
            raise ValueError(
                "min_stock_threshold cannot be negative, "
                f"got {self.min_stock_threshold}"
            )
