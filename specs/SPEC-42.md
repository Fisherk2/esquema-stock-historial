# SPEC-42: Rutas FastAPI /v1/ & OpenAPI

**Fase:** F4 — Capa API (Casos de Uso + Endpoints)  
**Dependencias:** Spec-40 (Casos de Uso) ✅ Pendiente, Spec-41 (DTOs) ✅ Pendiente  
**Prioridad:** Alta  
**Estado:** Pendiente  

---

## Objective

Implementar los **4 routers** FastAPI (`/v1/movements`, `/v1/stock`, `/v1/products`, `/v1/categories`), el **middleware de mapeo de errores** que traduce excepciones de dominio a respuestas HTTP, y las **factory functions de dependency injection** que construyen repos y use cases inyectando el pool asyncpg. Los routers son adaptadores puros: su única responsabilidad es recibir HTTP, invocar use cases, y retornar HTTP. Cero lógica de negocio.

**Principios de diseño:**
- **Routers como adaptadores puros** —solo HTTP ↔ Use Cases, sin reglas de negocio, sin acceso directo a DB
- **Annotated + Depends** — Patrón moderno de FastAPI para inyección de dependencias tipadas
- **Error mapping centralizado** — Un solo handler captura excepciones de dominio y las mapea a `ErrorResponse`
- **Status codes semánticos** — 201 para POST (creado), 200 para GET, 404 para no encontrado, 409 para conflicto (stock), 422 para validación Pydantic
- **snake_case en la API** — Query params, field names, todo consistente con Python
- **Documentación OpenAPI automática** — Pydantic models con `json_schema_extra` generan docs interactivos

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| 4 routers separados (no uno solo) | SRP: cada router maneja un recurso. Modular, testeable independientemente, fácil de mantener |
| `Annotated[UseCase, Depends(get_use_case)]` | Patrón moderno de FastAPI (v0.100+). Tipado explícito, autocomplete en IDEs, sin boilerplate |
| Error mapping como excepción handlers (no middleware HTTP) | FastAPI `@exception_handler` es más elegante que middleware HTTP para este caso: captura excepciones específicas y retorna `JSONResponse` |
| Status 409 para `InsufficientStockError` | Semánticamente correcto: el recurso (producto) existe pero el estado actual impide la operación (conflicto) |
| Status 422 para validación de dominio | Pydantic ya usa 422 para validación de input; extenderlo a validaciones de dominio mantiene consistencia |
| Paginación con defaults en query params | `limit=100` por defecto, `offset=0`. Sin paginación, los endpoints con muchos registros son vulnerables a DoS |
| `get_pool()` reutilizado desde `src/infrastructure/db/connection.py` | No reinventar la rueda. El pool ya existe y se gestiona via lifespan. Los adapters lo consumen directamente |

---

## Dependency Injection Factory Functions

Las factories construyen repos y use cases inyectando el pool asyncpg. Se definen en `src/adapters/api/dependencies.py`.

```python
"""Factory functions para dependency injection de FastAPI.

Cada factory function construye un repositorio o caso de uso inyectando
el pool de conexiones asyncpg. Se usan con ``Depends()`` en los endpoints.

Ejemplo::

    @router.post("/movements", response_model=MovementOutput, status_code=201)
    async def create_movement(
        body: CreateMovementInput,
        use_case: Annotated[RecordMovementUseCase, Depends(get_record_movement_use_case)],
    ) -> MovementOutput:
        movement = await use_case.execute(...)
        return MovementOutput.model_validate(movement)
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.application.use_cases.create_category import CreateCategoryUseCase
from src.application.use_cases.create_product import CreateProductUseCase
from src.application.use_cases.list_products import ListProductsUseCase
from src.application.use_cases.query_current_stock import QueryCurrentStockUseCase
from src.application.use_cases.query_stock_at_date import QueryStockAtDateUseCase
from src.application.use_cases.record_movement import RecordMovementUseCase
from src.domain.ports.category_repository import ICategoryRepository
from src.domain.ports.movement_repository import IMovementRepository
from src.domain.ports.product_repository import IProductRepository
from src.domain.ports.stock_query_repository import IStockQueryRepository
from src.domain.ports.unit_of_work import IUnitOfWork
from src.infrastructure.db.connection import get_pool
from src.infrastructure.db.uow import PostgresUnitOfWork
from src.infrastructure.repositories.category_repository import (
    PostgresCategoryRepository,
)
from src.infrastructure.repositories.movement_repository import (
    PostgresMovementRepository,
)
from src.infrastructure.repositories.product_repository import (
    PostgresProductRepository,
)
from src.infrastructure.repositories.stock_query_repository import (
    PostgresStockQueryRepository,
)

import asyncpg


# ─── Pool ───────────────────────────────────────────────────────────────

async def get_db_pool() -> asyncpg.Pool:
    """Obtiene el pool de conexiones asyncpg.

    Raises:
        HTTPException: Si el pool no esta inicializado.
    """
    pool = await get_pool()
    if pool is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="Database connection not available",
        )
    return pool


# ─── Repositories ───────────────────────────────────────────────────────

async def get_movement_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> IMovementRepository:
    """Fabrica de repositorio de movimientos."""
    return PostgresMovementRepository(pool)


async def get_product_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> IProductRepository:
    """Fabrica de repositorio de productos."""
    return PostgresProductRepository(pool)


async def get_category_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> ICategoryRepository:
    """Fabrica de repositorio de categorias."""
    return PostgresCategoryRepository(pool)


async def get_stock_query_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> IStockQueryRepository:
    """Fabrica de repositorio de consultas de stock."""
    return PostgresStockQueryRepository(pool)


# ─── Unit of Work ───────────────────────────────────────────────────────

async def get_unit_of_work(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> IUnitOfWork:
    """Fabrica de Unit of Work."""
    return PostgresUnitOfWork(pool)


# ─── Use Cases ──────────────────────────────────────────────────────────

async def get_record_movement_use_case(
    movement_repo: Annotated[IMovementRepository, Depends(get_movement_repo)],
    product_repo: Annotated[IProductRepository, Depends(get_product_repo)],
    stock_query_repo: Annotated[IStockQueryRepository, Depends(get_stock_query_repo)],
    uow: Annotated[IUnitOfWork, Depends(get_unit_of_work)],
) -> RecordMovementUseCase:
    """Fabrica de RecordMovementUseCase."""
    return RecordMovementUseCase(movement_repo, product_repo, stock_query_repo, uow)


async def get_query_current_stock_use_case(
    stock_query_repo: Annotated[IStockQueryRepository, Depends(get_stock_query_repo)],
) -> QueryCurrentStockUseCase:
    """Fabrica de QueryCurrentStockUseCase."""
    return QueryCurrentStockUseCase(stock_query_repo)


async def get_query_stock_at_date_use_case(
    stock_query_repo: Annotated[IStockQueryRepository, Depends(get_stock_query_repo)],
) -> QueryStockAtDateUseCase:
    """Fabrica de QueryStockAtDateUseCase."""
    return QueryStockAtDateUseCase(stock_query_repo)


async def get_create_product_use_case(
    product_repo: Annotated[IProductRepository, Depends(get_product_repo)],
    category_repo: Annotated[ICategoryRepository, Depends(get_category_repo)],
) -> CreateProductUseCase:
    """Fabrica de CreateProductUseCase."""
    return CreateProductUseCase(product_repo, category_repo)


async def get_list_products_use_case(
    product_repo: Annotated[IProductRepository, Depends(get_product_repo)],
) -> ListProductsUseCase:
    """Fabrica de ListProductsUseCase."""
    return ListProductsUseCase(product_repo)


async def get_create_category_use_case(
    category_repo: Annotated[ICategoryRepository, Depends(get_category_repo)],
) -> CreateCategoryUseCase:
    """Fabrica de CreateCategoryUseCase."""
    return CreateCategoryUseCase(category_repo)
```

**Design Notes:**
- Las factories son async porque `get_pool()` es async
- FastAPI resolve dependencias en cascada automáticamente: `get_record_movement_use_case` → `get_movement_repo` → `get_db_pool`
- Cada factory retorna el tipo Protocol (no la implementación concreta), manteniendo DIP visible a nivel de firma

---

## Routers

### `/v1/movements` — `src/adapters/api/routers/movements.py`

```python
"""Router de movimientos — registro y consulta de movimientos de stock.

Expone endpoints para crear movimientos (entradas, salidas, ajustes,
transferencias) y consultar el historial de movimientos de un producto.

Endpoints:
    POST   /v1/movements           — Crear movimiento
    GET    /v1/movements/{id}      — Obtener movimiento por ID
    GET    /v1/movements           — Listar movimientos de un producto
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.application.dtos.movement_dtos import (
    CreateMovementInput,
    MovementListOutput,
    MovementOutput,
)
from src.application.use_cases.record_movement import RecordMovementUseCase
from src.domain.ports.movement_repository import IMovementRepository

router = APIRouter(prefix="/movements", tags=["movements"])


@router.post(
    "",
    response_model=MovementOutput,
    status_code=201,
    summary="Crear movimiento de stock",
    description="Registra un nuevo movimiento (IN, OUT, ADJUSTMENT, TRANSFER). "
    "Para OUT y TRANSFER, valida que el stock no quede negativo.",
)
async def create_movement(
    body: CreateMovementInput,
    use_case: Annotated[RecordMovementUseCase, Depends(get_record_movement_use_case)],
) -> MovementOutput:
    """Crea un nuevo movimiento de stock."""
    from src.domain.value_objects.movement_type import MovementType

    movement = await use_case.execute(
        product_id=body.product_id,
        movement_type=MovementType(body.movement_type.value),
        quantity=body.quantity,
        metadata=body.metadata,
        reference=body.reference,
    )
    return MovementOutput(
        id=movement.id,
        product_id=movement.product_id,
        movement_type=movement.movement_type.value,
        quantity=movement.quantity.value,
        metadata=movement.metadata,
        reference=movement.reference,
        created_at=movement.created_at,
    )


@router.get(
    "/{movement_id}",
    response_model=MovementOutput,
    summary="Obtener movimiento por ID",
)
async def get_movement(
    movement_id: int,
    repo: Annotated[IMovementRepository, Depends(get_movement_repo)],
) -> MovementOutput:
    """Recupera un movimiento por su ID."""
    movement = await repo.get_by_id(movement_id)
    if movement is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Movement not found")
    return MovementOutput(
        id=movement.id,
        product_id=movement.product_id,
        movement_type=movement.movement_type.value,
        quantity=movement.quantity.value,
        metadata=movement.metadata,
        reference=movement.reference,
        created_at=movement.created_at,
    )


@router.get(
    "",
    response_model=MovementListOutput,
    summary="Listar movimientos de un producto",
)
async def list_movements(
    product_id: int = Query(description="ID del producto."),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximo de resultados."),
    offset: int = Query(default=0, ge=0, description="Desplazamiento."),
    repo: Annotated[IMovementRepository, Depends(get_movement_repo)],
) -> MovementListOutput:
    """Lista movimientos de un producto con paginacion."""
    movements = await repo.list_by_product(product_id, limit=limit, offset=offset)
    return MovementListOutput(
        items=[
            MovementOutput(
                id=m.id,
                product_id=m.product_id,
                movement_type=m.movement_type.value,
                quantity=m.quantity.value,
                metadata=m.metadata,
                reference=m.reference,
                created_at=m.created_at,
            )
            for m in movements
        ],
        total=len(movements),  # El repositorio deberia retornar total; simplificado
        limit=limit,
        offset=offset,
    )
```

**Design Notes:**
- `POST /v1/movements` usa `response_model=MovementOutput` — FastAPI valida la respuesta con Pydantic
- `status_code=201` para POST (recurso creado)
- El mapping de `Movement` (entidad) → `MovementOutput` (DTO) se hace en el router porque el use case retorna la entidad de dominio
- `list_movements` recibe `product_id` como query param (no path param) porque es un filtro, no un identificador de recurso

---

### `/v1/stock` — `src/adapters/api/routers/stock.py`

```python
"""Router de stock — consultas de stock actual e historico.

Endpoints:
    GET    /v1/stock/{product_id}/current        — Stock actual
    GET    /v1/stock/{product_id}/at-date        — Stock en una fecha
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.application.dtos.stock_dtos import CurrentStockOutput, StockAtDateOutput
from src.application.use_cases.query_current_stock import QueryCurrentStockUseCase
from src.application.use_cases.query_stock_at_date import QueryStockAtDateUseCase

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get(
    "/{product_id}/current",
    response_model=CurrentStockOutput,
    summary="Consultar stock actual",
    description="Obtiene el stock actual de un producto usando la vista "
    "materializada (con fallback a calculo directo).",
)
async def get_current_stock(
    product_id: int,
    use_case: Annotated[
        QueryCurrentStockUseCase, Depends(get_query_current_stock_use_case)
    ],
) -> CurrentStockOutput:
    """Obtiene el stock actual de un producto."""
    stock = await use_case.execute(product_id)
    return CurrentStockOutput(product_id=product_id, current_stock=stock)


@router.get(
    "/{product_id}/at-date",
    response_model=StockAtDateOutput,
    summary="Consultar stock historico",
    description="Calcula el stock de un producto en una fecha especifica "
    "usando calculo directo sobre la tabla de movimientos.",
)
async def get_stock_at_date(
    product_id: int,
    date: datetime = Query(
        description="Fecha de consulta (timezone-aware, ISO 8601). "
        "Ej: 2025-01-01T00:00:00Z",
    ),
    use_case: Annotated[
        QueryStockAtDateUseCase, Depends(get_query_stock_at_date_use_case)
    ],
) -> StockAtDateOutput:
    """Obtiene el stock de un producto en una fecha."""
    stock = await use_case.execute(product_id, date)
    return StockAtDateOutput(product_id=product_id, stock=stock, date=date)
```

**Design Notes:**
- `date` como query param con tipo `datetime` — FastAPI lo parsea automáticamente desde ISO 8601
- No se valida que el producto exista aquí — el use case/repositorio retorna 0 si no hay movimientos (comportamiento esperado)
- El endpoint histórico usa cálculo directo (no vista materializada), por lo que puede ser más lento; esto se documenta en la descripción

---

### `/v1/products` — `src/adapters/api/routers/products.py`

```python
"""Router de productos — creacion y consulta de productos.

Endpoints:
    POST   /v1/products              — Crear producto
    GET    /v1/products              — Listar productos
    GET    /v1/products/{product_id} — Obtener producto por ID
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.application.dtos.product_dtos import (
    CreateProductInput,
    ProductListOutput,
    ProductOutput,
)
from src.application.use_cases.create_product import CreateProductUseCase
from src.application.use_cases.list_products import ListProductsUseCase
from src.domain.ports.product_repository import IProductRepository

router = APIRouter(prefix="/products", tags=["products"])


@router.post(
    "",
    response_model=ProductOutput,
    status_code=201,
    summary="Crear producto",
    description="Crea un nuevo producto en el inventario. "
    "La categoria debe existir previamente.",
)
async def create_product(
    body: CreateProductInput,
    use_case: Annotated[CreateProductUseCase, Depends(get_create_product_use_case)],
) -> ProductOutput:
    """Crea un nuevo producto."""
    product = await use_case.execute(
        sku=body.sku,
        name=body.name,
        unit_of_measure=body.unit_of_measure,
        category_id=body.category_id,
        description=body.description,
        min_stock_threshold=body.min_stock_threshold,
    )
    return ProductOutput(
        id=product.id,
        sku=product.sku.value,
        name=product.name,
        description=product.description,
        unit_of_measure=product.unit_of_measure,
        category_id=product.category_id,
        min_stock_threshold=product.min_stock_threshold,
        created_at=product.created_at,
    )


@router.get(
    "",
    response_model=ProductListOutput,
    summary="Listar productos",
)
async def list_products(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximo de resultados."),
    offset: int = Query(default=0, ge=0, description="Desplazamiento."),
    use_case: Annotated[ListProductsUseCase, Depends(get_list_products_use_case)],
) -> ProductListOutput:
    """Lista productos con paginacion."""
    products = await use_case.execute(limit=limit, offset=offset)
    return ProductListOutput(
        items=[
            ProductOutput(
                id=p.id,
                sku=p.sku.value,
                name=p.name,
                description=p.description,
                unit_of_measure=p.unit_of_measure,
                category_id=p.category_id,
                min_stock_threshold=p.min_stock_threshold,
                created_at=p.created_at,
            )
            for p in products
        ],
        total=len(products),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{product_id}",
    response_model=ProductOutput,
    summary="Obtener producto por ID",
)
async def get_product(
    product_id: int,
    repo: Annotated[IProductRepository, Depends(get_product_repo)],
) -> ProductOutput:
    """Obtiene un producto por su ID."""
    product = await repo.get_by_id(product_id)
    if product is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOutput(
        id=product.id,
        sku=product.sku.value,
        name=product.name,
        description=product.description,
        unit_of_measure=product.unit_of_measure,
        category_id=product.category_id,
        min_stock_threshold=product.min_stock_threshold,
        created_at=product.created_at,
    )
```

---

### `/v1/categories` — `src/adapters/api/routers/categories.py`

```python
"""Router de categorias — creacion y consulta de categorias.

Endpoints:
    POST   /v1/categories    — Crear categoria
    GET    /v1/categories    — Listar categorias
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from src.application.dtos.category_dtos import (
    CategoryOutput,
    CreateCategoryInput,
)
from src.application.use_cases.create_category import CreateCategoryUseCase
from src.domain.ports.category_repository import ICategoryRepository

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post(
    "",
    response_model=CategoryOutput,
    status_code=201,
    summary="Crear categoria",
)
async def create_category(
    body: CreateCategoryInput,
    use_case: Annotated[CreateCategoryUseCase, Depends(get_create_category_use_case)],
) -> CategoryOutput:
    """Crea una nueva categoria."""
    category = await use_case.execute(
        name=body.name,
        description=body.description,
    )
    return CategoryOutput(
        id=category.id,
        name=category.name,
        description=category.description,
        created_at=category.created_at,
    )


@router.get(
    "",
    response_model=list[CategoryOutput],
    summary="Listar categorias",
)
async def list_categories(
    repo: Annotated[ICategoryRepository, Depends(get_category_repo)],
) -> list[CategoryOutput]:
    """Lista todas las categorias (sin paginacion)."""
    categories = await repo.list_all()
    return [
        CategoryOutput(
            id=c.id,
            name=c.name,
            description=c.description,
            created_at=c.created_at,
        )
        for c in categories
    ]
```

**Design Notes:**
- Sin paginación en `list_categories` — Se espera un conjunto pequeño (<100 categorías)
- `response_model=list[CategoryOutput]` — FastAPI serializa la lista automáticamente

---

## Error Mapping Middleware

Handler centralizado en `src/adapters/api/middleware/error_handler.py` que captura excepciones de dominio y las mapea a `ErrorResponse`.

```python
"""Mapeo de excepciones de dominio a respuestas HTTP.

Registra handlers de excepcion en la app FastAPI para capturar errores
del dominio y convertirlos en respuestas JSON estructuradas.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from src.application.dtos.error_dtos import ErrorDetail, ErrorResponse
from src.domain.exceptions.domain_error import DomainError
from src.domain.exceptions.immutability_violation import ImmutabilityViolationError
from src.domain.exceptions.insufficient_stock import InsufficientStockError
from src.domain.exceptions.invalid_quantity import InvalidQuantityError
from src.domain.exceptions.invalid_sku import InvalidSKUError


def register_error_handlers(app: FastAPI) -> None:
    """Registra los handlers de excepcion en la app FastAPI.

    Args:
        app: Instancia de FastAPI donde registrar los handlers.
    """

    @app.exception_handler(InsufficientStockError)
    async def handle_insufficient_stock(
        request, exc: InsufficientStockError
    ) -> JSONResponse:
        """Mapea InsufficientStockError a HTTP 409 Conflict."""
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INSUFFICIENT_STOCK",
                    message=str(exc),
                    details={
                        "product_id": exc.product_id,
                        "requested": exc.requested,
                        "available": exc.available,
                    },
                )
            ).model_dump(),
        )

    @app.exception_handler(InvalidSKUError)
    async def handle_invalid_sku(request, exc: InvalidSKUError) -> JSONResponse:
        """Mapea InvalidSKUError a HTTP 422 Unprocessable Entity."""
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_SKU",
                    message=str(exc),
                )
            ).model_dump(),
        )

    @app.exception_handler(InvalidQuantityError)
    async def handle_invalid_quantity(
        request, exc: InvalidQuantityError
    ) -> JSONResponse:
        """Mapea InvalidQuantityError a HTTP 422 Unprocessable Entity."""
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_QUANTITY",
                    message=str(exc),
                )
            ).model_dump(),
        )

    @app.exception_handler(ImmutabilityViolationError)
    async def handle_immutability_violation(
        request, exc: ImmutabilityViolationError
    ) -> JSONResponse:
        """Mapea ImmutabilityViolationError a HTTP 403 Forbidden."""
        return JSONResponse(
            status_code=403,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="IMMUTABILITY_VIOLATION",
                    message=str(exc),
                )
            ).model_dump(),
        )

    @app.exception_handler(DomainError)
    async def handle_domain_error(request, exc: DomainError) -> JSONResponse:
        """Mapea DomainError (base) a HTTP 500 Internal Server Error.

        Este handler captura cualquier DomainError no manejado por los
        handlers especificos de arriba (fall-through).
        """
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="DOMAIN_ERROR",
                    message=str(exc),
                )
            ).model_dump(),
        )

    @app.exception_handler(ValueError)
    async def handle_value_error(request, exc: ValueError) -> JSONResponse:
        """Mapea ValueError a HTTP 400 Bad Request.

        Se usa para errores de validacion de input (metadata inconsistente,
        producto/categoria no encontrado, etc.).
        """
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=str(exc),
                )
            ).model_dump(),
        )
```

### Tabla de Mapeo de Errores

| Excepción Dominio | HTTP Status | Error Code | Contexto |
|-------------------|-------------|------------|----------|
| `InsufficientStockError` | 409 Conflict | `INSUFFICIENT_STOCK` | OUT/TRANSFER con stock insuficiente |
| `InvalidSKUError` | 422 Unprocessable | `INVALID_SKU` | SKU no cumple patron `[A-Za-z0-9\-_]{1,50}` |
| `InvalidQuantityError` | 422 Unprocessable | `INVALID_QUANTITY` | Cantidad <= 0 |
| `ImmutabilityViolationError` | 403 Forbidden | `IMMUTABILITY_VIOLATION` | Intento de modificar movimiento existente |
| `DomainError` (base) | 500 Internal | `DOMAIN_ERROR` | Error de dominio no mapeado especificamente |
| `ValueError` | 400 Bad Request | `VALIDATION_ERROR` | Producto/categoría no encontrado, metadata inconsistente |
| (Pydantic ValidationError) | 422 Unprocessable | `VALIDATION_ERROR` | Input DTO invalido (manejado por FastAPI nativamente) |
| (FastAPI HTTPException) | Según exception | Según exception | 404 para recurso no encontrado |

**Design Notes:**
- El orden de registro importa: los handlers específicos se registran antes que el handler genérico de `DomainError`
- `ValueError` se captura a nivel de app (no en cada endpoint) para centralizar el manejo de "producto no encontrado", "categoría no encontrada", etc.
- FastAPI ya maneja `ValidationError` de Pydantic automáticamente (422) — no necesitamos handler para eso
- El handler de `DomainError` es un catch-all para subclases no mapeadas — retorna 500 porque es un error inesperado del dominio

---

## Update `src/main.py`

Actualizar `create_app()` para registrar los 4 nuevos routers y los error handlers.

```python
# Añadir al final de create_app(), despues del health router:
from src.adapters.api.middleware.error_handler import register_error_handlers
from src.adapters.api.routers.categories import router as categories_router
from src.adapters.api.routers.movements import router as movements_router
from src.adapters.api.routers.products import router as products_router
from src.adapters.api.routers.stock import router as stock_router

# Register routers
app.include_router(movements_router, prefix="/v1")
app.include_router(stock_router, prefix="/v1")
app.include_router(products_router, prefix="/v1")
app.include_router(categories_router, prefix="/v1")

# Register error handlers
register_error_handlers(app)

# Actualizar version
app = FastAPI(
    title="Stock Historial",
    description="Sistema de gestion de inventario con Source of Truth Inmutable",
    version="0.4.0",  # de 0.1.0 a 0.4.0 (F4 completada)
    lifespan=lifespan,
)
```

---

## Endpoint Summary

| Método | Ruta | Use Case | Status | Response | Tags |
|--------|------|----------|--------|----------|------|
| POST | `/v1/movements` | `RecordMovementUseCase` | 201 | `MovementOutput` | movements |
| GET | `/v1/movements/{movement_id}` | (directo a repo) | 200 / 404 | `MovementOutput` | movements |
| GET | `/v1/movements?product_id=&limit=&offset=` | (directo a repo) | 200 | `MovementListOutput` | movements |
| GET | `/v1/stock/{product_id}/current` | `QueryCurrentStockUseCase` | 200 | `CurrentStockOutput` | stock |
| GET | `/v1/stock/{product_id}/at-date?date=` | `QueryStockAtDateUseCase` | 200 | `StockAtDateOutput` | stock |
| POST | `/v1/products` | `CreateProductUseCase` | 201 | `ProductOutput` | products |
| GET | `/v1/products` | `ListProductsUseCase` | 200 | `ProductListOutput` | products |
| GET | `/v1/products/{product_id}` | (directo a repo) | 200 / 404 | `ProductOutput` | products |
| POST | `/v1/categories` | `CreateCategoryUseCase` | 201 | `CategoryOutput` | categories |
| GET | `/v1/categories` | (directo a repo) | 200 | `list[CategoryOutput]` | categories |

---

## Files

| File | Description |
|------|-------------|
| `src/adapters/api/dependencies.py` | Factory functions para DI (pool → repos → use cases) |
| `src/adapters/api/routers/movements.py` | Router POST/GET movimientos |
| `src/adapters/api/routers/stock.py` | Router GET stock actual e historico |
| `src/adapters/api/routers/products.py` | Router POST/GET productos |
| `src/adapters/api/routers/categories.py` | Router POST/GET categorias |
| `src/adapters/api/middleware/error_handler.py` | Exception handlers para errores de dominio |
| `src/main.py` | Update: registrar 4 routers + error handlers |

---

## Acceptance Criteria

- [ ] Los 4 routers se registran en `create_app()` con prefijo `/v1`
- [ ] `POST /v1/movements` retorna 201 con `MovementOutput` al crear un movimiento valido
- [ ] `POST /v1/movements` retorna 409 cuando el stock es insuficiente (OUT/TRANSFER)
- [ ] `POST /v1/movements` retorna 400 cuando el producto no existe
- [ ] `GET /v1/stock/{product_id}/current` retorna `CurrentStockOutput` con stock actual
- [ ] `GET /v1/stock/{product_id}/at-date?date=` retorna `StockAtDateOutput` con stock historico
- [ ] `POST /v1/products` retorna 201 con `ProductOutput` al crear un producto valido
- [ ] `POST /v1/products` retorna 422 cuando el SKU es invalido
- [ ] `POST /v1/products` retorna 400 cuando la categoria no existe
- [ ] `POST /v1/categories` retorna 201 con `CategoryOutput` al crear una categoria valida
- [ ] `POST /v1/categories` retorna 422 cuando el nombre es vacio
- [ ] Los errores de dominio se mapean a `ErrorResponse` via exception handlers
- [ ] La documentacion OpenAPI (`/docs`) muestra los 10 endpoints con descripciones y ejemplos
- [ ] `make lint` pasa sin errores en todos los archivos de adapters

---

## Testing Strategy

- **Tests de integración con `testcontainers.postgres`** — Validar cada endpoint con DB real:
  - Seed data (categoría, producto) antes de cada test
  - `POST /v1/categories` → validar 201 + response body
  - `POST /v1/products` → validar 201 + response body
  - `POST /v1/movements` (IN) → validar 201
  - `POST /v1/movements` (OUT sin stock) → validar 409
  - `GET /v1/stock/{id}/current` → validar stock correcto
  - `GET /v1/products` → validar lista con paginación

- **Tests de error mapping** — Simular excepciones de dominio y verificar que el handler retorna el formato correcto:
  - `InsufficientStockError` → 409 + `INSUFFICIENT_STOCK`
  - `InvalidSKUError` → 422 + `INVALID_SKU`
  - `ValueError` (producto no encontrado) → 400 + `VALIDATION_ERROR`

- **Tests de validación Pydantic** — Enviar payloads inválidos a los endpoints y verificar que FastAPI retorna 422:
  - `POST /v1/products` con SKU vacío → 422
  - `POST /v1/movements` con quantity=0 → 422
  - `POST /v1/movements` con TRANSFER sin origin/destination → 422

- **Tests de DI factories** — Verificar que las factories construyen los objetos correctos (opcional, más unit que integration)

---

## Resolved Questions

1. **¿Los routers deben importar de `infrastructure/` para crear repos?** → **No directamente.** Los routers importan de `dependencies.py`, y `dependencies.py` es el único archivo de `adapters/` que importa de `infrastructure/`. Esto mantiene la regla de importación: `adapters/` puede importar de `infrastructure/`, pero los routers (que son los endpoints públicos) no deberían tener esa dependencia directa. Las factories encapsulan la construcción.

2. **¿Los endpoints de GET por ID deben usar use cases o ir directo al repo?** → **Directo al repositorio.** Consultar un recurso por ID es una operación de lectura simple sin lógica de negocio. Envolverlo en un use case añadiría una capa de indirección sin valor. Esto es consistente con el patrón de CQRS: queries simples → repositorio directo; commands y queries complejas → use case. El router health.py ya sigue este patrón (importa `get_pool()` directamente).

3. **¿El total de `MovementListOutput` debe ser exacto o puede ser `len(items)`?** → **Debe ser exacto (count separado).** Usar `len(items)` es incorrecto porque si hay 150 movimientos y el limit es 50, `len(items)` sería 50 pero el total real es 150. El repositorio debe exponer un método `count_by_product()` o el use case debe hacer la consulta de conteo. **Esta es una nota para Spec-40:** `ListProductsUseCase` y `list_movements` deben retornar `(items, total)` en lugar de solo `items`. Esto se puede añadir como follow-up sin romper el contrato del use case (cambiar el tipo de retorno).
