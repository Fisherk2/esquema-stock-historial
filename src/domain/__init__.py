"""Domain layer — public API del nucleo de dominio.

Proporciona una superficie de import limpia para las capas de
aplicacion e infraestructura. Todos los componentes del dominio
son accesibles desde este modulo.

Ejemplo::

    from src.domain import (
        Movement, Product, Category,
        MovementType, SKU, Quantity,
        DomainError, InsufficientStockError,
        IMovementRepository, IProductRepository,
    )
"""

# Entities
from src.domain.entities.category import Category
from src.domain.entities.movement import Movement
from src.domain.entities.product import Product

# Exceptions
from src.domain.exceptions.domain_error import DomainError
from src.domain.exceptions.immutability_violation import (
    ImmutabilityViolationError,
)
from src.domain.exceptions.insufficient_stock import InsufficientStockError
from src.domain.exceptions.invalid_quantity import InvalidQuantityError
from src.domain.exceptions.invalid_sku import InvalidSKUError

# Ports (protocols)
from src.domain.ports.category_repository import ICategoryRepository
from src.domain.ports.movement_repository import IMovementRepository
from src.domain.ports.product_repository import IProductRepository
from src.domain.ports.stock_query_repository import IStockQueryRepository

# Rules
from src.domain.rules.immutability import enforce_immutability
from src.domain.rules.movement_consistency import (
    validate_movement_type_consistency,
)
from src.domain.rules.stock_validation import (
    calculate_stock_delta,
    validate_stock_not_negative,
)

# Value objects
from src.domain.value_objects.movement_type import MovementType
from src.domain.value_objects.quantity import Quantity
from src.domain.value_objects.sku import SKU

__all__ = [
    "SKU",
    "Category",
    "DomainError",
    "ICategoryRepository",
    "IMovementRepository",
    "IProductRepository",
    "IStockQueryRepository",
    "ImmutabilityViolationError",
    "InsufficientStockError",
    "InvalidQuantityError",
    "InvalidSKUError",
    "Movement",
    "MovementType",
    "Product",
    "Quantity",
    "calculate_stock_delta",
    "enforce_immutability",
    "validate_movement_type_consistency",
    "validate_stock_not_negative",
]
