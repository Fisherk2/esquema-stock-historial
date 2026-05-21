# SPEC-40: Casos de Uso (Application)

**Fase:** F4 — Capa API (Casos de Uso + Endpoints)  
**Dependencias:** Spec-21 (Reglas de Negocio) ✅ Completado, Spec-22 (Protocolos) ✅ Completado, Spec-32 (Unit of Work) ✅ Completado  
**Prioridad:** Alta  
**Estado:** Pendiente  

---

## Objective

Implementar los 6 casos de uso de la capa de aplicación que orquestan las reglas de negocio del dominio con los repositorios de infraestructura. Cada caso de uso es una clase con un único método `execute()` que sigue el **Single Responsibility Principle**: una sola operación de negocio por clase.

**Principios de diseño:**
- **Use cases como clases** — permite inyección de dependencias en `__init__`, testeable con mocks, estado inmutable
- **Un solo método público `execute()`** — SRP estricto, punto de entrada único por caso de uso
- **Inyección de Protocolos** — el constructor recibe interfaces (`IMovementRepository`, etc.), no implementaciones concretas. DIP puro.
- **Zero imports de `infrastructure/`** — la capa de aplicación solo importa de `domain/` (ports, entities, exceptions, rules)
- **Excepciones de dominio se propagan** — los use cases NO capturan `DomainError` ni sus subclases. El adapter (Spec-42) las mapea a HTTP.
- **UoW para atomicidad** — `RecordMovementUseCase` usa `IUnitOfWork` para verificar stock y crear movimiento en una sola transacción

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| Clases con `execute()` (no funciones) | Permite DI en constructor, estado inmutable, mocks en testing, y composición de dependencias |
| Protocolos en `__init__`, no en `execute()` | Las dependencias son fijas por caso de uso; inyectarlas en `execute()` violaría DIP y haría difícil el testing |
| `RecordMovementUseCase` usa UoW | Verificar stock + crear movimiento deben ser atómicos; si el check pasa pero el create falla, no debe quedar inconsistencia |
| Validación de stock DENTRO del use case | El use case es el orquestador; la regla `validate_stock_not_negative()` requiere contexto de dominio que el repositorio no tiene |
| Excepciones de dominio sin capturar | Los use cases no saben de HTTP; capturar aquí acoplaría application con adapters. El middleware (Spec-42) mapea |
| `ListProductsUseCase` existe como clase | Aunque es un passthrough al repositorio, envolverlo permite añadir lógica futura (filtrado, caching, autorización) sin cambiar la API |

---

## Use Cases

### 1. `RecordMovementUseCase`

El caso de uso más complejo. Orquesta verificación de producto, validación de stock, consistencia de metadata, y persistencia atómica del movimiento.

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
    """Registra un nuevo movimiento de stock de forma atomica.

    Flujo:
        1. Verificar que el producto existe.
        2. Si el tipo de movimiento es OUT o TRANSFER:
           a. Consultar stock actual del producto.
           b. Validar que el stock no quede negativo.
        3. Construir la entidad Movement (validación de metadata en
           ``__post_init__`` — TRANSFER requiere origin/destination,
           ADJUSTMENT requiere reason).
        4. Persistir dentro de una transaccion (UoW).
        5. Retornar el movimiento persistido.

    Args:
        movement_repo: Repositorio de movimientos.
        product_repo: Repositorio de productos.
        stock_query_repo: Repositorio de consultas de stock.
        unit_of_work: Unit of Work para transacciones atomicas.
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
        """Ejecuta el caso de uso de registro de movimiento.

        Args:
            product_id: ID del producto al que afecta el movimiento.
            movement_type: Tipo de movimiento (IN, OUT, ADJUSTMENT, TRANSFER).
            quantity: Cantidad positiva de unidades.
            metadata: Diccionario contextual (obligatorio para TRANSFER y ADJUSTMENT).
            reference: Referencia externa opcional (orden, nota, etc.).

        Returns:
            Movement: La entidad movimiento persistida con id asignado.

        Raises:
            ValueError: Si el producto no existe.
            ValueError: Si la metadata es inconsistente con el tipo de movimiento.
            InsufficientStockError: Si el movimiento resultaria en stock negativo.
            InvalidQuantityError: Si quantity <= 0 (validado por el VO Quantity).

        Ejemplo::

            use_case = RecordMovementUseCase(movement_repo, product_repo, stock_repo, uow)
            movement = await use_case.execute(
                product_id=1,
                movement_type=MovementType.IN,
                quantity=10,
                metadata={"supplier": "ACME"},
                reference="PO-12345",
            )
        """
        # 1. Verificar que el producto existe
        product = await self._product_repo.get_by_id(product_id)
         if product is None:
             raise ProductNotFoundError(product_id)

        # 2. Para movimientos que reducen stock, validar que no quede negativo
        if movement_type in (MovementType.OUT, MovementType.TRANSFER):
            # Consultar stock actual dentro de la misma transaccion
            current_stock = await self._stock_query_repo.get_current_stock(product_id)
            validate_stock_not_negative(movement_type, quantity, current_stock, product_id)

        # 3. Construir y persistir dentro de UoW
        # (La validación de metadata se ejecuta en Movement.__post_init__)
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
            # Re-validar stock dentro de la transaccion para evitar race conditions
            # Se usa get_current_stock_with_lock (SELECT FOR UPDATE) para
            # serializar transacciones concurrentes del mismo producto.
            # La MV puede estar stale; calcular directamente dentro del lock.
            if movement_type in (MovementType.OUT, MovementType.TRANSFER):
                current_stock = await self._stock_query_repo.get_current_stock_with_lock(product_id)
                validate_stock_not_negative(movement_type, quantity, current_stock)

            result = await self._movement_repo.create(movement)

        return result
```

**Design Notes:**
- La validación de stock se ejecuta **dos veces**: antes del UoW (fail-fast sin adquirir conexión) y dentro del UoW (protección contra race conditions)
- **Dentro del UoW se usa `get_current_stock_with_lock()`** que ejecuta `SELECT ... FOR UPDATE` + cálculo directo desde la tabla `movements` (no la MV). Esto serializa transacciones concurrentes del mismo producto, previniendo que dos movimientos OUT/TRANSFER simultáneos lean el mismo stock stale de la MV y ambos pasen la validación.
- La validación de metadata se ejecuta en `Movement.__post_init__` al construir la entidad — **single source of truth** (SPEC-21). El use case NO llama `validate_movement_type_consistency` directamente. Si la metadata es inconsistente, `ValueError` se eleva desde el constructor y se traduce a HTTP 400.
- El UoW garantiza que si `create()` falla (FK violation, constraint), todo se revierte
- `RecordMovementUseCase` es el único use case que usa UoW; los demás son operaciones individuales

---

### 2. `QueryCurrentStockUseCase`

Consulta el stock actual de un producto. Simple, sin transacción.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.ports.stock_query_repository import IStockQueryRepository

if TYPE_CHECKING:
    pass


class QueryCurrentStockUseCase:
    """Consulta el stock actual de un producto.

    Args:
        stock_query_repo: Repositorio de consultas de stock.
    """

    def __init__(
        self,
        stock_query_repo: IStockQueryRepository,
    ) -> None:
        self._stock_query_repo = stock_query_repo

    async def execute(self, product_id: int) -> float:
        """Ejecuta la consulta de stock actual.

        Args:
            product_id: ID del producto.

        Returns:
            float: Stock actual del producto (0 si no tiene movimientos).

        Ejemplo::

            use_case = QueryCurrentStockUseCase(stock_repo)
            stock = await use_case.execute(product_id=1)  # 42.0
        """
        return await self._stock_query_repo.get_current_stock(product_id)
```

**Design Notes:**
- Operación de lectura pura — no requiere UoW
- El repositorio ya implementa la estrategia MV + fallback (Spec-31)

---

### 3. `QueryStockAtDateUseCase`

Consulta el stock de un producto en una fecha histórica específica.

```python
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.domain.ports.stock_query_repository import IStockQueryRepository

if TYPE_CHECKING:
    pass


class QueryStockAtDateUseCase:
    """Consulta el stock de un producto en una fecha historica.

    Args:
        stock_query_repo: Repositorio de consultas de stock.
    """

    def __init__(
        self,
        stock_query_repo: IStockQueryRepository,
    ) -> None:
        self._stock_query_repo = stock_query_repo

    async def execute(self, product_id: int, date: datetime) -> float:
        """Ejecuta la consulta de stock historico.

        Args:
            product_id: ID del producto.
            date: Fecha/hora de referencia (timezone-aware).

        Returns:
            float: Stock del producto en la fecha (0 si no hay movimientos anteriores).

        Ejemplo::

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
- Siempre usa cálculo directo sobre `movements` (la vista materializada solo tiene stock actual)
- La fecha debe ser timezone-aware — el caller (router/DTO) debe garantizarlo

---

### 4. `CreateProductUseCase`

Crea un nuevo producto, verificando que la categoría existe.

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
    """Crea un nuevo producto en el inventario.

    Flujo:
        1. Verificar que la categoria existe.
        2. Construir la entidad Product (con SKU VO).
        3. Persistir y retornar.

    Args:
        product_repo: Repositorio de productos.
        category_repo: Repositorio de categorias.
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
        """Ejecuta la creacion de un producto.

        Args:
            sku: Codigo SKU del producto.
            name: Nombre del producto (no vacio).
            unit_of_measure: Unidad de medida (e.g., "unit", "kg").
            category_id: ID de la categoria a la que pertenece.
            description: Descripcion opcional.
            min_stock_threshold: Umbral minimo de stock (default 0).

        Returns:
            Product: El producto persistido con id asignado.

        Raises:
            ValueError: Si la categoria no existe.
            InvalidSKUError: Si el SKU no cumple el patron requerido.
            ValueError: Si name o unit_of_measure son vacios.

        Ejemplo::

            use_case = CreateProductUseCase(product_repo, category_repo)
            product = await use_case.execute(
                sku="PROD-001",
                name="Widget A",
                unit_of_measure="unit",
                category_id=1,
                description="Widget de prueba",
                min_stock_threshold=10,
            )
        """
        # 1. Verificar que la categoria existe
        category = await self._category_repo.get_by_id(category_id)
        if category is None:
            raise ValueError(f"Category {category_id} not found")

        # 2. Construir y persistir
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
- La verificación de categoría usa el repositorio directamente (no necesita UoW porque es solo lectura)
- El constructor de `Product` ya valida `name`, `unit_of_measure`, y `min_stock_threshold` en `__post_init__`
- `SKU(sku)` lanza `InvalidSKUError` si el formato es inválido

---

### 5. `ListProductsUseCase`

Lista productos con paginación. Passthrough al repositorio, pero envuelto para consistencia arquitectónica.

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.ports.product_repository import IProductRepository

if TYPE_CHECKING:
    from src.domain.entities.product import Product


class ListProductsUseCase:
    """Lista productos del inventario con paginacion.

    Args:
        product_repo: Repositorio de productos.
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
        """Ejecuta la lista de productos.

        Args:
            limit: Maximo de resultados (default 100).
            offset: Desplazamiento para paginacion (default 0).

        Returns:
            list[Product]: Lista de productos ordenados por ID.

        Ejemplo::

            use_case = ListProductsUseCase(product_repo)
            products = await use_case.execute(limit=50, offset=0)
        """
        return await self._product_repo.list_all(limit=limit, offset=offset)
```

**Design Notes:**
- Actualmente es un passthrough al repositorio, pero envolverlo permite añadir lógica futura (filtrado por categoría, búsqueda por nombre, caching) sin cambiar la API del adapter
- Mantiene consistencia: todos los endpoints de lectura pasan por un use case

---

### 6. `CreateCategoryUseCase`

Crea una nueva categoría de productos.

```python
from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from src.domain.entities.category import Category
from src.domain.ports.category_repository import ICategoryRepository

if TYPE_CHECKING:
    pass


class CreateCategoryUseCase:
    """Crea una nueva categoria de productos.

    Args:
        category_repo: Repositorio de categorias.
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
        """Ejecuta la creacion de una categoria.

        Args:
            name: Nombre de la categoria (no vacio).
            description: Descripcion opcional.

        Returns:
            Category: La categoria persistida con id asignado.

        Raises:
            ValueError: Si name es vacio.

        Ejemplo::

            use_case = CreateCategoryUseCase(category_repo)
            category = await use_case.execute(
                name="Electronics",
                description="Productos electronicos",
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
- La entidad `Category` ya valida `name` no vacío en `__post_init__`
- Operación simple, no requiere UoW (single insert)

---

## Files

| File | Description |
|------|-------------|
| `src/application/use_cases/record_movement.py` | `RecordMovementUseCase` — crea movimiento con validacion de stock |
| `src/application/use_cases/query_current_stock.py` | `QueryCurrentStockUseCase` — stock actual |
| `src/application/use_cases/query_stock_at_date.py` | `QueryStockAtDateUseCase` — stock historico |
| `src/application/use_cases/create_product.py` | `CreateProductUseCase` — crea producto con verificacion de categoria |
| `src/application/use_cases/list_products.py` | `ListProductsUseCase` — lista con paginacion |
| `src/application/use_cases/create_category.py` | `CreateCategoryUseCase` — crea categoria |
| `src/application/use_cases/__init__.py` | Re-exports: los 6 use cases |

---

## Acceptance Criteria

- [ ] Los 6 use cases implementan un unico metodo publico `async execute()`
- [ ] Todos los use cases inyectan Protocolos en `__init__` (no implementaciones concretas)
- [ ] `RecordMovementUseCase` verifica que el producto existe antes de crear el movimiento
- [ ] `RecordMovementUseCase` valida stock no negativo para OUT y TRANSFER (dos veces: fail-fast + dentro de UoW)
- [ ] `RecordMovementUseCase` valida consistencia de metadata para TRANSFER y ADJUSTMENT
- [ ] `RecordMovementUseCase` usa `IUnitOfWork` para atomicidad
- [ ] `CreateProductUseCase` verifica que la categoria existe antes de crear el producto
- [ ] Los use cases NO importan de `infrastructure/` (solo de `domain/` ports, entities, exceptions, rules)
- [ ] Las excepciones de dominio (`InsufficientStockError`, `InvalidSKUError`, etc.) se propagan sin capturar
- [ ] `src/application/use_cases/__init__.py` exporta los 6 use cases
- [ ] `make lint` pasa sin errores en todos los archivos de use cases

---

## Testing Strategy

- **Tests unitarios con mocks** — Cada use case se testea aisladamente con mocks de sus Protocolos. No se usa DB real.
- **`RecordMovementUseCase`** — Tests parametrizados por `MovementType`:
  - IN: crea sin validar stock
  - OUT: valida stock, lanza `InsufficientStockError` si no hay suficiente
  - TRANSFER: valida stock + metadata (origin/destination)
  - ADJUSTMENT: valida metadata (reason)
  - Producto no encontrado: lanza `ValueError`
- **`QueryCurrentStockUseCase`** — Delega al mock del repo, retorna valor
- **`QueryStockAtDateUseCase`** — Delega al mock del repo con fecha, retorna valor
- **`CreateProductUseCase`** — Categoria no encontrada (`ValueError`), SKU invalido (`InvalidSKUError`), creacion exitosa
- **`ListProductsUseCase`** — Lista vacia, lista con items, paginacion (limit/offset)
- **`CreateCategoryUseCase`** — Nombre vacio (`ValueError`), creacion exitosa
- Mock de `IUnitOfWork`: crear un context manager async fake que simule commit/rollback

---

## Resolved Questions

1. **¿Cuántos casos de uso debe definir Spec-40?** → **6 Use Cases.** `RecordMovementUseCase`, `QueryCurrentStockUseCase`, `QueryStockAtDateUseCase`, `CreateProductUseCase`, `ListProductsUseCase`, `CreateCategoryUseCase`. Cubre las operaciones principales del dominio sin excesiva granularity. `ListCategoriesUseCase` y `ListBelowThresholdUseCase` se pueden añadir en fases futuras si se identifican endpoints que los requieran.

2. **¿Cómo debe manejar `RecordMovementUseCase` la validación de stock?** → **Dentro del Use Case.** El use case consulta `IStockQueryRepository.get_current_stock()`, aplica `validate_stock_not_negative()`, y si pasa, crea el movimiento dentro de una `IUnitOfWork` para atomicidad. La validación se ejecuta dos veces: antes del UoW (fail-fast sin adquirir conexión) y dentro del UoW (protección contra race conditions entre el check y el insert).

3. **¿Debe `RecordMovementUseCase` usar UoW también para IN/ADJUSTMENT?** → **No.** Solo para OUT y TRANSFER. IN y ADJUSTMENT siempre incrementan stock y no pueden violar el invariante de stock negativo. Usar UoW para todas las operaciones añadiría overhead innecesario. Si en el futuro se necesita atomicidad multi-repositorio para IN/ADJUSTMENT (ej: crear movimiento + actualizar tabla de auditoría), se añade sin romper el patrón existente.

4. **¿`ListProductsUseCase` es necesario o es un passthrough innecesario?** → **Sí, es necesario.** Aunque actualmente es un passthrough al repositorio, envolverlo mantiene consistencia arquitectónica: todos los endpoints de lectura pasan por un use case. Esto permite añadir lógica futura (filtrado por categoría, búsqueda por nombre, caching, autorización) sin cambiar la API del adapter. El costo de la envoltura es mínimo (una clase de ~15 líneas).
