# SPEC-22: Protocolos/Interfaces (Ports)

**Phase:** F2 — Domain Core
**Dependencies:** Spec-20 (Entities) ✅ Completed
**Priority:** High
**Status:** Pending

---

## Objective

Definir los ports (interfaces) del dominio usando `typing.Protocol`. Estos protocols son los contratos que la capa de infraestructura debe implementar, siguiendo el **Dependency Inversion Principle (DIP)**. El dominio define QUÉ necesita; la infraestructura define CÓMO se provee.

**Principios de diseño:**
- **`typing.Protocol` con `@runtime_checkable`** — no `abc.ABC` ni `@abstractmethod`
- **Métodos async** — todos los repositorios operan con I/O asíncrono
- **Interface Segregation** — repositorios separados por responsabilidad (movimientos, productos, categorías, consultas de stock)
- **No mutación en MovementRepository** — sin métodos `update` o `delete` (inmutabilidad)

---

## Ports

### Port: `IMovementRepository`

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.entities.movement import Movement


@runtime_checkable
class IMovementRepository(Protocol):
    """Protocol for movement persistence and querying.

    Does not include update() or delete() methods — movements are
    immutable by domain design. Corrections are performed
    via new compensatory movements (ADJUSTMENT).
    """

    async def create(self, movement: Movement) -> Movement:
        """Persists a new movement.

        Args:
            movement: Movement to persist (no id assigned).

        Returns:
            Movement: The same movement with id populated after persistence.
        """
        ...

    async def get_by_id(self, movement_id: int) -> Movement | None:
        """Retrieves a movement by its ID.

        Args:
            movement_id: Technical identifier of the movement.

        Returns:
            Movement | None: The movement if it exists, None otherwise.
        """
        ...

    async def list_by_product(
        self,
        product_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Movement]:
        """Lists movements for a product, ordered by created_at DESC.

        Args:
            product_id: Product identifier.
            limit: Maximum number of movements to return.
            offset: Number of movements to skip (pagination).

        Returns:
            list[Movement]: List of movements ordered by date descending.
        """
        ...
```

**Design Notes:**
- **No `update()` ni `delete()`** — inmutabilidad es una regla de dominio
- `create()` retorna el Movement con `id` populated (no un string o int separado)
- `list_by_product()` usa paginación para evitar resultados masivos

---

### Port: `IProductRepository`

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.entities.product import Product


@runtime_checkable
class IProductRepository(Protocol):
    """Protocol for product persistence and querying."""

    async def create(self, product: Product) -> Product:
        """Persists a new product.

        Args:
            product: Product to persist (no id assigned).

        Returns:
            Product: The same product with id populated after persistence.
        """
        ...

    async def get_by_id(self, product_id: int) -> Product | None:
        """Retrieves a product by its ID.

        Args:
            product_id: Technical identifier of the product.

        Returns:
            Product | None: The product if it exists, None otherwise.
        """
        ...

    async def get_by_sku(self, sku: str) -> Product | None:
        """Retrieves a product by its SKU.

        Args:
            sku: Business identifier of the product.

        Returns:
            Product | None: The product if it exists, None otherwise.
        """
        ...

    async def list_all(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Product]:
        """Lists all products with pagination.

        Args:
            limit: Maximum number of products to return.
            offset: Number of products to skip (pagination).

        Returns:
            list[Product]: List of products.
        """
        ...

    async def list_below_threshold(self) -> list[Product]:
        """Lists products with current stock below the minimum threshold.

        This query requires calculating the current stock for each product
        (sum of movements) and comparing it with their min_stock_threshold.

        Returns:
            list[Product]: Products with stock below the threshold.
        """
        ...
```

**Design Notes:**
- `list_below_threshold()` is a complex query requiring join with movements
- `get_by_sku()` uses SKU as string (not the VO) to simplify the infrastructure layer
- Consistent pagination with `IMovementRepository` (limit/offset)

---

### Port: `ICategoryRepository`

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.entities.category import Category


@runtime_checkable
class ICategoryRepository(Protocol):
    """Protocol for category persistence and querying."""

    async def create(self, category: Category) -> Category:
        """Persists a new category.

        Args:
            category: Category to persist (no id assigned).

        Returns:
            Category: The same category with id populated after persistence.
        """
        ...

    async def get_by_id(self, category_id: int) -> Category | None:
        """Retrieves a category by its ID.

        Args:
            category_id: Technical identifier of the category.

        Returns:
            Category | None: The category if it exists, None otherwise.
        """
        ...

    async def list_all(self) -> list[Category]:
        """Lists all categories.

        Returns:
            list[Category]: List of all categories.
        """
        ...
```

**Design Notes:**
- No pagination in `list_all()` — a small number of categories is expected
- No `get_by_name()` — name is UNIQUE but ID lookup is sufficient

---

### Port: `IStockQueryRepository`

```python
from __future__ import annotations

from datetime import datetime

from typing import Protocol, runtime_checkable


@runtime_checkable
class IStockQueryRepository(Protocol):
    """Protocol for analytical stock queries.

    Separated from IMovementRepository (Interface Segregation Principle).
    Stock queries are read operations that can use
    materialized views, CTEs, or direct calculations depending on implementation.
    """

    async def get_current_stock(self, product_id: int) -> float:
        """Calculates the current stock of a product.

        Sums all movements for the product:
        - IN: +quantity
        - OUT: -quantity
        - ADJUSTMENT: +quantity
        - TRANSFER: -quantity (from origin perspective)

        Args:
            product_id: Product identifier.

        Returns:
            float: Current stock of the product (0.0 if no movements).

        Note:
            Resolution F3-Q1: return type is `float` for compatibility
            with the implementation in SPEC-30/31 (materialized view + asyncpg).
            Changed from `int` to `float` to match actual code.
        """
        ...

    async def get_stock_at_date(
        self,
        product_id: int,
        date: datetime,
    ) -> float:
        """Calculates the stock of a product on a specific date.

        Only considers movements where created_at <= date.

        Args:
            product_id: Product identifier.
            date: Reference date/time (timezone-aware).

        Returns:
            float: Product stock on the specified date (0.0 if no prior movements).
        """
        ...
```

**Design Notes:**
- Separated from `IMovementRepository` — ISP: analytical queries vs. movement CRUD
- Returns `float` (not entities) — these are aggregation queries (resolution F3-Q1)
- `get_stock_at_date()` is the main query for the <100ms historical stock objective
- Implementation can use materialized views or direct calculation based on performance

---

## Files

| File | Description |
|------|-------------|
| `src/domain/ports/movement_repository.py` | `IMovementRepository` Protocol |
| `src/domain/ports/product_repository.py` | `IProductRepository` Protocol |
| `src/domain/ports/category_repository.py` | `ICategoryRepository` Protocol |
| `src/domain/ports/stock_query_repository.py` | `IStockQueryRepository` Protocol |
| `src/domain/ports/__init__.py` | Re-exports: all protocols |

---

## Acceptance Criteria

- [ ] All ports use `typing.Protocol` with `@runtime_checkable`
- [ ] No `abc.ABC` or `@abstractmethod` in `domain/ports/`
- [ ] Repository methods are `async` (return coroutines)
- [ ] `IMovementRepository` has no `update` or `delete` methods (immutability enforced)
- [ ] `IProductRepository.list_below_threshold` exists for low-stock alerts
- [ ] `IStockQueryRepository` is separate from `IMovementRepository` (ISP separation)
- [ ] `domain/ports/` imports only from `domain/` (entities, value_objects, exceptions)
- [ ] `make lint` passes with zero errors on all port files
- [ ] Unit tests can create mock implementations satisfying each Protocol at runtime

---

## Open Questions

1. Should `IStockQueryRepository` also include `get_stock_for_multiple_products(product_ids: list[int]) -> dict[int, int]` for batch queries?
2. Should `IProductRepository.list_below_threshold()` return a tuple `(Product, current_stock)` instead of just `Product`?
3. Should `IMovementRepository.list_by_product()` accept an optional `movement_type` filter?
