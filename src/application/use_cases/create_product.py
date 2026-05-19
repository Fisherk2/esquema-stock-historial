"""CreateProductUseCase — crea un nuevo producto en el inventario.

Verifica que la categoria existe antes de construir el producto.
El SKU se valida a traves del value object SKU.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.domain.entities.product import Product
from src.domain.value_objects.sku import SKU

if TYPE_CHECKING:
    from src.domain.ports.category_repository import ICategoryRepository
    from src.domain.ports.product_repository import IProductRepository


class CreateProductUseCase:
    """Crea un nuevo producto en el inventario.

    Flujo:
        1. Verificar que la categoria existe.
        2. Construir la entidad Product (con SKU VO).
        3. Persistir y retornar.

    Args:
        product_repo: Repositorio de productos.
        category_repo: Repositorio de categorias.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        category_repo: ICategoryRepository,
    ) -> None:
        self._product_repo = product_repo
        self._category_repo = category_repo

    async def execute(
        self,
        sku: str,
        name: str,
        unit_of_measure: str,
        category_id: int,
        description: str | None = None,
        min_stock_threshold: int = 0,
    ) -> Product:
        """Ejecuta la creacion de un producto.

        Args:
            sku: Codigo SKU del producto.
            name: Nombre del producto (no vacio).
            unit_of_measure: Unidad de medida (e.g., "unit", "kg").
            category_id: ID de la categoria a la que pertenece.
            description: Descripcion opcional.
            min_stock_threshold: Umbral minimo de stock (default 0).

        Returns:
            Product: El producto persistido con id asignado.

        Raises:
            ValueError: Si la categoria no existe.
            InvalidSKUError: Si el SKU no cumple el patron requerido.
            ValueError: Si name o unit_of_measure son vacios.
        """
        # 1. Verificar que la categoria existe
        category = await self._category_repo.get_by_id(category_id)
        if category is None:
            raise ValueError(f"Category {category_id} not found")

        # 2. Construir y persistir
        product = Product(
            id=None,
            sku=SKU(sku),
            name=name,
            description=description,
            unit_of_measure=unit_of_measure,
            category_id=category_id,
            min_stock_threshold=min_stock_threshold,
            created_at=datetime.now(tz=UTC),
        )

        return await self._product_repo.create(product)
