"""DTOs de la capa de aplicacion — re-exports publicos."""

from src.application.dtos.category_dtos import CategoryOutput, CreateCategoryInput
from src.application.dtos.error_dtos import ErrorDetail, ErrorResponse
from src.application.dtos.movement_dtos import (
    CreateMovementInput,
    MovementListOutput,
    MovementOutput,
)
from src.application.dtos.product_dtos import (
    CreateProductInput,
    ProductListOutput,
    ProductOutput,
)
from src.application.dtos.stock_dtos import CurrentStockOutput, StockAtDateOutput

__all__ = [
    "CategoryOutput",
    "CreateCategoryInput",
    "CreateMovementInput",
    "CreateProductInput",
    "CurrentStockOutput",
    "ErrorDetail",
    "ErrorResponse",
    "MovementListOutput",
    "MovementOutput",
    "ProductListOutput",
    "ProductOutput",
    "StockAtDateOutput",
]
