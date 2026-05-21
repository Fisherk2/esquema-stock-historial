"""Domain exceptions — error hierarchy for business rule violations."""

from src.domain.exceptions.category_not_found import CategoryNotFoundError
from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError
from src.domain.exceptions.domain_error import DomainError
from src.domain.exceptions.immutability_violation import (
    ImmutabilityViolationError,
)
from src.domain.exceptions.insufficient_stock import InsufficientStockError
from src.domain.exceptions.invalid_quantity import InvalidQuantityError
from src.domain.exceptions.invalid_sku import InvalidSKUError
from src.domain.exceptions.product_not_found import ProductNotFoundError

__all__ = [
    "CategoryNotFoundError",
    "ConcurrencyConflictError",
    "DomainError",
    "ImmutabilityViolationError",
    "InsufficientStockError",
    "InvalidQuantityError",
    "InvalidSKUError",
    "ProductNotFoundError",
]
