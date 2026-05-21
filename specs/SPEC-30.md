# SPEC-30: Repository Implementation

**Phase:** F3 — Data Adapters  
**Dependencies:** Spec-12 (Indexes) ✅ Completed, Spec-22 (Protocols) ✅ Completed  
**Priority:** High  
**Status:** Pending  

---

## Objective

Implement the concrete adapters for the 4 domain ports using `asyncpg` with explicit SQL, positional parameters (`$1`, `$2`) and Row→Entity mapping via pure functions. **No ORM** — full control over queries and execution plans.

**Design principles:**
- **Explicit SQL** — each method contains its readable SQL query, no hidden abstractions
- **Positional parameters** — `$1`, `$2`, etc. Never string concatenation (SQL injection)
- **Mappers as pure functions** — `asyncpg.Record` → domain entity transformation, separated from the repository
- **asyncpg handles JSONB natively** — do not use `json.dumps()` for `metadata` parameters
- **BasePostgresRepository** — abstract class centralizes `__init__` and `_get_conn()` for DRY
- **Interface Segregation** — each repository implements its domain-specific protocol

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| Explicit inline SQL | Full control over `EXPLAIN ANALYZE`, no ORM hiding the plan |
| Positional parameters `$N` | SQL injection prevention, query caching performance |
| Mappers as pure functions | Isolated testable, stateless, deterministic |
| Abstract `BasePostgresRepository` | DRY: centralizes `__init__` and `_get_conn()` — 4 repos share the same logic |
| asyncpg handles JSONB natively | Do not use `json.dumps()` for `metadata` — asyncpg converts `dict` to JSONB automatically |
| No pagination in `list_all()` for categories | A small set was expected (<100). **As of v1.0.0:** `list_all()` now accepts `limit` and `offset` with `LIMIT $1 OFFSET $2` in SQL to avoid fetching all rows into memory. |

---

## Mappers (`src/infrastructure/repositories/mappers.py`)

Pure functions that transform `asyncpg.Record` into domain entities.

### `map_category_row(record) -> Category`

```python
from datetime import datetime
from src.domain.entities.category import Category


def map_category_row(record) -> Category:
    """Transforms an asyncpg.Record into a Category entity.

    Args:
        record: asyncpg.Record with columns id, name, description, created_at.

    Returns:
        Category with fields mapped from the database row.

    Example::

        row = await pool.fetchrow("SELECT * FROM categories WHERE id = $1", 1)
        category = map_category_row(row)
    """
    return Category(
        id=record["id"],
        name=record["name"],
        description=record["description"],
        created_at=record["created_at"],
    )
```

### `map_product_row(record) -> Product`

```python
from datetime import datetime
from src.domain.entities.product import Product
from src.domain.value_objects.sku import SKU


def map_product_row(record) -> Product:
    """Transforms an asyncpg.Record into a Product entity.

    Builds the SKU Value Object from the string stored in DB.

    Args:
        record: asyncpg.Record with columns id, sku, name, description,
                unit_of_measure, category_id, min_stock_threshold, created_at.

    Returns:
        Product with SKU as Value Object.

    Raises:
        InvalidSKUError: If the SKU in DB does not meet format rules.
    """
    return Product(
        id=record["id"],
        sku=SKU(record["sku"]),
        name=record["name"],
        description=record["description"],
        unit_of_measure=record["unit_of_measure"],
        category_id=record["category_id"],
        min_stock_threshold=record["min_stock_threshold"],
        created_at=record["created_at"],
    )
```

### `map_movement_row(record) -> Movement`

```python
import json
import logging
from typing import Any
from src.domain.entities.movement import Movement
from src.domain.value_objects.movement_type import MovementType
from src.domain.value_objects.quantity import Quantity

logger = logging.getLogger(__name__)


def map_movement_row(record) -> Movement:
    """Transforms an asyncpg.Record into a Movement entity.

    Parses the movement_type string to the MovementType Enum and builds
    the Quantity Value Object from the stored integer.

    Args:
        record: asyncpg.Record with columns id, product_id, movement_type,
                quantity, metadata, reference, created_at.

    Returns:
        Movement with correct domain types.

    Raises:
        ValueError: If movement_type is not a valid Enum value.
        InvalidQuantityError: If quantity <= 0 (should not occur with CHECK constraint).
    """
    metadata_raw = record["metadata"]
    if metadata_raw is None:
        metadata: dict[str, object] = {}
    elif isinstance(metadata_raw, dict):
        metadata = metadata_raw
    else:
        try:
            metadata = json.loads(metadata_raw)
        except json.JSONDecodeError:
            logger.warning(
                "Corrupted metadata for movement id=%s, defaulting to empty dict",
                record.get("id"),
            )
            metadata = {}

    return Movement(
        id=record["id"],
        product_id=record["product_id"],
        movement_type=MovementType(record["movement_type"]),
        quantity=Quantity(record["quantity"]),
        metadata=metadata,
        reference=record["reference"],
        created_at=record["created_at"],
    )
```

---

## Repositories

> **Note F3-hardening:** All repositories inherit from `BasePostgresRepository`
> (abstract class in `src/infrastructure/repositories/base_repository.py`).
> `BasePostgresRepository` centralizes `__init__(pool, connection)` and `_get_conn()`.
> The examples below show the full pattern for reference;
> in the actual implementation, repos delegate `__init__` and `_get_conn` to the base class.

### `BasePostgresRepository` (abstract)

```python
class BasePostgresRepository:
    """Base class for repositories using asyncpg."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        connection: asyncpg.Connection | None = None,
    ) -> None:
        self._pool = pool
        self._connection = connection

    def _get_conn(self) -> asyncpg.Pool | asyncpg.Connection:
        """Returns the active connection or the pool."""
        return self._connection if self._connection else self._pool
```

### `PostgresMovementRepository`

Implements `IMovementRepository` from the domain.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

import asyncpg

from src.domain.entities.movement import Movement
from src.domain.ports.movement_repository import IMovementRepository
from src.infrastructure.repositories.mappers import map_movement_row

if TYPE_CHECKING:
    pass


class PostgresMovementRepository(IMovementRepository):
    """Movement repository with asyncpg and explicit SQL.

    Does not include update() or delete() — movements are immutable.
    Supports shared connection for Unit of Work transactions.

    Usage example without transaction::

        repo = PostgresMovementRepository(pool)
        movement = await repo.create(movement_entity)

    Usage example with Unit of Work::

        async with PostgresUnitOfWork(pool) as uow:
            repo = PostgresMovementRepository(pool, connection=uow.connection)
            movement = await repo.create(movement_entity)
    """

    _CREATE_SQL = """
        INSERT INTO movements (product_id, movement_type, quantity, metadata, reference, created_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, product_id, movement_type, quantity, metadata, reference, created_at
    """

    _GET_BY_ID_SQL = """
        SELECT id, product_id, movement_type, quantity, metadata, reference, created_at
        FROM movements
        WHERE id = $1
    """

    _LIST_BY_PRODUCT_SQL = """
        SELECT id, product_id, movement_type, quantity, metadata, reference, created_at
        FROM movements
        WHERE product_id = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        connection: asyncpg.Connection | None = None,
    ) -> None:
        """Initializes the repository with pool and optional connection.

        Args:
            pool: asyncpg connection pool (required).
            connection: Active connection for transactions (optional).
                        If None, the pool is used directly.
        """
        self._pool = pool
        self._connection = connection

    def _get_conn(self) -> asyncpg.Pool | asyncpg.Connection:
        """Returns the active connection or the pool."""
        return self._connection if self._connection else self._pool

    async def create(self, movement: Movement) -> Movement:
        """Persists a new movement and returns the entity with assigned id."""
        row = await self._get_conn().fetchrow(
            self._CREATE_SQL,
            movement.product_id,
            movement.movement_type.value,
            movement.quantity.value,
            movement.metadata,
            movement.reference,
            movement.created_at,
        )
        return map_movement_row(row)

    async def get_by_id(self, movement_id: int) -> Movement | None:
        """Retrieves a movement by its ID."""
        row = await self._get_conn().fetchrow(self._GET_BY_ID_SQL, movement_id)
        if row is None:
            return None
        return map_movement_row(row)

    async def list_by_product(
        self,
        product_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Movement]:
        """Lists movements for a product with pagination."""
        rows = await self._get_conn().fetch(
            self._LIST_BY_PRODUCT_SQL, product_id, limit, offset
        )
        return [map_movement_row(r) for r in rows]
```

---

### `PostgresProductRepository`

Implements `IProductRepository` from the domain.

```python
class PostgresProductRepository(IProductRepository):
    """Product repository with asyncpg and explicit SQL."""

    _CREATE_SQL = """
        INSERT INTO products (sku, name, description, unit_of_measure, category_id, min_stock_threshold, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING id, sku, name, description, unit_of_measure, category_id, min_stock_threshold, created_at
    """

    _GET_BY_ID_SQL = """
        SELECT id, sku, name, description, unit_of_measure, category_id, min_stock_threshold, created_at
        FROM products
        WHERE id = $1
    """

    _GET_BY_SKU_SQL = """
        SELECT id, sku, name, description, unit_of_measure, category_id, min_stock_threshold, created_at
        FROM products
        WHERE sku = $1
    """

    _LIST_ALL_SQL = """
        SELECT id, sku, name, description, unit_of_measure, category_id, min_stock_threshold, created_at
        FROM products
        ORDER BY id
        LIMIT $1 OFFSET $2
    """

    _LIST_BELOW_THRESHOLD_SQL = """
        SELECT p.id, p.sku, p.name, p.description, p.unit_of_measure,
               p.category_id, p.min_stock_threshold, p.created_at
        FROM products p
        LEFT JOIN movements m ON m.product_id = p.id
        GROUP BY p.id
        HAVING COALESCE(
            SUM(
                CASE m.movement_type
                    WHEN 'IN' THEN m.quantity
                    WHEN 'OUT' THEN -m.quantity
                    WHEN 'ADJUSTMENT' THEN m.quantity
                    WHEN 'TRANSFER' THEN -m.quantity
                    ELSE 0
                END
            ), 0
        ) < p.min_stock_threshold
        LIMIT $1
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        connection: asyncpg.Connection | None = None,
    ) -> None:
        self._pool = pool
        self._connection = connection

    def _get_conn(self) -> asyncpg.Pool | asyncpg.Connection:
        return self._connection if self._connection else self._pool

    async def create(self, product: Product) -> Product:
        row = await self._get_conn().fetchrow(
            self._CREATE_SQL,
            product.sku.value,
            product.name,
            product.description,
            product.unit_of_measure,
            product.category_id,
            product.min_stock_threshold,
            product.created_at,
        )
        return map_product_row(row)

    async def get_by_id(self, product_id: int) -> Product | None:
        row = await self._get_conn().fetchrow(self._GET_BY_ID_SQL, product_id)
        return map_product_row(row) if row else None

    async def get_by_sku(self, sku: str) -> Product | None:
        row = await self._get_conn().fetchrow(self._GET_BY_SKU_SQL, sku)
        return map_product_row(row) if row else None

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[Product]:
        rows = await self._get_conn().fetch(self._LIST_ALL_SQL, limit, offset)
        return [map_product_row(r) for r in rows]

    async def list_below_threshold(self, *, limit: int = 100) -> list[Product]:
        rows = await self._get_conn().fetch(self._LIST_BELOW_THRESHOLD_SQL, limit)
        return [map_product_row(r) for r in rows]
```

---

### `PostgresCategoryRepository` (updated v1.0.0)

Implements `ICategoryRepository` from the domain. **As of v1.0.0, `list_all()` accepts `limit` and `offset` for database pagination.**

```python
class PostgresCategoryRepository(ICategoryRepository):
    """Category repository with asyncpg and explicit SQL."""

    _CREATE_SQL = """
        INSERT INTO categories (name, description, created_at)
        VALUES ($1, $2, $3)
        RETURNING id, name, description, created_at
    """

    _GET_BY_ID_SQL = """
        SELECT id, name, description, created_at
        FROM categories
        WHERE id = $1
    """

    _LIST_ALL_SQL = """
        SELECT id, name, description, created_at
        FROM categories
        ORDER BY name
        LIMIT $1 OFFSET $2
    """

    # ... __init__, _get_conn, create, get_by_id inherited from BasePostgresRepository ...

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Category]:
        """Lists categories with database pagination."""
        rows = await self._get_conn().fetch(self._LIST_ALL_SQL, limit, offset)
        return [map_category_row(r) for r in rows]
```

---

### `PostgresStockQueryRepository`

Implements `IStockQueryRepository` from the domain. Uses **direct calculation** from the `movements` table (no materialized view — optimization added in Spec-31).

```python
from datetime import datetime


class PostgresStockQueryRepository(IStockQueryRepository):
    """Stock query repository with direct calculation from movements.

    Uses SQL with CASE/SUM to calculate stock. In Spec-31 it will be optimized
    with the materialized view mv_stock_historical.
    """

    _CURRENT_STOCK_SQL = """
        SELECT COALESCE(
            SUM(
                CASE movement_type
                    WHEN 'IN' THEN quantity
                    WHEN 'OUT' THEN -quantity
                    WHEN 'ADJUSTMENT' THEN quantity
                    WHEN 'TRANSFER' THEN -quantity
                    ELSE 0
                END
            ), 0
        ) AS stock
        FROM movements
        WHERE product_id = $1
    """

    _STOCK_AT_DATE_SQL = """
        SELECT COALESCE(
            SUM(
                CASE movement_type
                    WHEN 'IN' THEN quantity
                    WHEN 'OUT' THEN -quantity
                    WHEN 'ADJUSTMENT' THEN quantity
                    WHEN 'TRANSFER' THEN -quantity
                    ELSE 0
                END
            ), 0
        ) AS stock
        FROM movements
        WHERE product_id = $1
          AND created_at <= $2
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        connection: asyncpg.Connection | None = None,
    ) -> None:
        self._pool = pool
        self._connection = connection

    def _get_conn(self) -> asyncpg.Pool | asyncpg.Connection:
        return self._connection if self._connection else self._pool

    async def get_current_stock(self, product_id: int) -> float:
        """Calculates current stock by summing all product movements."""
        row = await self._get_conn().fetchrow(self._CURRENT_STOCK_SQL, product_id)
        return float(row["stock"]) if row else 0.0

    async def get_stock_at_date(self, product_id: int, date: datetime) -> float:
        """Calculates stock at a specific date."""
        row = await self._get_conn().fetchrow(self._STOCK_AT_DATE_SQL, product_id, date)
        return float(row["stock"]) if row else 0.0
```

---

## Files

| File | Description |
|------|-------------|
| `src/infrastructure/repositories/base_repository.py` | `BasePostgresRepository` — abstract class with shared `__init__` and `_get_conn()` |
| `src/infrastructure/repositories/mappers.py` | Pure functions: `map_category_row`, `map_product_row`, `map_movement_row` (with `JSONDecodeError` handling) |
| `src/infrastructure/repositories/movement_repository.py` | `PostgresMovementRepository` (inherits `BasePostgresRepository`) |
| `src/infrastructure/repositories/product_repository.py` | `PostgresProductRepository` (inherits `BasePostgresRepository`) |
| `src/infrastructure/repositories/category_repository.py` | `PostgresCategoryRepository` (inherits `BasePostgresRepository`) |
| `src/infrastructure/repositories/stock_query_repository.py` | `PostgresStockQueryRepository` (inherits `BasePostgresRepository`) |
| `src/infrastructure/repositories/__init__.py` | Re-exports: all repositories and mappers |

---

## Acceptance Criteria

- [ ] The 4 repositories implement their respective protocols (verifiable with `isinstance(repo, Protocol)` at runtime)
- [ ] All repositories inherit from `BasePostgresRepository` (no duplicated `__init__` or `_get_conn()`)
- [ ] All SQL uses positional parameters (`$1`, `$2`) — zero string concatenation
- [ ] Mappers are pure functions (stateless, no I/O, isolated testable)
- [ ] `map_movement_row` handles `JSONDecodeError` on corrupted metadata (fallback to `{}` with warning log)
- [ ] **No** `json.dumps()` used for JSONB parameters — asyncpg handles `dict → JSONB` natively
- [ ] Constructor accepts optional `connection` for Unit of Work integration (Spec-32)
- [ ] `PostgresMovementRepository` **does not** have `update()` or `delete()` methods
- [ ] Integration tests with `testcontainers.postgres` validate: CRUD, pagination, stock calculation, type mapping
- [ ] `make lint` passes without errors on all repository files

---

## Testing Strategy

- **Integration tests only** with `testcontainers.postgres` — validates real SQL against PostgreSQL 16
- Existing `db_pool` fixture in `tests/integration/` is reused
- For each repository: test `create()`, `get_by_id()`, `list_*()`, and edge cases (not found, empty pagination)
- Isolated mapper tests: validate that simulated `asyncpg.Record` transforms correctly
- `list_below_threshold`: insert movements that bring stock below threshold and verify it appears in the list

---

## Resolved Questions

1. **Does `get_current_stock()` return `int` or `float`?** → **`float`**. The `IStockQueryRepository` port defines `float` as the return type. Maintain compatibility with the existing contract (F2). The implementation explicitly converts with `float(row["stock"])`. If an `int` port is needed in the future, a separate method can be added without breaking this contract.

2. **Add batch method `get_stock_for_multiple_products()`?** → **Not in F3 (YAGNI).** There is no current use case that requires it. F4 repositories can perform individual queries. If a real bottleneck is identified in F5/F6, it can be added without breaking the existing API.

3. **Do mappers validate entities or assume valid DB?** → **Assume valid DB with type validation.** The database has CHECK constraints, FKs, and an immutability trigger that protect integrity. Mappers only transform types (`string → Enum`, `int → Quantity VO`). If a value does not match (e.g., unrecognized `movement_type` in Enum), the native exception is raised (`ValueError`). If the SKU has an invalid format, `SKU()` raises `InvalidSKUError`. Mappers do not validate business invariants — that is the responsibility of entities and the domain layer.
