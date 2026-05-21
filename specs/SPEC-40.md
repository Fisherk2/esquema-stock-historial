# SPEC-40: Use Cases (Application)

**Phase:** F4 — API Layer (Use Cases + Endpoints)  
**Dependencies:** Spec-21 (Business Rules) ✅ Completed, Spec-22 (Protocols) ✅ Completed, Spec-32 (Unit of Work) ✅ Completed  
**Priority:** High  
**Status:** Pending  

---

## Objective

Implement the 6 use cases of the application layer that orchestrate domain business rules with infrastructure repositories. Each use case is a class with a single `execute()` method that follows the **Single Responsibility Principle**: one business operation per class.

**Design principles:**
- **Use cases as classes** — allows dependency injection in `__init__`, testable with mocks, immutable state
- **Single public `execute()` method** — strict SRP, single entry point per use case
- **Protocol Injection** — the constructor receives interfaces (`IMovementRepository`, etc.), not concrete implementations. Pure DIP.
- **Zero imports from `infrastructure/`** — the application layer only imports from `domain/` (ports, entities, exceptions, rules)
- **Domain exceptions propagate** — use cases do NOT catch `DomainError` or its subclasses. The adapter (Spec-42) maps them to HTTP.
- **UoW for atomicity** — `RecordMovementUseCase` uses `IUnitOfWork` to verify stock and create movement in a single transaction

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| Classes with `execute()` (not functions) | Enables DI in constructor, immutable state, mocking in testing, and dependency composition |
| Protocols in `__init__`, not in `execute()` | Dependencies are fixed per use case; injecting them in `execute()` would violate DIP and make testing difficult |
| `RecordMovementUseCase` uses UoW | Verifying stock + creating movement must be atomic; if the check passes but the create fails, there should be no inconsistency |
| Stock validation INSIDE the use case | The use case is the orchestrator; the `validate_stock_not_negative()` rule requires domain context that the repository does not have |
| Domain exceptions uncaptured | Use cases know nothing about HTTP; catching here would couple application with adapters. The middleware (Spec-42) maps |
| `ListProductsUseCase` exists as a class | Although it is a passthrough to the repository, wrapping it allows adding future logic (filtering, caching, authorization) without changing the API |

---

## Use Cases

### 1. `RecordMovementUseCase`

The most complex use case. Orchestrates product verification, stock validation, metadata consistency, and atomic persistence of the movement.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.exceptions.domain_error import DomainError
from src.domain.ports.movement_repository import IMovementRepository
from src.domain.ports.product_repository import IProductRepository
from src.domain.ports.stock_query_repository import IStockQueryRepository
from src.domain.ports.unit_of_work import IUnitOfWork
from src.domain.rules.stock_validation import validate_stock_not_negative

if TYPE_CHECKING:
    from datetime import datetime

    from src.domain.entities.movement import Movement
    from src.domain.value_objects.movement_type import MovementType


class RecordMovementUseCase:
    """Registers a new stock movement atomically.

    Flow:
        1. Verify that the product exists.
        2. If the movement type is OUT or TRANSFER:
           a. Query current stock of the product.
           b. Validate that stock does not become negative.
        3. Build the Movement entity (metadata validation in
           ``__post_init__`` — TRANSFER requires origin/destination,
           ADJUSTMENT requires reason).
        4. Persist within a transaction (UoW).
        5. Return the persisted movement.

    Args:
        movement_repo: Movement repository.
        product_repo: Product repository.
        stock_query_repo: Stock query repository.
        unit_of_work: Unit of Work for atomic transactions.
    """

    def __init__(
        self,
        movement_repo: IMovementRepository,
        product_repo: IProductRepository,
        stock_query_repo: IStockQueryRepository,
        unit_of_work: IUnitOfWork,
    ) -> None:
        self._movement_repo = movement_repo
        self._product_repo = product_repo
        self._stock_query_repo = stock_query_repo
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        product_id: int,
        movement_type: MovementType,
        quantity: int | float,
        metadata: dict[str, Any],
        reference: str | None = None,
    ) -> Movement:
        """Executes the movement recording use case.

        Args:
            product_id: ID of the product affected by the movement.
            movement_type: Movement type (IN, OUT, ADJUSTMENT, TRANSFER).
            quantity: Positive quantity of units.
            metadata: Contextual dictionary (required for TRANSFER and ADJUSTMENT).
            reference: Optional external reference (order, note, etc.).

        Returns:
            Movement: The persisted movement entity with assigned id.

        Raises:
            ValueError: If the product does not exist.
            ValueError: If the metadata is inconsistent with the movement type.
            InsufficientStockError: If the movement would result in negative stock.
            InvalidQuantityError: If quantity <= 0 (validated by the Quantity VO).

        Example::

            use_case = RecordMovementUseCase(movement_repo, product_repo, stock_repo, uow)
            movement = await use_case.execute(
                product_id=1,
                movement_type=MovementType.IN,
                quantity=10,
                metadata={"supplier": "ACME"},
                reference="PO-12345",
            )
        """
        # 1. Verify that the product exists
        product = await self._product_repo.get_by_id(product_id)
         if product is None:
             raise ProductNotFoundError(product_id)

        # 2. For movements that reduce stock, validate that it does not become negative
        if movement_type in (MovementType.OUT, MovementType.TRANSFER):
            # Query current stock within the same transaction
            current_stock = await self._stock_query_repo.get_current_stock(product_id)
            validate_stock_not_negative(movement_type, quantity, current_stock, product_id)

        # 3. Build and persist within UoW
        # (Metadata validation executes in Movement.__post_init__)
        from datetime import UTC, datetime

        from src.domain.entities.movement import Movement

        movement = Movement(
            id=None,
            product_id=product_id,
            movement_type=movement_type,
            quantity=Quantity(quantity),
            metadata=metadata,
            reference=reference,
            created_at=datetime.now(tz=UTC),
        )

        async with self._unit_of_work as uow:
            # Re-validate stock within the transaction to avoid race conditions
            # Uses get_current_stock_with_lock (SELECT FOR UPDATE) to
            # serialize concurrent transactions of the same product.
            # The MV may be stale; calculate directly within the lock.
            if movement_type in (MovementType.OUT, MovementType.TRANSFER):
                current_stock = await self._stock_query_repo.get_current_stock_with_lock(product_id)
                validate_stock_not_negative(movement_type, quantity, current_stock)

            result = await self._movement_repo.create(movement)

        return result
```

**Design Notes:**
- Stock validation runs **twice**: before the UoW (fail-fast without acquiring a connection) and inside the UoW (protection against race conditions)
- **Inside the UoW, `get_current_stock_with_lock()` is used** which executes `SELECT ... FOR UPDATE` + direct calculation from the `movements` table (not the MV). This serializes concurrent transactions of the same product, preventing two simultaneous OUT/TRANSFER movements from reading the same stale stock from the MV and both passing validation.
- Metadata validation executes in `Movement.__post_init__` when building the entity — **single source of truth** (SPEC-21). The use case does NOT call `validate_movement_type_consistency` directly. If metadata is inconsistent, `ValueError` is raised from the constructor and translated to HTTP 400.
- The UoW guarantees that if `create()` fails (FK violation, constraint), everything is rolled back
- `RecordMovementUseCase` is the only use case that uses UoW; the others are individual operations

---

### 2. `QueryCurrentStockUseCase`

Queries the current stock of a product. Simple, no transaction.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.ports.stock_query_repository import IStockQueryRepository

if TYPE_CHECKING:
    pass


class QueryCurrentStockUseCase:
    """Queries the current stock of a product.

    Args:
        stock_query_repo: Stock query repository.
    """

    def __init__(
        self,
        stock_query_repo: IStockQueryRepository,
    ) -> None:
        self._stock_query_repo = stock_query_repo

    async def execute(self, product_id: int) -> float:
        """Executes the current stock query.

        Args:
            product_id: Product ID.

        Returns:
            float: Current stock of the product (0 if it has no movements).

        Example::

            use_case = QueryCurrentStockUseCase(stock_repo)
            stock = await use_case.execute(product_id=1)  # 42.0
        """
        return await self._stock_query_repo.get_current_stock(product_id)
```

**Design Notes:**
- Pure read operation — does not require UoW
- The repository already implements the MV + fallback strategy (Spec-31)

---

### 3. `QueryStockAtDateUseCase`

Queries the stock of a product at a specific historical date.

```python
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.domain.ports.stock_query_repository import IStockQueryRepository

if TYPE_CHECKING:
    pass


class QueryStockAtDateUseCase:
    """Queries the stock of a product at a historical date.

    Args:
        stock_query_repo: Stock query repository.
    """

    def __init__(
        self,
        stock_query_repo: IStockQueryRepository,
    ) -> None:
        self._stock_query_repo = stock_query_repo

    async def execute(self, product_id: int, date: datetime) -> float:
        """Executes the historical stock query.

        Args:
            product_id: Product ID.
            date: Reference date/time (timezone-aware).

        Returns:
            float: Stock of the product at the date (0 if there are no prior movements).

        Example::

            from datetime import datetime, timezone
            use_case = QueryStockAtDateUseCase(stock_repo)
            stock = await use_case.execute(
                product_id=1,
                date=datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            )  # 15.0
        """
        return await self._stock_query_repo.get_stock_at_date(product_id, date)
```

**Design Notes:**
- Always uses direct calculation on `movements` (the materialized view only has current stock)
- The date must be timezone-aware — the caller (router/DTO) must guarantee this

---

### 4. `CreateProductUseCase`

Creates a new product, verifying that the category exists.

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.domain.entities.product import Product
from src.domain.ports.category_repository import ICategoryRepository
from src.domain.ports.product_repository import IProductRepository
from src.domain.value_objects.sku import SKU

if TYPE_CHECKING:
    pass


class CreateProductUseCase:
    """Creates a new product in the inventory.

    Flow:
        1. Verify that the category exists.
        2. Build the Product entity (with SKU VO).
        3. Persist and return.

    Args:
        product_repo: Product repository.
        category_repo: Category repository.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        category_repo: ICategoryRepository,
    ) -> None:
        self._product_repo = product_repo
        self._category_repo = category_repo

    async def execute(
        self,
        sku: str,
        name: str,
        unit_of_measure: str,
        category_id: int,
        description: str | None = None,
        min_stock_threshold: int = 0,
    ) -> Product:
        """Executes the creation of a product.

        Args:
            sku: Product SKU code.
            name: Product name (non-empty).
            unit_of_measure: Unit of measure (e.g., "unit", "kg").
            category_id: ID of the category it belongs to.
            description: Optional description.
            min_stock_threshold: Minimum stock threshold (default 0).

        Returns:
            Product: The persisted product with assigned id.

        Raises:
            ValueError: If the category does not exist.
            InvalidSKUError: If the SKU does not match the required pattern.
            ValueError: If name or unit_of_measure are empty.

        Example::

            use_case = CreateProductUseCase(product_repo, category_repo)
            product = await use_case.execute(
                sku="PROD-001",
                name="Widget A",
                unit_of_measure="unit",
                category_id=1,
                description="Test widget",
                min_stock_threshold=10,
            )
        """
        # 1. Verify that the category exists
        category = await self._category_repo.get_by_id(category_id)
        if category is None:
            raise ValueError(f"Category {category_id} not found")

        # 2. Build and persist
        product = Product(
            id=None,
            sku=SKU(sku),
            name=name,
            description=description,
            unit_of_measure=unit_of_measure,
            category_id=category_id,
            min_stock_threshold=min_stock_threshold,
            created_at=datetime.now(tz=UTC),
        )

        return await self._product_repo.create(product)
```

**Design Notes:**
- Category verification uses the repository directly (does not need UoW because it is read-only)
- The `Product` constructor already validates `name`, `unit_of_measure`, and `min_stock_threshold` in `__post_init__`
- `SKU(sku)` raises `InvalidSKUError` if the format is invalid

---

### 5. `ListProductsUseCase`

Lists products with pagination. Passthrough to the repository, but wrapped for architectural consistency.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.ports.product_repository import IProductRepository

if TYPE_CHECKING:
    from src.domain.entities.product import Product


class ListProductsUseCase:
    """Lists inventory products with pagination.

    Args:
        product_repo: Product repository.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
    ) -> None:
        self._product_repo = product_repo

    async def execute(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Product]:
        """Executes the product listing.

        Args:
            limit: Maximum number of results (default 100).
            offset: Offset for pagination (default 0).

        Returns:
            list[Product]: List of products ordered by ID.

        Example::

            use_case = ListProductsUseCase(product_repo)
            products = await use_case.execute(limit=50, offset=0)
        """
        return await self._product_repo.list_all(limit=limit, offset=offset)
```

**Design Notes:**
- Currently a passthrough to the repository, but wrapping it allows adding future logic (filtering by category, searching by name, caching) without changing the adapter API
- Maintains consistency: all read endpoints go through a use case

---

### 6. `CreateCategoryUseCase`

Creates a new product category.

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.domain.entities.category import Category
from src.domain.ports.category_repository import ICategoryRepository

if TYPE_CHECKING:
    pass


class CreateCategoryUseCase:
    """Creates a new product category.

    Args:
        category_repo: Category repository.
    """

    def __init__(
        self,
        category_repo: ICategoryRepository,
    ) -> None:
        self._category_repo = category_repo

    async def execute(
        self,
        name: str,
        description: str | None = None,
    ) -> Category:
        """Executes the creation of a category.

        Args:
            name: Category name (non-empty).
            description: Optional description.

        Returns:
            Category: The persisted category with assigned id.

        Raises:
            ValueError: If name is empty.

        Example::

            use_case = CreateCategoryUseCase(category_repo)
            category = await use_case.execute(
                name="Electronics",
                description="Electronic products",
            )
        """
        category = Category(
            id=None,
            name=name,
            description=description,
            created_at=datetime.now(tz=UTC),
        )

        return await self._category_repo.create(category)
```

**Design Notes:**
- The `Category` entity already validates non-empty `name` in `__post_init__`
- Simple operation, does not require UoW (single insert)

---

## Files

| File | Description |
|------|-------------|
| `src/application/use_cases/record_movement.py` | `RecordMovementUseCase` — creates movement with stock validation |
| `src/application/use_cases/query_current_stock.py` | `QueryCurrentStockUseCase` — current stock |
| `src/application/use_cases/query_stock_at_date.py` | `QueryStockAtDateUseCase` — historical stock |
| `src/application/use_cases/create_product.py` | `CreateProductUseCase` — creates product with category verification |
| `src/application/use_cases/list_products.py` | `ListProductsUseCase` — lists with pagination |
| `src/application/use_cases/create_category.py` | `CreateCategoryUseCase` — creates category |
| `src/application/use_cases/__init__.py` | Re-exports: all 6 use cases |

---

## Acceptance Criteria

- [ ] All 6 use cases implement a single public method `async execute()`
- [ ] All use cases inject Protocols in `__init__` (not concrete implementations)
- [ ] `RecordMovementUseCase` verifies that the product exists before creating the movement
- [ ] `RecordMovementUseCase` validates non-negative stock for OUT and TRANSFER (twice: fail-fast + inside UoW)
- [ ] `RecordMovementUseCase` validates metadata consistency for TRANSFER and ADJUSTMENT
- [ ] `RecordMovementUseCase` uses `IUnitOfWork` for atomicity
- [ ] `CreateProductUseCase` verifies that the category exists before creating the product
- [ ] Use cases do NOT import from `infrastructure/` (only from `domain/` ports, entities, exceptions, rules)
- [ ] Domain exceptions (`InsufficientStockError`, `InvalidSKUError`, etc.) propagate without being caught
- [ ] `src/application/use_cases/__init__.py` exports all 6 use cases
- [ ] `make lint` passes without errors on all use case files

---

## Testing Strategy

- **Unit tests with mocks** — Each use case is tested in isolation with mocks of its Protocols. No real DB is used.
- **`RecordMovementUseCase`** — Tests parameterized by `MovementType`:
  - IN: creates without validating stock
  - OUT: validates stock, raises `InsufficientStockError` if insufficient
  - TRANSFER: validates stock + metadata (origin/destination)
  - ADJUSTMENT: validates metadata (reason)
  - Product not found: raises `ValueError`
- **`QueryCurrentStockUseCase`** — Delegates to repo mock, returns value
- **`QueryStockAtDateUseCase`** — Delegates to repo mock with date, returns value
- **`CreateProductUseCase`** — Category not found (`ValueError`), invalid SKU (`InvalidSKUError`), successful creation
- **`ListProductsUseCase`** — Empty list, list with items, pagination (limit/offset)
- **`CreateCategoryUseCase`** — Empty name (`ValueError`), successful creation
- Mock of `IUnitOfWork`: create a fake async context manager that simulates commit/rollback

---

## Resolved Questions

1. **How many use cases should Spec-40 define?** → **6 Use Cases.** `RecordMovementUseCase`, `QueryCurrentStockUseCase`, `QueryStockAtDateUseCase`, `CreateProductUseCase`, `ListProductsUseCase`, `CreateCategoryUseCase`. Covers the main domain operations without excessive granularity. `ListCategoriesUseCase` and `ListBelowThresholdUseCase` can be added in future phases if endpoints requiring them are identified.

2. **How should `RecordMovementUseCase` handle stock validation?** → **Inside the Use Case.** The use case queries `IStockQueryRepository.get_current_stock()`, applies `validate_stock_not_negative()`, and if it passes, creates the movement within an `IUnitOfWork` for atomicity. Validation runs twice: before the UoW (fail-fast without acquiring a connection) and inside the UoW (protection against race conditions between the check and the insert).

3. **Should `RecordMovementUseCase` use UoW for IN/ADJUSTMENT as well?** → **No.** Only for OUT and TRANSFER. IN and ADJUSTMENT always increment stock and cannot violate the negative stock invariant. Using UoW for all operations would add unnecessary overhead. If multi-repository atomicity is needed for IN/ADJUSTMENT in the future (e.g., create movement + update audit table), it can be added without breaking the existing pattern.

4. **Is `ListProductsUseCase` necessary or is it an unnecessary passthrough?** → **Yes, it is necessary.** Although currently a passthrough to the repository, wrapping it maintains architectural consistency: all read endpoints go through a use case. This allows adding future logic (filtering by category, searching by name, caching, authorization) without changing the adapter API. The cost of the wrapper is minimal (~15 lines class).
