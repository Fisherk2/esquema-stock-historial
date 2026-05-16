"""Domain entities — business objects with identity and invariants."""

from src.domain.entities.category import Category
from src.domain.entities.movement import Movement
from src.domain.entities.product import Product

__all__ = ["Category", "Movement", "Product"]
