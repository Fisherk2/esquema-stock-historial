"""Infrastructure repositories — re-exports de todos los repositorios y mappers.

Proporciona una superficie de import conveniente para la capa de
aplicacion.

Ejemplo::

    from src.infrastructure.repositories import (
        PostgresMovementRepository,
        PostgresProductRepository,
        PostgresCategoryRepository,
        PostgresStockQueryRepository,
    )
"""

from src.infrastructure.repositories.category_repository import (
    PostgresCategoryRepository,
)
from src.infrastructure.repositories.mappers import (
    map_category_row,
    map_movement_row,
    map_product_row,
)
from src.infrastructure.repositories.movement_repository import (
    PostgresMovementRepository,
)
from src.infrastructure.repositories.product_repository import (
    PostgresProductRepository,
)
from src.infrastructure.repositories.stock_query_repository import (
    PostgresStockQueryRepository,
)

__all__ = [
    "PostgresCategoryRepository",
    "PostgresMovementRepository",
    "PostgresProductRepository",
    "PostgresStockQueryRepository",
    "map_category_row",
    "map_movement_row",
    "map_product_row",
]
