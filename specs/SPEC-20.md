# SPEC-20: Entidades del Dominio

**Fase:** F2 — Núcleo de Dominio  
**Dependencias:** Spec-11 (Esquema y Migraciones) ✅ Completado  
**Prioridad:** Alta  
**Estado:** En Progreso

---

## Objective

Definir las entidades centrales del dominio (`Category`, `Product`, `Movement`) y sus value objects asociados (`MovementType`, `SKU`, `Quantity`), así como la jerarquía de excepciones de dominio. Estas entidades son el núcleo inmutable del sistema y **no dependen de ninguna capa externa**.

**Principios de diseño:**
- **No Pydantic en el dominio** — entidades son `@dataclass` nativos, validación pura
- **Inmutabilidad por diseño** — `Movement` usa `frozen=True`
- **Identidad técnica separada de identidad de negocio** — `id: int | None` (técnica) vs `SKU` (negocio)
- **FK como referencias, no navegación** — `Product` tiene `category_id: int`, no un objeto `Category`

---

## Entities

### Entity: `Category`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class Category:
    """Categoría de productos del inventario.

    Entidad inmutable: una vez construida, no puede modificarse.

    Attributes:
        id: Identificador técnico (None hasta persistencia).
        name: Nombre único de la categoría (no vacío).
        description: Descripción opcional.
        created_at: Marca de tiempo de creación (timezone-aware).
    """

    id: int | None
    name: str
    description: str | None
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Category name cannot be empty")

    __hash__ = None  # type: ignore[assignment]
```

**Invariants:**
- `name` no puede ser vacío ni solo espacios
- `id` es `None` hasta que se persiste en la base de datos

---

### Entity: `Product`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from src.domain.value_objects.sku import SKU


@dataclass(frozen=True)
class Product:
    """Producto del inventario.

    Entidad inmutable: una vez construida, no puede modificarse.

    Attributes:
        id: Identificador técnico (None hasta persistencia).
        sku: Identificador de negocio (Value Object validado).
        name: Nombre del producto (no vacío).
        description: Descripción opcional.
        unit_of_measure: Unidad de medida.
        category_id: Referencia FK a Category (no navegación).
        min_stock_threshold: Umbral mínimo de stock (>= 0).
        created_at: Marca de tiempo de creación (timezone-aware).
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
        if not self.name or not self.name.strip():
            raise ValueError("Product name cannot be empty")
        if self.min_stock_threshold < 0:
            raise ValueError("min_stock_threshold cannot be negative")
        if not self.unit_of_measure or not self.unit_of_measure.strip():
            raise ValueError("unit_of_measure cannot be empty")

    __hash__ = None  # type: ignore[assignment]
```

**Invariants:**
- `name` no puede ser vacío ni solo espacios
- `min_stock_threshold` >= 0
- `unit_of_measure` no puede ser vacío
- `sku` ya está validado por el Value Object `SKU`

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
    """Movimiento de inventario — Source of Truth inmutable.

    Una vez creado, un Movement no se modifica. Las correcciones se
    realizan mediante movimientos compensatorios (type: ADJUSTMENT).

    Attributes:
        id: Identificador técnico (None hasta persistencia).
        product_id: Referencia FK al producto afectado.
        movement_type: Tipo de movimiento (IN, OUT, ADJUSTMENT, TRANSFER).
        quantity: Cantidad movida (siempre > 0).
        metadata: Datos contextuales opcionales (origen/destino, razón, etc.).
        reference: Referencia externa (número de orden, factura, etc.).
        created_at: Marca de tiempo de creación (timezone-aware).
    """

    id: int | None
    product_id: int
    movement_type: MovementType
    quantity: Quantity
    metadata: dict[str, Any]
    created_at: datetime
    reference: str | None = None

    def __post_init__(self) -> None:
        # frozen=True previene mutaciones en runtime
        # Validación adicional de metadata según tipo de movimiento
        self._validate_metadata_consistency()

    def _validate_metadata_consistency(self) -> None:
        """Valida que el metadata sea consistente con el tipo de movimiento."""
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
- `frozen=True` — inmutable por diseño del lenguaje
- `quantity.value` siempre > 0 (validado por `Quantity` VO)
- `TRANSFER` requiere `origin` y `destination` en metadata
- `ADJUSTMENT` requiere `reason` en metadata
- **No tiene métodos mutadores** — las correcciones son nuevos movimientos

---

## Value Objects

### Value Object: `MovementType`

```python
from __future__ import annotations

from enum import StrEnum


class MovementType(StrEnum):
    """Tipo de movimiento de inventario.

    Usa StrEnum (Python 3.11+) para serialización directa a string
    sin mixin boilerplate. Mapea 1:1 con el ENUM nativo de PostgreSQL
    `movement_type`.

    Values:
        IN: Entrada de stock al inventario.
        OUT: Salida de stock del inventario.
        ADJUSTMENT: Ajuste de stock (siempre cantidad positiva).
        TRANSFER: Transferencia entre ubicaciones (metadata con origin/destination).
    """

    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"
```

**Invariants:**
- Conjunto cerrado de 4 valores (no extensible en runtime)
- Mapeo exacto con el ENUM de PostgreSQL definido en migración 001

---

### Value Object: `SKU`

```python
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SKU:
    """Stock Keeping Unit — identificador de negocio del producto.

    Attributes:
        value: Valor del SKU (no vacío, max 50 chars, alfanumérico + guiones).

    Raises:
        InvalidSKUError: Si el valor no cumple las reglas de formato.
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
- No vacío
- Longitud máxima: 50 caracteres
- Caracteres permitidos: alfanuméricos, guiones (`-`), guiones bajos (`_`)
- Inmutable (`frozen=True`)

---

### Value Object: `Quantity`

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Quantity:
    """Cantidad de un movimiento de inventario.

    Attributes:
        value: Valor numérico de la cantidad (siempre > 0).

    Raises:
        InvalidQuantityError: Si el valor no es positivo.
    """

    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            from src.domain.exceptions.invalid_quantity import InvalidQuantityError

            raise InvalidQuantityError(self.value)
```

**Invariants:**
- `value` siempre > 0
- Entero (no flotante)
- Inmutable (`frozen=True`)

---

## Domain Exceptions

### Base Exception

```python
class DomainError(Exception):
    """Excepción base del dominio.

    Todas las excepciones de dominio heredan de esta clase para
    permitir captura genérica sin atrapar excepciones del sistema.
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
    """Producto no encontrado en el inventario."""

    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"Product with id {product_id} not found")


class CategoryNotFoundError(DomainError):
    """Categoría no encontrada en el inventario."""

    def __init__(self, category_id: int) -> None:
        self.category_id = category_id
        super().__init__(f"Category with id {category_id} not found")


class InsufficientStockError(DomainError):
    """El stock resultante sería negativo tras aplicar un movimiento."""

    def __init__(self, product_id: int, requested: int, available: int) -> None:
        self.product_id = product_id
        self.requested = requested
        self.available = available
        super().__init__(
            f"Insufficient stock for product {product_id}: "
            f"requested {requested}, available {available}"
        )


class ImmutabilityViolationError(DomainError):
    """Se intentó modificar una entidad inmutable."""

    def __init__(self, entity_type: str, entity_id: int | None = None) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            f"Cannot modify immutable entity {entity_type} (id={entity_id})"
        )


class InvalidSKUError(DomainError):
    """El SKU no cumple las reglas de formato."""

    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(f"Invalid SKU format: '{value}'")


class InvalidQuantityError(DomainError):
    """La cantidad no es un entero positivo."""

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
3. ~~Should `Movement` have a `__hash__` method for use in sets/dicts?~~ → **Resolved:** Todas las entidades tienen `__hash__ = None` para prevenir uso en sets/dicts (semántica de identidad, no valor).
