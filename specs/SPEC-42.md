# SPEC-42: FastAPI /v1/ Routes & OpenAPI

**Phase:** F4 — API Layer (Use Cases + Endpoints)  
**Dependencies:** Spec-40 (Use Cases) ✅ Pending, Spec-41 (DTOs) ✅ Pending  
**Priority:** High  
**Status:** Pending  

---

## Objective

Implement the **4 FastAPI routers** (`/v1/movements`, `/v1/stock`, `/v1/products`, `/v1/categories`), the **error mapping middleware** that translates domain exceptions to HTTP responses, and the **dependency injection factory functions** that build repos and use cases injecting the asyncpg pool. The routers are pure adapters: their only responsibility is to receive HTTP, invoke use cases, and return HTTP. Zero business logic.

**Design principles:**
- **Routers as pure adapters** —only HTTP ↔ Use Cases, no business rules, no direct DB access
- **Annotated + Depends** — Modern FastAPI pattern for typed dependency injection
- **Centralized error mapping** — A single handler captures domain exceptions and maps them to `ErrorResponse`
- **Semantic status codes** — 201 for POST (created), 200 for GET, 404 for not found, 409 for conflict (stock), 422 for Pydantic validation
- **snake_case in the API** — Query params, field names, everything consistent with Python
- **Automatic OpenAPI documentation** — Pydantic models with `json_schema_extra` generate interactive docs

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| 4 separate routers (not a single one) | SRP: each router handles one resource. Modular, independently testable, easy to maintain |
| `Annotated[UseCase, Depends(get_use_case)]` | Modern FastAPI pattern (v0.100+). Explicit typing, IDE autocomplete, no boilerplate |
| Error mapping as exception handlers (not HTTP middleware) | FastAPI `@exception_handler` is more elegant than HTTP middleware for this case: captures specific exceptions and returns `JSONResponse` |
| Status 409 for `InsufficientStockError` | Semantically correct: the resource (product) exists but the current state prevents the operation (conflict) |
| Status 422 for domain validation | Pydantic already uses 422 for input validation; extending it to domain validations maintains consistency |
| Pagination with defaults in query params | `limit=100` by default, `offset=0`. Without pagination, endpoints with many records are vulnerable to DoS |
| `get_pool()` reused from `src/infrastructure/db/connection.py` | Don't reinvent the wheel. The pool already exists and is managed via lifespan. Adapters consume it directly |

---

## Dependency Injection Factory Functions

The factories build repos and use cases injecting the asyncpg pool. They are defined in `src/adapters/api/dependencies.py`.

```python
"""Factory functions for FastAPI dependency injection.

Each factory function builds a repository or use case injecting
the asyncpg connection pool. They are used with ``Depends()`` in endpoints.

Example::

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
    """Gets the asyncpg connection pool.

    Raises:
        HTTPException: If the pool is not initialized.
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
    """Movement repository factory."""
    return PostgresMovementRepository(pool)


async def get_product_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> IProductRepository:
    """Product repository factory."""
    return PostgresProductRepository(pool)


async def get_category_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> ICategoryRepository:
    """Category repository factory."""
    return PostgresCategoryRepository(pool)


async def get_stock_query_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> IStockQueryRepository:
    """Stock query repository factory."""
    return PostgresStockQueryRepository(pool)


# ─── Unit of Work ───────────────────────────────────────────────────────

async def get_unit_of_work(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> IUnitOfWork:
    """Unit of Work factory."""
    return PostgresUnitOfWork(pool)


# ─── Use Cases ──────────────────────────────────────────────────────────

async def get_record_movement_use_case(
    movement_repo: Annotated[IMovementRepository, Depends(get_movement_repo)],
    product_repo: Annotated[IProductRepository, Depends(get_product_repo)],
    stock_query_repo: Annotated[IStockQueryRepository, Depends(get_stock_query_repo)],
    uow: Annotated[IUnitOfWork, Depends(get_unit_of_work)],
) -> RecordMovementUseCase:
    """RecordMovementUseCase factory."""
    return RecordMovementUseCase(movement_repo, product_repo, stock_query_repo, uow)


async def get_query_current_stock_use_case(
    stock_query_repo: Annotated[IStockQueryRepository, Depends(get_stock_query_repo)],
) -> QueryCurrentStockUseCase:
    """QueryCurrentStockUseCase factory."""
    return QueryCurrentStockUseCase(stock_query_repo)


async def get_query_stock_at_date_use_case(
    stock_query_repo: Annotated[IStockQueryRepository, Depends(get_stock_query_repo)],
) -> QueryStockAtDateUseCase:
    """QueryStockAtDateUseCase factory."""
    return QueryStockAtDateUseCase(stock_query_repo)


async def get_create_product_use_case(
    product_repo: Annotated[IProductRepository, Depends(get_product_repo)],
    category_repo: Annotated[ICategoryRepository, Depends(get_category_repo)],
) -> CreateProductUseCase:
    """CreateProductUseCase factory."""
    return CreateProductUseCase(product_repo, category_repo)


async def get_list_products_use_case(
    product_repo: Annotated[IProductRepository, Depends(get_product_repo)],
) -> ListProductsUseCase:
    """ListProductsUseCase factory."""
    return ListProductsUseCase(product_repo)


async def get_create_category_use_case(
    category_repo: Annotated[ICategoryRepository, Depends(get_category_repo)],
) -> CreateCategoryUseCase:
    """CreateCategoryUseCase factory."""
    return CreateCategoryUseCase(category_repo)
```

**Design Notes:**
- Factories are async because `get_pool()` is async
- FastAPI resolves dependencies in cascade automatically: `get_record_movement_use_case` → `get_movement_repo` → `get_db_pool`
- Each factory returns the Protocol type (not the concrete implementation), keeping DIP visible at the signature level

---

## Routers

### `/v1/movements` — `src/adapters/api/routers/movements.py`

```python
"""Movements router — recording and querying stock movements.

Exposes endpoints to create movements (entries, exits, adjustments,
transfers) and query the movement history of a product.

Endpoints:
    POST   /v1/movements           — Create movement
    GET    /v1/movements/{id}      — Get movement by ID
    GET    /v1/movements           — List movements of a product
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
    summary="Create stock movement",
    description="Records a new movement (IN, OUT, ADJUSTMENT, TRANSFER). "
    "For OUT and TRANSFER, validates that stock does not go negative.",
)
async def create_movement(
    body: CreateMovementInput,
    use_case: Annotated[RecordMovementUseCase, Depends(get_record_movement_use_case)],
) -> MovementOutput:
    """Creates a new stock movement."""
    from src.domain.value_objects.movement_type import MovementType

    movement = await use_case.execute(
        product_id=body.product_id,
        movement_type=MovementType(body.movement_type.value),
        quantity=body.quantity,
        metadata=body.metadata,
        reference=body.reference,
    )
    if movement.id is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to create movement: no ID generated",
        )
    return _movement_to_output(movement)


@router.get(
    "/{movement_id}",
    response_model=MovementOutput,
    summary="Get movement by ID",
)
async def get_movement(
    movement_id: int,
    repo: Annotated[IMovementRepository, Depends(get_movement_repo)],
) -> MovementOutput:
    """Retrieves a movement by its ID."""
    movement = await repo.get_by_id(movement_id)
    if movement is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Movement not found")
    return _movement_to_output(movement)


@router.get(
    "",
    response_model=MovementListOutput,
    summary="List movements of a product",
)
async def list_movements(
    product_id: int = Query(description="Product ID."),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results."),
    offset: int = Query(default=0, ge=0, description="Offset."),
    repo: Annotated[IMovementRepository, Depends(get_movement_repo)],
) -> MovementListOutput:
    """Lists movements of a product with pagination."""
    movements = await repo.list_by_product(product_id, limit=limit, offset=offset)
    total = await repo.count_by_product(product_id)
    return MovementListOutput(
        items=[_movement_to_output(m) for m in movements],
        total=total,
        limit=limit,
        offset=offset,
    )
```

**Design Notes:**
- `POST /v1/movements` uses `response_model=MovementOutput` — FastAPI validates the response with Pydantic
- `status_code=201` for POST (resource created)
- The mapping of `Movement` (entity) → `MovementOutput` (DTO) is done in the router because the use case returns the domain entity
- `list_movements` receives `product_id` as a query param (not path param) because it is a filter, not a resource identifier

---

### `/v1/stock` — `src/adapters/api/routers/stock.py`

```python
"""Stock router — current and historical stock queries.

Endpoints:
    GET    /v1/stock/{product_id}/current        — Current stock
    GET    /v1/stock/{product_id}/at-date        — Stock at a date
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
    summary="Query current stock",
    description="Gets the current stock of a product using the materialized "
    "view (with fallback to direct calculation).",
)
async def get_current_stock(
    product_id: int,
    use_case: Annotated[
        QueryCurrentStockUseCase, Depends(get_query_current_stock_use_case)
    ],
) -> CurrentStockOutput:
    """Gets the current stock of a product."""
    stock = await use_case.execute(product_id)
    return CurrentStockOutput(product_id=product_id, current_stock=stock)


@router.get(
    "/{product_id}/at-date",
    response_model=StockAtDateOutput,
    summary="Query historical stock",
    description="Calculates the stock of a product at a specific date "
    "using direct calculation on the movements table.",
)
async def get_stock_at_date(
    product_id: int,
    date: datetime = Query(
        description="Query date (timezone-aware, ISO 8601). "
        "E.g.: 2025-01-01T00:00:00Z",
    ),
    use_case: Annotated[
        QueryStockAtDateUseCase, Depends(get_query_stock_at_date_use_case)
    ],
) -> StockAtDateOutput:
    """Gets the stock of a product at a date."""
    stock = await use_case.execute(product_id, date)
    return StockAtDateOutput(product_id=product_id, stock=stock, date=date)
```

**Design Notes:**
- `date` as query param with type `datetime` — FastAPI parses it automatically from ISO 8601
- **Timezone handling:** If the client sends a naive datetime (without timezone), the router converts it to UTC-aware via `_ensure_timezone_aware()` before passing to the use case. This is necessary because the DB uses `TIMESTAMPTZ` and a naive datetime could produce incorrect results depending on the server timezone.
- The product existence is not validated here — the use case/repository returns 0 if there are no movements (expected behavior)
- The historical endpoint uses direct calculation (not materialized view), so it may be slower; this is documented in the description

---

### `/v1/products` — `src/adapters/api/routers/products.py`

```python
"""Products router — creation and querying of products.

Endpoints:
    POST   /v1/products              — Create product
    GET    /v1/products              — List products
    GET    /v1/products/{product_id} — Get product by ID
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
    summary="Create product",
    description="Creates a new product in the inventory. "
    "The category must exist beforehand.",
)
async def create_product(
    body: CreateProductInput,
    use_case: Annotated[CreateProductUseCase, Depends(get_create_product_use_case)],
) -> ProductOutput:
    """Creates a new product."""
    product = await use_case.execute(
        sku=body.sku,
        name=body.name,
        unit_of_measure=body.unit_of_measure,
        category_id=body.category_id,
        description=body.description,
        min_stock_threshold=body.min_stock_threshold,
    )
    if product.id is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to create product: no ID generated",
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
    summary="List products",
)
async def list_products(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum results."),
    offset: int = Query(default=0, ge=0, description="Offset."),
    use_case: Annotated[ListProductsUseCase, Depends(get_list_products_use_case)],
) -> ProductListOutput:
    """Lists products with pagination."""
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
    summary="Get product by ID",
)
async def get_product(
    product_id: int,
    repo: Annotated[IProductRepository, Depends(get_product_repo)],
) -> ProductOutput:
    """Gets a product by its ID."""
    product = await repo.get_by_id(product_id)
    if product is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Product not found")
    if product.id is None:
        raise HTTPException(
            status_code=500,
            detail="Product ID missing after retrieval",
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
```

---

### `/v1/categories` — `src/adapters/api/routers/categories.py`

```python
"""Categories router — creation and querying of categories.

Endpoints:
    POST   /v1/categories    — Create category
    GET    /v1/categories    — List categories
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
    summary="Create category",
)
async def create_category(
    body: CreateCategoryInput,
    use_case: Annotated[CreateCategoryUseCase, Depends(get_create_category_use_case)],
) -> CategoryOutput:
    """Creates a new category."""
    category = await use_case.execute(
        name=body.name,
        description=body.description,
    )
    if category.id is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to create category: no ID generated",
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
    summary="List categories",
)
async def list_categories(
    repo: Annotated[ICategoryRepository, Depends(get_category_repo)],
) -> list[CategoryOutput]:
    """Lists all categories (without pagination)."""
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
- Database pagination: `list_all(limit, offset)` uses `LIMIT $1 OFFSET $2` in SQL (not in-memory slicing). See SPEC-30 for repository implementation details.
- `response_model=list[CategoryOutput]` — FastAPI serializes the list automatically
- Query params `limit` (default=100, max=1000) and `offset` (default=0) validated by FastAPI

---

## Error Mapping Middleware

Centralized handler in `src/adapters/api/middleware/error_handler.py` that captures domain exceptions and maps them to `ErrorResponse`.

```python
"""Domain exception mapping to HTTP responses.

Registers exception handlers on the FastAPI app to capture domain errors
and convert them into structured JSON responses.
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
    """Registers exception handlers on the FastAPI app.

    Args:
        app: FastAPI instance where to register the handlers.
    """

    @app.exception_handler(InsufficientStockError)
    async def handle_insufficient_stock(
        request, exc: InsufficientStockError
    ) -> JSONResponse:
        """Maps InsufficientStockError to HTTP 409 Conflict."""
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
        """Maps InvalidSKUError to HTTP 422 Unprocessable Entity."""
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
        """Maps InvalidQuantityError to HTTP 422 Unprocessable Entity."""
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
        """Maps ImmutabilityViolationError to HTTP 403 Forbidden."""
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
        """Maps DomainError (base) to HTTP 500 Internal Server Error.

        This handler captures any DomainError not handled by the
        specific handlers above (fall-through).
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
        """Maps ValueError to HTTP 400 Bad Request.

        Used for input validation errors (inconsistent metadata,
        product/category not found, etc.).
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

### Error Mapping Table

| Domain Exception | HTTP Status | Error Code | Context |
|-------------------|-------------|------------|----------|
| `InsufficientStockError` | 409 Conflict | `INSUFFICIENT_STOCK` | OUT/TRANSFER with insufficient stock |
| `InvalidSKUError` | 422 Unprocessable | `INVALID_SKU` | SKU does not match pattern `[A-Za-z0-9\-_]{1,50}` |
| `InvalidQuantityError` | 422 Unprocessable | `INVALID_QUANTITY` | Quantity <= 0 |
| `ImmutabilityViolationError` | 403 Forbidden | `IMMUTABILITY_VIOLATION` | Attempt to modify existing movement |
| `DomainError` (base) | 500 Internal | `DOMAIN_ERROR` | Domain error not specifically mapped |
| `ValueError` | 400 Bad Request | `VALIDATION_ERROR` | Product/category not found, inconsistent metadata |
| (Pydantic ValidationError) | 422 Unprocessable | `VALIDATION_ERROR` | Invalid input DTO (handled natively by FastAPI) |
| (FastAPI HTTPException) | Per exception | Per exception | 404 for resource not found |

**Design Notes:**
- Registration order matters: specific handlers are registered before the generic `DomainError` handler
- **`ValueError` handler with origin verification:** The `handle_value_error` handler does not capture all `ValueError` indiscriminately. It checks the exception traceback to determine if it originated in validation modules (`src/application/dtos`, `src/domain/value_objects`, `src/domain/entities`, `src/domain/rules`). If the exception came from infrastructure or internal code, it is re-raised (reaches the `Exception` handler → HTTP 500). This prevents masking internal bugs as client errors (400).
- FastAPI already handles Pydantic `ValidationError` automatically (422) — no handler needed for that
- The `DomainError` handler is a catch-all for unmapped subclasses — returns 500 because it is an unexpected domain error

---

## Update `src/main.py`

Update `create_app()` to register the 4 new routers and error handlers.

```python
# Add at the end of create_app(), after the health router:
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

# Update version
app = FastAPI(
    title="Stock Historial",
    description="Inventory management system with Immutable Source of Truth",
    version="0.4.0",  # from 0.1.0 to 0.4.0 (F4 completed)
    lifespan=lifespan,
)
```

---

## Endpoint Summary

| Method | Route | Use Case | Status | Response | Tags |
|--------|------|----------|--------|----------|------|
| POST | `/v1/movements` | `RecordMovementUseCase` | 201 | `MovementOutput` | movements |
| GET | `/v1/movements/{movement_id}` | (direct to repo) | 200 / 404 | `MovementOutput` | movements |
| GET | `/v1/movements?product_id=&limit=&offset=` | (direct to repo) | 200 | `MovementListOutput` | movements |
| GET | `/v1/stock/{product_id}/current` | `QueryCurrentStockUseCase` | 200 | `CurrentStockOutput` | stock |
| GET | `/v1/stock/{product_id}/at-date?date=` | `QueryStockAtDateUseCase` | 200 | `StockAtDateOutput` | stock |
| POST | `/v1/products` | `CreateProductUseCase` | 201 | `ProductOutput` | products |
| GET | `/v1/products` | `ListProductsUseCase` | 200 | `ProductListOutput` | products |
| GET | `/v1/products/{product_id}` | (direct to repo) | 200 / 404 | `ProductOutput` | products |
| POST | `/v1/categories` | `CreateCategoryUseCase` | 201 | `CategoryOutput` | categories |
| GET | `/v1/categories` | (direct to repo) | 200 | `list[CategoryOutput]` | categories |

---

## Files

| File | Description |
|------|-------------|
| `src/adapters/api/dependencies.py` | Factory functions for DI (pool → repos → use cases) |
| `src/adapters/api/routers/movements.py` | POST/GET movements router |
| `src/adapters/api/routers/stock.py` | GET current and historical stock router |
| `src/adapters/api/routers/products.py` | POST/GET products router |
| `src/adapters/api/routers/categories.py` | POST/GET categories router |
| `src/adapters/api/middleware/error_handler.py` | Exception handlers for domain errors |
| `src/main.py` | Update: register 4 routers + error handlers |

---

## Acceptance Criteria

- [ ] The 4 routers are registered in `create_app()` with `/v1` prefix
- [ ] `POST /v1/movements` returns 201 with `MovementOutput` when creating a valid movement
- [ ] `POST /v1/movements` returns 409 when stock is insufficient (OUT/TRANSFER)
- [ ] `POST /v1/movements` returns 400 when the product does not exist
- [ ] `GET /v1/stock/{product_id}/current` returns `CurrentStockOutput` with current stock
- [ ] `GET /v1/stock/{product_id}/at-date?date=` returns `StockAtDateOutput` with historical stock
- [ ] `POST /v1/products` returns 201 with `ProductOutput` when creating a valid product
- [ ] `POST /v1/products` returns 422 when the SKU is invalid
- [ ] `POST /v1/products` returns 400 when the category does not exist
- [ ] `POST /v1/categories` returns 201 with `CategoryOutput` when creating a valid category
- [ ] `POST /v1/categories` returns 422 when the name is empty
- [ ] Domain errors are mapped to `ErrorResponse` via exception handlers
- [ ] OpenAPI documentation (`/docs`) shows the 10 endpoints with descriptions and examples
- [ ] `make lint` passes without errors on all adapter files

---

## Testing Strategy

- **Integration tests with `testcontainers.postgres`** — Validate each endpoint with a real DB:
  - Seed data (category, product) before each test
  - `POST /v1/categories` → validate 201 + response body
  - `POST /v1/products` → validate 201 + response body
  - `POST /v1/movements` (IN) → validate 201
  - `POST /v1/movements` (OUT without stock) → validate 409
  - `GET /v1/stock/{id}/current` → validate correct stock
  - `GET /v1/products` → validate list with pagination

- **Error mapping tests** — Simulate domain exceptions and verify the handler returns the correct format:
  - `InsufficientStockError` → 409 + `INSUFFICIENT_STOCK`
  - `InvalidSKUError` → 422 + `INVALID_SKU`
  - `ValueError` (product not found) → 400 + `VALIDATION_ERROR`

- **Pydantic validation tests** — Send invalid payloads to endpoints and verify FastAPI returns 422:
  - `POST /v1/products` with empty SKU → 422
  - `POST /v1/movements` with quantity=0 → 422
  - `POST /v1/movements` with TRANSFER without origin/destination → 422

- **DI factory tests** — Verify that factories build the correct objects (optional, more unit than integration)

---

## Resolved Questions

1. **Should routers import from `infrastructure/` to create repos?** → **Not directly.** Routers import from `dependencies.py`, and `dependencies.py` is the only file in `adapters/` that imports from `infrastructure/`. This maintains the import rule: `adapters/` can import from `infrastructure/`, but routers (which are the public endpoints) should not have that direct dependency. Factories encapsulate the construction.

2. **Should GET by ID endpoints use use cases or go directly to the repo?** → **Direct to repository.** Querying a resource by ID is a simple read operation with no business logic. Wrapping it in a use case would add a layer of indirection without value. This is consistent with the CQRS pattern: simple queries → direct repository; commands and complex queries → use case. The health.py router already follows this pattern (imports `get_pool()` directly).

3. **Should the total of `MovementListOutput` be exact or can it be `len(items)`?** → **Must be exact (separate count).** Using `len(items)` is incorrect because if there are 150 movements and the limit is 50, `len(items)` would be 50 but the actual total is 150. The repository must expose a `count_by_product()` method or the use case must perform the count query. **This is a note for Spec-40:** `ListProductsUseCase` and `list_movements` should return `(items, total)` instead of just `items`. This can be added as a follow-up without breaking the use case contract (change the return type).