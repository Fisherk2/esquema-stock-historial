# SPEC-22: Protocolos/Interfaces (Ports)

**Fase:** F2 — Núcleo de Dominio  
**Dependencias:** Spec-20 (Entidades) ✅ Completado  
**Prioridad:** Alta  
**Estado:** Pendiente

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
    """Protocolo para persistencia y consulta de movimientos.

    No incluye métodos update() ni delete() — los movimientos son
    inmutables por diseño del dominio. Las correcciones se realizan
    mediante nuevos movimientos compensatorios (ADJUSTMENT).
    """

    async def create(self, movement: Movement) -> Movement:
        """Persiste un nuevo movimiento.

        Args:
            movement: Movimiento a persistir (sin id asignado).

        Returns:
            Movement: El mismo movimiento con id populated tras persistencia.
        """
        ...

    async def get_by_id(self, movement_id: int) -> Movement | None:
        """Recupera un movimiento por su ID.

        Args:
            movement_id: Identificador técnico del movimiento.

        Returns:
            Movement | None: El movimiento si existe, None si no.
        """
        ...

    async def list_by_product(
        self,
        product_id: int,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Movement]:
        """Lista movimientos de un producto, ordenados por created_at DESC.

        Args:
            product_id: Identificador del producto.
            limit: Máximo número de movimientos a retornar.
            offset: Número de movimientos a saltar (paginación).

        Returns:
            list[Movement]: Lista de movimientos ordenados por fecha descendente.
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
    """Protocolo para persistencia y consulta de productos."""

    async def create(self, product: Product) -> Product:
        """Persiste un nuevo producto.

        Args:
            product: Producto a persistir (sin id asignado).

        Returns:
            Product: El mismo producto con id populated tras persistencia.
        """
        ...

    async def get_by_id(self, product_id: int) -> Product | None:
        """Recupera un producto por su ID.

        Args:
            product_id: Identificador técnico del producto.

        Returns:
            Product | None: El producto si existe, None si no.
        """
        ...

    async def get_by_sku(self, sku: str) -> Product | None:
        """Recupera un producto por su SKU.

        Args:
            sku: Identificador de negocio del producto.

        Returns:
            Product | None: El producto si existe, None si no.
        """
        ...

    async def list_all(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Product]:
        """Lista todos los productos con paginación.

        Args:
            limit: Máximo número de productos a retornar.
            offset: Número de productos a saltar (paginación).

        Returns:
            list[Product]: Lista de productos.
        """
        ...

    async def list_below_threshold(self) -> list[Product]:
        """Lista productos con stock actual por debajo del umbral mínimo.

        Esta consulta requiere calcular el stock actual de cada producto
        (suma de movimientos) y compararlo con su min_stock_threshold.

        Returns:
            list[Product]: Productos con stock por debajo del umbral.
        """
        ...
```

**Design Notes:**
- `list_below_threshold()` es una consulta compleja que requiere join con movimientos
- `get_by_sku()` usa el SKU como string (no el VO) para simplificar la capa de infraestructura
- Paginación consistente con `IMovementRepository` (limit/offset)

---

### Port: `ICategoryRepository`

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.entities.category import Category


@runtime_checkable
class ICategoryRepository(Protocol):
    """Protocolo para persistencia y consulta de categorías."""

    async def create(self, category: Category) -> Category:
        """Persiste una nueva categoría.

        Args:
            category: Categoría a persistir (sin id asignado).

        Returns:
            Category: La misma categoría con id populated tras persistencia.
        """
        ...

    async def get_by_id(self, category_id: int) -> Category | None:
        """Recupera una categoría por su ID.

        Args:
            category_id: Identificador técnico de la categoría.

        Returns:
            Category | None: La categoría si existe, None si no.
        """
        ...

    async def list_all(self) -> list[Category]:
        """Lista todas las categorías.

        Returns:
            list[Category]: Lista de todas las categorías.
        """
        ...
```

**Design Notes:**
- Sin paginación en `list_all()` — se espera un número pequeño de categorías
- Sin `get_by_name()` — el nombre es UNIQUE pero la consulta por ID es suficiente

---

### Port: `IStockQueryRepository`

```python
from __future__ import annotations

from datetime import datetime

from typing import Protocol, runtime_checkable


@runtime_checkable
class IStockQueryRepository(Protocol):
    """Protocolo para consultas analíticas de stock.

    Separado de IMovementRepository (Interface Segregation Principle).
    Las consultas de stock son operaciones de lectura que pueden usar
    vistas materializadas, CTEs, o cálculos directos según la implementación.
    """

    async def get_current_stock(self, product_id: int) -> float:
        """Calcula el stock actual de un producto.

        Suma todos los movimientos del producto:
        - IN: +quantity
        - OUT: -quantity
        - ADJUSTMENT: +quantity
        - TRANSFER: -quantity (desde la perspectiva del origen)

        Args:
            product_id: Identificador del producto.

        Returns:
            float: Stock actual del producto (0.0 si no tiene movimientos).

        Note:
            Resolución F3-Q1: el tipo de retorno es `float` para compatibilidad
            con la implementación en SPEC-30/31 (vista materializada + asyncpg).
            Corregido de `int` a `float` para coincidir con el código real.
        """
        ...

    async def get_stock_at_date(
        self,
        product_id: int,
        date: datetime,
    ) -> float:
        """Calcula el stock de un producto en una fecha específica.

        Solo considera movimientos donde created_at <= date.

        Args:
            product_id: Identificador del producto.
            date: Fecha/hora de referencia (timezone-aware).

        Returns:
            float: Stock del producto en la fecha especificada (0.0 si no hay movimientos anteriores).
        """
        ...
```

**Design Notes:**
- Separado de `IMovementRepository` — ISP: consultas analíticas vs. CRUD de movimientos
- Retorna `float` (no entidades) — son consultas de agregación (resolución F3-Q1)
- `get_stock_at_date()` es la consulta principal para el objetivo de stock histórico <100ms
- La implementación puede usar vistas materializadas o cálculo directo según performance

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
