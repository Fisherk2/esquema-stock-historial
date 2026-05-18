"""Domain ports (protocols) — interfaces de dependencias invertidas."""

from src.domain.ports.category_repository import ICategoryRepository
from src.domain.ports.movement_repository import IMovementRepository
from src.domain.ports.product_repository import IProductRepository
from src.domain.ports.stock_query_repository import IStockQueryRepository
from src.domain.ports.unit_of_work import IUnitOfWork

__all__ = [
    "ICategoryRepository",
    "IMovementRepository",
    "IProductRepository",
    "IStockQueryRepository",
    "IUnitOfWork",
]
