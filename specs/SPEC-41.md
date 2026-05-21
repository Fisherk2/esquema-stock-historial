# SPEC-41: DTOs & Pydantic Validation

**Phase:** F4 — API Layer (Use Cases + Endpoints)  
**Dependencies:** Spec-40 (Use Cases) ✅ Pending  
**Priority:** High  
**Status:** Pending  

---

## Objective

Define separate Pydantic models (BaseModel) for **Input** and **Output** for each resource exposed by the API. Input DTOs validate and transform HTTP request data before passing it to the use case. Output DTOs serialize entities/use case data to the JSON response format.

**Design principles:**
- **Separate Input/Output** — `CreateMovementInput` (no `id`, no `created_at`) vs `MovementOutput` (with `id`, with `created_at`). Never the same model for both.
- **Validation at the system boundary** — Input DTOs are the first line of defense. If data passes the DTO, the use case can trust it.
- **snake_case in the API** — Consistent with Python. Do not use `camelCase` or aliases.
- **Strict mode in input** — `ConfigDict(strict=True)` prevents silent type coercion (e.g., `"123"` → `123`).
- **Value Objects are not exposed** — DTOs use primitive types (`str`, `int`, `float`). The use case builds VOs (`SKU`, `Quantity`) from validated data.
- **Consistent error format** — `ErrorResponse` with `{error: {code, message, details?}}` for all endpoints.

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| Separate Input/Output (not unified) | Semantic clarity: input = what the client sends, output = what the server returns. Avoids confusion with Optional fields |
| `strict=True` only in input DTOs | Output DTOs receive already validated data from the use case; strict mode is unnecessary and could break serialization |
| `snake_case` in API (not `camelCase`) | Consistent with Python, simpler (no aliases), and the API consumer is controlled by the team |
| Conditional metadata validation in `CreateMovementInput` | `@model_validator(mode="after")` verifies that TRANSFER has origin/destination and ADJUSTMENT has reason. Fails before reaching the use case |
| SKU regex in DTO same as in VO | Same pattern `^[A-Za-z0-9\-_]{1,50}$` on both sides for consistent error messages and fail-fast at the HTTP boundary |
| `ErrorResponse` with machine-readable `code` | Allows the API consumer to make programmatic decisions without parsing `message` |

---

## DTOs

### Movements

#### Input: `CreateMovementInput`

```python
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MovementTypeInput(StrEnum):
    """Inventory movement type (serializable to JSON)."""

    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"


class CreateMovementInput(BaseModel):
    """Input data to register a stock movement.

    Example::

        {
            "product_id": 1,
            "movement_type": "IN",
            "quantity": 10,
            "metadata": {"supplier": "ACME"},
            "reference": "PO-12345"
        }
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    product_id: int = Field(
        gt=0,
        description="ID of the product affected by the movement.",
        json_schema_extra={"examples": [1]},
    )
    movement_type: MovementTypeInput = Field(
        description="Movement type: IN, OUT, ADJUSTMENT, TRANSFER.",
        json_schema_extra={"examples": ["IN"]},
    )
    quantity: int = Field(
        gt=0,
        description="Positive quantity of units.",
        json_schema_extra={"examples": [10]},
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual data. Required for TRANSFER and ADJUSTMENT.",
        json_schema_extra={"examples": [{"supplier": "ACME"}]},
    )
    reference: str | None = Field(
        default=None,
        max_length=255,
        description="Optional external reference (order, note, etc.).",
        json_schema_extra={"examples": ["PO-12345"]},
    )

    @field_validator("movement_type", mode="before")
    @classmethod
    def coerce_movement_type(
        cls,
        v: str | MovementTypeInput,
    ) -> MovementTypeInput:
        """Converts strings to MovementTypeInput enum.

        With strict=True, Pydantic requires enum instances, not strings.
        This validator allows the API to accept strings (e.g., "IN") and
        convert them to enum before strict validation.
        """
        if isinstance(v, MovementTypeInput):
            return v
        return MovementTypeInput(v)
        """Validates metadata conditionally based on movement type.

        TRANSFER requires 'origin' and 'destination' in metadata.
        ADJUSTMENT requires 'reason' in metadata.

        Raises:
            ValueError: If metadata is insufficient for the type.
        """
        if self.movement_type == MovementTypeInput.TRANSFER:
            if "origin" not in self.metadata or "destination" not in self.metadata:
                raise ValueError(
                    "TRANSFER movement requires 'origin' and 'destination' in metadata"
                )
        elif self.movement_type == MovementTypeInput.ADJUSTMENT:
            if "reason" not in self.metadata:
                raise ValueError("ADJUSTMENT movement requires 'reason' in metadata")
        return self
```

**Design Notes:**
- `quantity: int` (not `int | float`) in input — the API only accepts integers. The use case can convert if necessary. If decimals are needed in the future, change to `int | float` without breaking the contract.
- `metadata: dict[str, str]` — values as strings for simplicity. The use case can interpret values according to context.
- `@model_validator(mode="after")` runs after individual field validation. If `movement_type` is invalid, Pydantic already raises before reaching here.

#### Output: `MovementOutput`

```python
from datetime import datetime

from pydantic import BaseModel, Field


class MovementOutput(BaseModel):
    """Output data for a stock movement.

    Example::

        {
            "id": 42,
            "product_id": 1,
            "movement_type": "IN",
            "quantity": 10,
            "metadata": {"supplier": "ACME"},
            "reference": "PO-12345",
            "created_at": "2025-05-18T14:30:00Z"
        }
    """

    id: int = Field(description="Unique identifier of the movement.")
    product_id: int = Field(description="ID of the affected product.")
    movement_type: str = Field(description="Movement type.")
    quantity: int = Field(description="Quantity of units.")
    metadata: dict[str, Any] = Field(description="Contextual data.")
    reference: str | None = Field(description="External reference.")
    created_at: datetime = Field(description="UTC date and time of the movement.")
```

#### List Output: `MovementListOutput`

```python
from pydantic import BaseModel, Field


class MovementListOutput(BaseModel):
    """Paginated response for movement list.

    Example::

        {
            "items": [...],
            "total": 150,
            "limit": 50,
            "offset": 0
        }
    """

    items: list[MovementOutput] = Field(description="List of movements.")
    total: int = Field(description="Total number of available movements.")
    limit: int = Field(description="Limit applied in the query.")
    offset: int = Field(description="Offset applied in the query.")
```

---

### Stock

#### Output: `CurrentStockOutput`

```python
from pydantic import BaseModel, Field


class CurrentStockOutput(BaseModel):
    """Current stock for a product.

    Example::

        {
            "product_id": 1,
            "current_stock": 42.0
        }
    """

    product_id: int = Field(description="ID of the product.")
    current_stock: float = Field(description="Current stock (can be decimal).")
```

#### Output: `StockAtDateOutput`

```python
from datetime import datetime

from pydantic import BaseModel, Field


class StockAtDateOutput(BaseModel):
    """Stock for a product at a historical date.

    Example::

        {
            "product_id": 1,
            "stock": 15.0,
            "date": "2025-01-01T00:00:00Z"
        }
    """

    product_id: int = Field(description="ID of the product.")
    stock: float = Field(description="Stock at the specified date.")
    date: datetime = Field(description="Query date.")
```

---

### Products

#### Input: `CreateProductInput`

```python
from pydantic import BaseModel, ConfigDict, Field


class CreateProductInput(BaseModel):
    """Input data to create a product.

    Example::

        {
            "sku": "PROD-001",
            "name": "Widget A",
            "unit_of_measure": "unit",
            "category_id": 1,
            "description": "Test widget",
            "min_stock_threshold": 10
        }
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    sku: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[A-Za-z0-9\-_]{1,50}$",
        description="Unique SKU code for the product.",
        json_schema_extra={"examples": ["PROD-001"]},
    )
    name: str = Field(
        min_length=1,
        max_length=255,
        description="Product name.",
        json_schema_extra={"examples": ["Widget A"]},
    )
    unit_of_measure: str = Field(
        min_length=1,
        max_length=50,
        description="Unit of measure (e.g., 'unit', 'kg', 'liter').",
        json_schema_extra={"examples": ["unit"]},
    )
    category_id: int = Field(
        gt=0,
        description="ID of the category it belongs to.",
        json_schema_extra={"examples": [1]},
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional product description.",
        json_schema_extra={"examples": ["Test widget"]},
    )
    min_stock_threshold: int = Field(
        default=0,
        ge=0,
        description="Minimum stock threshold for alerts.",
        json_schema_extra={"examples": [10]},
    )
```

**Design Notes:**
- The SKU regex pattern is identical to the `SKU` VO (`^[A-Za-z0-9\-_]{1,50}$`) for consistency
- `category_id: int > 0` — the use case will verify that the category exists
- `min_stock_threshold: int >= 0` — domain validation reflected in the DTO

#### Output: `ProductOutput`

```python
from datetime import datetime

from pydantic import BaseModel, Field


class ProductOutput(BaseModel):
    """Output data for a product.

    Example::

        {
            "id": 1,
            "sku": "PROD-001",
            "name": "Widget A",
            "description": "Test widget",
            "unit_of_measure": "unit",
            "category_id": 1,
            "min_stock_threshold": 10,
            "created_at": "2025-05-18T14:30:00Z"
        }
    """

    id: int = Field(description="Unique identifier of the product.")
    sku: str = Field(description="SKU code.")
    name: str = Field(description="Product name.")
    description: str | None = Field(description="Optional description.")
    unit_of_measure: str = Field(description="Unit of measure.")
    category_id: int = Field(description="Category ID.")
    min_stock_threshold: int = Field(description="Minimum stock threshold.")
    created_at: datetime = Field(description="UTC creation date and time.")
```

#### List Output: `ProductListOutput`

```python
from pydantic import BaseModel, Field


class ProductListOutput(BaseModel):
    """Paginated response for product list.

    Example::

        {
            "items": [...],
            "total": 85,
            "limit": 50,
            "offset": 0
        }
    """

    items: list[ProductOutput] = Field(description="List of products.")
    total: int = Field(description="Total number of available products.")
    limit: int = Field(description="Limit applied in the query.")
    offset: int = Field(description="Offset applied in the query.")
```

---

### Categories

#### Input: `CreateCategoryInput`

```python
from pydantic import BaseModel, ConfigDict, Field


class CreateCategoryInput(BaseModel):
    """Input data to create a category.

    Example::

        {
            "name": "Electronics",
            "description": "Electronic products"
        }
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Category name.",
        json_schema_extra={"examples": ["Electronics"]},
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional category description.",
        json_schema_extra={"examples": ["Electronic products"]},
    )
```

#### Output: `CategoryOutput`

```python
from datetime import datetime

from pydantic import BaseModel, Field


class CategoryOutput(BaseModel):
    """Output data for a category.

    Example::

        {
            "id": 1,
            "name": "Electronics",
            "description": "Electronic products",
            "created_at": "2025-05-18T14:30:00Z"
        }
    """

    id: int = Field(description="Unique identifier of the category.")
    name: str = Field(description="Category name.")
    description: str | None = Field(description="Optional description.")
    created_at: datetime = Field(description="UTC creation date and time.")
```

---

### Error

#### `ErrorResponse`

```python
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """API error detail.

    Example::

        {
            "code": "INSUFFICIENT_STOCK",
            "message": "Insufficient stock for product 1: requested 10, available 3",
            "details": {"product_id": 1, "requested": 10, "available": 3}
        }
    """

    code: str = Field(
        description="Machine-readable error code (UPPER_SNAKE_CASE)."
    )
    message: str = Field(description="Human-readable message.")
    details: dict[str, str | int | float] | None = Field(
        default=None,
        description="Additional error context (optional).",
    )


class ErrorResponse(BaseModel):
    """Error response wrapper.

    All endpoints return this format in case of error.

    Example::

        {
            "error": {
                "code": "NOT_FOUND",
                "message": "Product 999 not found"
            }
        }
    """

    error: ErrorDetail = Field(description="Error detail.")
```

---

## Files

| File | Description |
|------|-------------|
| `src/application/dtos/movement_dtos.py` | `CreateMovementInput`, `MovementOutput`, `MovementListOutput` |
| `src/application/dtos/stock_dtos.py` | `CurrentStockOutput`, `StockAtDateOutput` |
| `src/application/dtos/product_dtos.py` | `CreateProductInput`, `ProductOutput`, `ProductListOutput` |
| `src/application/dtos/category_dtos.py` | `CreateCategoryInput`, `CategoryOutput` |
| `src/application/dtos/error_dtos.py` | `ErrorResponse`, `ErrorDetail` |
| `src/application/dtos/__init__.py` | Re-exports: all DTOs |

---

## Acceptance Criteria

- [ ] All input DTOs use `ConfigDict(strict=True)` to prevent silent coercion
- [ ] `CreateMovementInput` validates metadata conditionally via `@model_validator(mode="after")`
- [ ] `CreateProductInput` validates SKU with regex `^[A-Za-z0-9\-_]{1,50}$` (same pattern as VO `SKU`)
- [ ] Input DTOs do NOT have `id` or `created_at` fields (generated by the server)
- [ ] Output DTOs DO have `id` and `created_at` fields
- [ ] `ErrorResponse` has consistent format: `{error: {code, message, details?}}`
- [ ] All DTOs include `json_schema_extra` with examples for OpenAPI
- [ ] `src/application/dtos/__init__.py` exports all public DTOs
- [ ] `make lint` passes without errors on all DTO files

---

## Testing Strategy

- **Input validation unit tests** — For each input DTO:
  - Valid data: constructs without error
  - Invalid data: raises `ValidationError` with descriptive message
  - Required fields omitted: raises `ValidationError`
  - Constraints (`gt=0`, `ge=0`, `min_length`, `max_length`, `pattern`): verify they are applied

- **`CreateMovementInput` — conditional validation:**
  - TRANSFER without origin/destination: `ValueError`
  - TRANSFER with origin and destination: OK
  - ADJUSTMENT without reason: `ValueError`
  - ADJUSTMENT with reason: OK
  - IN/OUT with empty metadata: OK
  - IN/OUT without metadata: OK (default factory)

- **`CreateProductInput` — SKU validation:**
  - Valid SKU (`PROD-001`): OK
  - Empty SKU: `ValidationError`
  - SKU with special characters (`PROD@001`): `ValidationError`
  - SKU > 50 chars: `ValidationError`

- **Output serialization tests** — Construct each output DTO, verify that `model.model_dump_json()` produces valid JSON with expected fields

- **`ErrorResponse` tests** — Construct with each error type, verify consistent format

---

## Resolved Questions

1. **Does the API use snake_case or camelCase for JSON fields?** → **snake_case.** Consistent with Python, simpler (no aliases), and the API consumer is controlled by the team. If frontend clients requiring camelCase are needed in the future, aliases can be added without breaking the internal contract.

2. **Include `CreateCategoryInput` and `CategoryOutput` in F4 or defer?** → **Include in F4.** Category is a prerequisite for creating products (`CreateProductUseCase` verifies the category exists). Without an endpoint to create categories, the system would not be functional for an HTTP client.

3. **Does `MovementListOutput` need pagination with `total`/`total_pages`?** → **Yes, with `total`, `limit`, `offset`.** Consistent pattern with `ProductListOutput`. `total_pages` is not included because the client can calculate it (`ceil(total / limit)`). Adding it to the DTO introduces ambiguity (does it round up? down?). The total/items calculation is sufficient.
