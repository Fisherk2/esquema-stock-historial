# SPEC-30: Implementación Repositorio

**Fase:** F3 — Adaptadores de Datos  
**Dependencias:** Spec-12 (Índices) ✅ Completado, Spec-22 (Protocolos) ✅ Completado  
**Prioridad:** Alta  
**Estado:** Pendiente  

---

## Objective

Implementar los adaptadores concretos de los 4 ports del dominio usando `asyncpg` con SQL explícito, parámetros posicionales (`$1`, `$2`) y mapeo Row→Entity mediante funciones puras. **Sin ORM** — control total sobre queries y planes de ejecución.

**Principios de diseño:**
- **SQL explícito** — cada método contiene su query SQL legible, sin abstracciones ocultas
- **Parámetros posicionales** — `$1`, `$2`, etc. Nunca concatenación de strings (SQL injection)
- **Mappers como funciones puras** — transformación `asyncpg.Record` → entidad de dominio, separada del repositorio
- **asyncpg maneja JSONB nativamente** — no usar `json.dumps()` para parámetros `metadata`
- **BasePostgresRepository** — clase abstracta centraliza `__init__` y `_get_conn()` para DRY
- **Interface Segregation** — cada repositorio implementa su protocol específico del dominio

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| SQL explícito inline | Control total sobre `EXPLAIN ANALYZE`, sin ORM que oculte el plan |
| Parámetros posicionales `$N` | Prevención de SQL injection, performance de query caching |
| Mappers como funciones puras | Testeables aisladamente, sin estado, determinísticas |
| `BasePostgresRepository` abstracto | DRY: centraliza `__init__` y `_get_conn()` — 4 repos comparten la misma lógica |
| asyncpg maneja JSONB nativo | No usar `json.dumps()` para `metadata` — asyncpg convierte `dict` a JSONB automáticamente |
| Sin paginación en `list_all()` de categorías | Se esperaba un conjunto pequeño (<100). **Desde v1.0.2:** `list_all()` ahora acepta `limit` y `offset` con `LIMIT $1 OFFSET $2` en SQL para evitar fetch de todas las filas en memoria. |

---

## Mappers (`src/infrastructure/repositories/mappers.py`)

Funciones puras que transforman `asyncpg.Record` en entidades de dominio.

### `map_category_row(record) -> Category`

```python
from datetime import datetime
from src.domain.entities.category import Category


def map_category_row(record) -> Category:
    """Transforma un asyncpg.Record en una entidad Category.

    Args:
        record: asyncpg.Record con columnas id, name, description, created_at.

    Returns:
        Category con campos mapeados desde la fila de base de datos.

    Ejemplo::

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
    """Transforma un asyncpg.Record en una entidad Product.

    Construye el Value Object SKU desde el string almacenado en DB.

    Args:
        record: asyncpg.Record con columnas id, sku, name, description,
                unit_of_measure, category_id, min_stock_threshold, created_at.

    Returns:
        Product con SKU como Value Object.

    Raises:
        InvalidSKUError: Si el SKU en DB no cumple las reglas de formato.
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
    """Transforma un asyncpg.Record en una entidad Movement.

    Parsea el string movement_type al Enum MovementType y construye
    el Value Object Quantity desde el integer almacenado.

    Args:
        record: asyncpg.Record con columnas id, product_id, movement_type,
                quantity, metadata, reference, created_at.

    Returns:
        Movement con tipos de dominio correctos.

    Raises:
        ValueError: Si movement_type no es un valor válido del Enum.
        InvalidQuantityError: Si quantity <= 0 (no debería ocurrir con CHECK constraint).
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

> **Nota F3-hardening:** Todos los repositorios heredan de `BasePostgresRepository`
> (clase abstracta en `src/infrastructure/repositories/base_repository.py`).
> `BasePostgresRepository` centraliza `__init__(pool, connection)` y `_get_conn()`.
> Los ejemplos a continuación muestran el patrón completo para referencia;
> en la implementación real, los repos delegan `__init__` y `_get_conn` a la clase base.

### `BasePostgresRepository` (abstract)

```python
class BasePostgresRepository:
    """Clase base para repositorios que usan asyncpg."""

    def __init__(
        self,
        pool: asyncpg.Pool,
        connection: asyncpg.Connection | None = None,
    ) -> None:
        self._pool = pool
        self._connection = connection

    def _get_conn(self) -> asyncpg.Pool | asyncpg.Connection:
        """Retorna la conexion activa o el pool."""
        return self._connection if self._connection else self._pool
```

### `PostgresMovementRepository`

Implementa `IMovementRepository` del dominio.

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
    """Repositorio de movimientos con asyncpg y SQL explícito.

    No incluye update() ni delete() — los movimientos son inmutables.
    Soporta conexión compartida para transacciones Unit of Work.

    Ejemplo de uso sin transacción::

        repo = PostgresMovementRepository(pool)
        movement = await repo.create(movement_entity)

    Ejemplo de uso con Unit of Work::

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
        """Inicializa el repositorio con pool y conexión opcional.

        Args:
            pool: Pool de conexiones asyncpg (requerido).
            connection: Conexión activa para transacciones (opcional).
                        Si es None, se usa el pool directamente.
        """
        self._pool = pool
        self._connection = connection

    def _get_conn(self) -> asyncpg.Pool | asyncpg.Connection:
        """Retorna la conexión activa o el pool."""
        return self._connection if self._connection else self._pool

    async def create(self, movement: Movement) -> Movement:
        """Persiste un nuevo movimiento y retorna la entidad con id asignado."""
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
        """Recupera un movimiento por su ID."""
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
        """Lista movimientos de un producto con paginación."""
        rows = await self._get_conn().fetch(
            self._LIST_BY_PRODUCT_SQL, product_id, limit, offset
        )
        return [map_movement_row(r) for r in rows]
```

---

### `PostgresProductRepository`

Implementa `IProductRepository` del dominio.

```python
class PostgresProductRepository(IProductRepository):
    """Repositorio de productos con asyncpg y SQL explícito."""

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

### `PostgresCategoryRepository` (actualizado v1.0.2)

Implementa `ICategoryRepository` del dominio. **Desde v1.0.2, `list_all()` acepta `limit` y `offset` para paginacion en base de datos.**

```python
class PostgresCategoryRepository(ICategoryRepository):
    """Repositorio de categorías con asyncpg y SQL explícito."""

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

    # ... __init__, _get_conn, create, get_by_id heredados de BasePostgresRepository ...

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Category]:
        """Lista categorias con paginacion en base de datos."""
        rows = await self._get_conn().fetch(self._LIST_ALL_SQL, limit, offset)
        return [map_category_row(r) for r in rows]
```

---

### `PostgresStockQueryRepository`

Implementa `IStockQueryRepository` del dominio. Usa **cálculo directo** desde la tabla `movements` (sin vista materializada — la optimización se añade en Spec-31).

```python
from datetime import datetime


class PostgresStockQueryRepository(IStockQueryRepository):
    """Repositorio de consultas de stock con cálculo directo desde movements.

    Usa SQL con CASE/SUM para calcular stock. En Spec-31 se optimizará
    con la vista materializada mv_stock_historical.
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
        """Calcula el stock actual sumando todos los movimientos del producto."""
        row = await self._get_conn().fetchrow(self._CURRENT_STOCK_SQL, product_id)
        return float(row["stock"]) if row else 0.0

    async def get_stock_at_date(self, product_id: int, date: datetime) -> float:
        """Calcula el stock en una fecha específica."""
        row = await self._get_conn().fetchrow(self._STOCK_AT_DATE_SQL, product_id, date)
        return float(row["stock"]) if row else 0.0
```

---

## Files

| File | Description |
|------|-------------|
| `src/infrastructure/repositories/base_repository.py` | `BasePostgresRepository` — clase abstracta con `__init__` y `_get_conn()` compartidos |
| `src/infrastructure/repositories/mappers.py` | Funciones puras: `map_category_row`, `map_product_row`, `map_movement_row` (con manejo `JSONDecodeError`) |
| `src/infrastructure/repositories/movement_repository.py` | `PostgresMovementRepository` (hereda `BasePostgresRepository`) |
| `src/infrastructure/repositories/product_repository.py` | `PostgresProductRepository` (hereda `BasePostgresRepository`) |
| `src/infrastructure/repositories/category_repository.py` | `PostgresCategoryRepository` (hereda `BasePostgresRepository`) |
| `src/infrastructure/repositories/stock_query_repository.py` | `PostgresStockQueryRepository` (hereda `BasePostgresRepository`) |
| `src/infrastructure/repositories/__init__.py` | Re-exports: todos los repositorios y mappers |

---

## Acceptance Criteria

- [ ] Los 4 repositorios implementan sus protocols respectivos (verificable con `isinstance(repo, Protocol)` a runtime)
- [ ] Todos los repositorios heredan de `BasePostgresRepository` (no duplican `__init__` ni `_get_conn()`)
- [ ] Todo SQL usa parámetros posicionales (`$1`, `$2`) — cero concatenación de strings
- [ ] Los mappers son funciones puras (sin estado, sin I/O, testeables aisladamente)
- [ ] `map_movement_row` maneja `JSONDecodeError` en metadata corrupta (fallback a `{}` con warning log)
- [ ] **No** se usa `json.dumps()` para parámetros JSONB — asyncpg maneja `dict → JSONB` nativamente
- [ ] Constructor acepta `connection` opcional para integración con Unit of Work (Spec-32)
- [ ] `PostgresMovementRepository` **no** tiene métodos `update()` ni `delete()`
- [ ] Tests de integración con `testcontainers.postgres` validan: CRUD, paginación, cálculo de stock, mapeo de tipos
- [ ] `make lint` pasa sin errores en todos los archivos de repositorio

---

## Testing Strategy

- **Solo tests de integración** con `testcontainers.postgres` — valida SQL real contra PostgreSQL 16
- Fixture `db_pool` existente en `tests/integration/` se reutiliza
- Para cada repositorio: test de `create()`, `get_by_id()`, `list_*()`, y casos edge (no encontrado, paginación vacía)
- Tests de mappers aislados: validar que `asyncpg.Record` simulado se transforma correctamente
- `list_below_threshold`: insertar movimientos que lleven el stock por debajo del umbral y verificar que aparece en la lista

---

## Resolved Questions

1. **`get_current_stock()` retorna `int` o `float`?** → **`float`**. El port `IStockQueryRepository` define `float` como tipo de retorno. Mantener compatibilidad con el contrato existente (F2). La implementación convierte explícitamente con `float(row["stock"])`. Si en el futuro se necesita un port con `int`, se puede añadir un método separado sin romper este contrato.

2. **Añadir método batch `get_stock_for_multiple_products()`?** → **No en F3 (YAGNI).** No existe un use case que lo requiera actualmente. Los repositorios de F4 pueden hacer consultas individuales. Si en F5/F6 se identifica un cuello de botella real, se añade sin romper la API existente.

3. **¿Los mappers validan entidades o asumen DB válida?** → **Asumen DB válida con validación de tipos.** La base de datos tiene CHECK constraints, FK y trigger de inmutabilidad que protegen la integridad. Los mappers solo transforman tipos (`string → Enum`, `int → Quantity VO`). Si un valor no coincide (ej: `movement_type` no reconocido en Enum), se lanza la excepción nativa (`ValueError`). Si el SKU tiene formato inválido, `SKU()` lanza `InvalidSKUError`. Los mappers no validan invariantes de negocio — eso es responsabilidad de las entidades y la capa de dominio.
