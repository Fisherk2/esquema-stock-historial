# SPEC-20: Domain Entities

**Phase:** F2 — Domain Core
**Dependencies:** Spec-11 (Schema and Migrations) ✅ Completed
**Priority:** High
**Status:** In Progress

---

## Objective

Define the core domain entities (`Category`, `Product`, `Movement`) and their associated value objects (`MovementType`, `SKU`, `Quantity`), as well as the domain exception hierarchy. These entities are the immutable core of the system and **do not depend on any external layer**.

**Design principles:**
- **No Pydantic in the domain** — entities are native `@dataclass`, pure validation
- **Immutability by design** — `Movement` uses `frozen=True`
- **Technical identity separate from business identity** — `id: int | None` (technical) vs `SKU` (business)
- **FK as references, not navigation** — `Product` has `category_id: int`, not a `Category` object

---

## Entities

### Entity: `Category`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class Category:
    """Product category grouping entity.

    Attributes:
        id: Technical identifier (None until persistence).
        name: Category name (must be unique, non-empty).
        description: Optional description.
        created_at: Creation timestamp (UTC, timezone-aware).
    """

    id: int | None = None
    name: str = field(repr=False)
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    __hash__ = None  # type: ignore[assignment]
```

**Invariants:**
- `name` cannot be empty or only whitespace
- `name` must be unique at the DB level (UNIQUE constraint)
- `created_at` is set on creation, never changes

---

### Entity: `Product`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class Product:
    """Inventory product entity.

    Attributes:
        id: Technical identifier (None until persistence).
        sku: Business identifier (SKU value object).
        name: Product name (non-empty).
        category_id: FK reference to category (not a Category object).
        min_stock_threshold: Minimum stock level for alerts.
        unit_of_measure: Measurement unit (e.g., 'units', 'kg', 'liters').
        created_at: Creation timestamp (UTC, timezone-aware).
    """

    id: int | None = None
    sku: str = field(compare=False)
    name: str = field(repr=False)
    category_id: int
    min_stock_threshold: int = 0
    unit_of_measure: str = "units"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Product name cannot be empty")
        if self.min_stock_threshold < 0:
            raise ValueError("min_stock_threshold cannot be negative")
        if not self.unit_of_measure or not self.unit_of_measure.strip():
            raise ValueError("unit_of_measure cannot be empty")

    __hash__ = None  # type: ignore[assignment]
```

**Invariants:**
- `name` cannot be empty or whitespace only
- `min_stock_threshold` >= 0
- `unit_of_measure` cannot be empty
- `sku` is already validated by the `SKU` Value Object

---

### Entity: `Movement`

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.value_objects.movement_type import MovementType
from src.domain.value_objects.quantity import Quantity


@dataclass(frozen=True)
class Movement:
    """Inventory movement — Immutable Source of Truth.

    Once created, a Movement is never modified. Corrections are
    performed via compensatory movements (type: ADJUSTMENT).

    Attributes:
        id: Technical identifier (None until persistence).
        product_id: FK reference to the affected product.
        movement_type: Type of movement (IN, OUT, ADJUSTMENT, TRANSFER).
        quantity: Moved quantity (always > 0).
        metadata: Optional contextual data (origin/destination, reason, etc.).
        reference: External reference (order number, invoice, etc.).
        created_at: Creation timestamp (timezone-aware).
    """

    id: int | None
    product_id: int
    movement_type: MovementType
    quantity: Quantity
    metadata: dict[str, Any]
    created_at: datetime
    reference: str | None = None

    def __post_init__(self) -> None:
        # frozen=True prevents mutations at runtime
        # Additional metadata validation by movement type
        self._validate_metadata_consistency()

    def _validate_metadata_consistency(self) -> None:
        """Validates that metadata is consistent with movement type."""
        if self.movement_type == MovementType.TRANSFER:
            if "origin" not in self.metadata or "destination" not in self.metadata:
                raise ValueError(
                    "TRANSFER movements require 'origin' and 'destination' in metadata"
                )
        elif self.movement_type == MovementType.ADJUSTMENT:
            if "reason" not in self.metadata:
                raise ValueError(
                    "ADJUSTMENT movements require 'reason' in metadata"
                )
```

**Invariants:**
- `frozen=True` — immutable by language design
- `quantity.value` always > 0 (validated by `Quantity` VO)
- `TRANSFER` requires `origin` and `destination` in metadata
- `ADJUSTMENT` requires `reason` in metadata
- **No mutator methods** — corrections are new movements

---

## Value Objects

### Value Object: `MovementType`

```python
from __future__ import annotations

from enum import StrEnum


class MovementType(StrEnum):
    """Inventory movement type.

    Uses StrEnum (Python 3.11+) for direct string serialization
    without mixin boilerplate. Maps 1:1 to the native PostgreSQL
    `movement_type` ENUM.

    Values:
        IN: Stock entry into inventory.
        OUT: Stock exit from inventory.
        ADJUSTMENT: Stock adjustment (always positive quantity).
        TRANSFER: Transfer between locations (metadata with origin/destination).
    """

    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"
```

**Invariants:**
- Closed set of 4 values (not extensible at runtime)
- Exact mapping with PostgreSQL ENUM defined in migration 001

---

### Value Object: `SKU`

```python
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SKU:
    """Stock Keeping Unit — product business identifier.

    Attributes:
        value: SKU value (non-empty, max 50 chars, alphanumeric + hyphens).

    Raises:
        InvalidSKUError: If the value does not meet format rules.
    """

    value: str

    _PATTERN = re.compile(r"^[A-Za-z0-9\-_]{1,50}$")

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            from src.domain.exceptions.invalid_sku import InvalidSKUError

            raise InvalidSKUError(self.value)
        if not self._PATTERN.match(self.value):
            from src.domain.exceptions.invalid_sku import InvalidSKUError

            raise InvalidSKUError(self.value)
```

**Invariants:**
- Not empty
- Maximum length: 50 characters
- Allowed characters: alphanumeric, hyphens (`-`), underscores (`_`)
- Immutable (`frozen=True`)

---

### Value Object: `Quantity`

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Quantity:
    """Quantity of an inventory movement.

    Attributes:
        value: Numeric value of the quantity (always > 0).

    Raises:
        InvalidQuantityError: If the value is not positive.
    """

    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            from src.domain.exceptions.invalid_quantity import InvalidQuantityError

            raise InvalidQuantityError(self.value)
```

**Invariants:**
- `value` always > 0
- Integer (not float)
- Immutable (`frozen=True`)

---

## Domain Exceptions

### Base Exception

```python
class DomainError(Exception):
    """Base domain exception.

    All domain exceptions inherit from this class to
    allow generic catching without catching system exceptions.
    """
```

### Exception Hierarchy

```
DomainError (Exception)
├── ProductNotFoundError
│   └── product_id: int
├── CategoryNotFoundError
│   └── category_id: int
├── InsufficientStockError
│   ├── product_id: int
│   ├── requested: int
│   └── available: int
├── ImmutabilityViolationError
│   ├── entity_type: str
│   └── entity_id: int | None
├── ConcurrencyConflictError
│   └── operation: str
├── InvalidSKUError
│   └── value: str
└── InvalidQuantityError
    └── value: int
```

```python
from src.domain.exceptions.domain_error import DomainError


class ProductNotFoundError(DomainError):
    """Product not found in inventory."""

    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"Product with id {product_id} not found")


class CategoryNotFoundError(DomainError):
    """Category not found in inventory."""

    def __init__(self, category_id: int) -> None:
        self.category_id = category_id
        super().__init__(f"Category with id {category_id} not found")


class InsufficientStockError(DomainError):
    """The resulting stock would be negative after applying a movement."""

    def __init__(self, product_id: int, requested: int, available: int) -> None:
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for product {product_id}: "
            f"requested {requested}, available {available}"
        )


class ImmutabilityViolationError(DomainError):
    """Attempted to modify an immutable entity."""

    def __init__(self, entity_type: str, entity_id: int | None = None) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            f"Cannot modify immutable entity {entity_type} (id={entity_id})"
        )


class InvalidSKUError(DomainError):
    """SKU does not meet format rules."""

    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(f"Invalid SKU format: '{value}'")


class InvalidQuantityError(DomainError):
    """Quantity is not a positive integer."""

    def __init__(self, value: int) -> None:
        self.value = value
        super().__init__(f"Quantity must be positive, got {value}")
```

---

## Files

| File | Description |
|------|-------------|
| `src/domain/entities/category.py` | Category dataclass |
| `src/domain/entities/product.py` | Product dataclass |
| `src/domain/entities/movement.py` | Movement frozen dataclass |
| `src/domain/entities/__init__.py` | Re-exports: Category, Product, Movement |
| `src/domain/value_objects/movement_type.py` | MovementType enum |
| `src/domain/value_objects/sku.py` | SKU frozen dataclass with validation |
| `src/domain/value_objects/quantity.py` | Quantity frozen dataclass with validation |
| `src/domain/value_objects/__init__.py` | Re-exports: MovementType, SKU, Quantity |
| `src/domain/exceptions/domain_error.py` | Base DomainError |
| `src/domain/exceptions/insufficient_stock.py` | InsufficientStockError |
| `src/domain/exceptions/immutability_violation.py` | ImmutabilityViolationError |
| `src/domain/exceptions/invalid_sku.py` | InvalidSKUError |
| `src/domain/exceptions/invalid_quantity.py` | InvalidQuantityError |
| `src/domain/exceptions/__init__.py` | Re-exports: all domain exceptions |

---

## Acceptance Criteria

- [ ] All entities use `@dataclass(frozen=True)` (Movement, Product, Category)
- [ ] All entities have `__hash__ = None` to prevent use in sets/dicts (identity semantics)
- [ ] No Pydantic imports in `domain/` — pure Python dataclasses only
- [ ] `domain/` imports only from stdlib and internal domain modules (no `application/`, `infrastructure/`, `adapters/`)
- [ ] `SKU.__post_init__` validates non-empty, max 50 chars, alphanumeric+hyphens+underscores
- [ ] `Quantity.__post_init__` validates `value > 0`
- [ ] `MovementType` uses `StrEnum` (not `str, Enum`) for direct string serialization
- [ ] `InsufficientStockError` carries `product_id`, `requested`, `available`
- [ ] `ProductNotFoundError` carries `product_id`
- [ ] `CategoryNotFoundError` carries `category_id`
- [ ] All exceptions inherit from `DomainError`
- [ ] `make lint` passes with zero errors on all domain files
- [ ] Unit tests for value object validation and entity construction

---

## Open Questions

1. Should `SKU` allow dots (`.`) in addition to hyphens and underscores? (Some industries use `PROD.001`)
2. Should `Product.__post_init__` validate `unit_of_measure` against a known set of values?
3. ~~Should `Movement` have a `__hash__` method for use in sets/dicts?~~ → **Resolved:** All entities have `__hash__ = None` to prevent use in sets/dicts (identity semantics, not value).
