"""Domain rules — pure functions for business logic validation."""

from src.domain.rules.immutability import enforce_immutability
from src.domain.rules.movement_consistency import (
    validate_movement_type_consistency,
)
from src.domain.rules.stock_validation import (
    calculate_stock_delta,
    validate_stock_not_negative,
)

__all__ = [
    "calculate_stock_delta",
    "enforce_immutability",
    "validate_movement_type_consistency",
    "validate_stock_not_negative",
]
