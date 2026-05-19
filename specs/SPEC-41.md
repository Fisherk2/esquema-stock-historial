# SPEC-41: DTOs & Validación Pydantic

**Fase:** F4 — Capa API (Casos de Uso + Endpoints)  
**Dependencias:** Spec-40 (Casos de Uso) ✅ Pendiente  
**Prioridad:** Alta  
**Estado:** Pendiente  

---

## Objective

Definir los modelos Pydantic (BaseModel) de **Input** y **Output** separados para cada recurso expuesto por la API. Los DTOs de input validan y transforman datos del request HTTP antes de pasarlos al use case. Los DTOs de output serializan las entidades/datos del use case al formato JSON de respuesta.

**Principios de diseño:**
- **Input/Output separados** — `CreateMovementInput` (sin `id`, sin `created_at`) vs `MovementOutput` (con `id`, con `created_at`). Nunca el mismo modelo para ambos.
- **Validación en el límite del sistema** — Los DTOs de input son la primera línea de defensa. Si un dato pasa el DTO, el use case puede confiar en él.
- **snake_case en la API** — Consistente con Python. No usar `camelCase` ni aliases.
- **Strict mode en input** — `ConfigDict(strict=True)` previene coerción silenciosa de tipos (ej: `"123"` → `123`).
- **Value Objects no se exponen** — Los DTOs usan tipos primitivos (`str`, `int`, `float`). El use case construye los VOs (`SKU`, `Quantity`) a partir de los datos validados.
- **Formato de error consistente** — `ErrorResponse` con `{error: {code, message, details?}}` para todos los endpoints.

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| Input/Output separados (no unificados) | Claridad semántica: input = lo que el cliente envía, output = lo que el servidor retorna. Evita confusión con campos Optional |
| `strict=True` solo en input DTOs | Los output DTOs reciben datos ya validados del use case; strict mode innecesario y podría romper serialización |
| `snake_case` en API (no `camelCase`) | Consistente con Python, más simple (sin aliases), y el consumidor de la API es controlado por el equipo |
| Validación condicional de metadata en `CreateMovementInput` | `@model_validator(mode="after")` verifica que TRANSFER tenga origin/destination y ADJUSTMENT tenga reason. Falla antes de llegar al use case |
| SKU regex en DTO igual que en VO | Mismo patrón `^[A-Za-z0-9\-_]{1,50}$` en ambos lados para mensajes de error consistentes y fail-fast en el boundary HTTP |
| `ErrorResponse` con `code` machine-readable | Permite al consumidor de la API tomar decisiones programáticas sin parsear `message` |

---

## DTOs

### Movements

#### Input: `CreateMovementInput`

```python
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MovementTypeInput(str, Enum):
    """Tipo de movimiento de inventario (serializable a JSON)."""

    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"


class CreateMovementInput(BaseModel):
    """Datos de entrada para registrar un movimiento de stock.

    Ejemplo::

        {
            "product_id": 1,
            "movement_type": "IN",
            "quantity": 10,
            "metadata": {"supplier": "ACME"},
            "reference": "PO-12345"
        }
    """

    model_config = ConfigDict(strict=True)

    product_id: int = Field(
        gt=0,
        description="ID del producto al que afecta el movimiento.",
        json_schema_extra={"examples": [1]},
    )
    movement_type: MovementTypeInput = Field(
        description="Tipo de movimiento: IN, OUT, ADJUSTMENT, TRANSFER.",
        json_schema_extra={"examples": ["IN"]},
    )
    quantity: int = Field(
        gt=0,
        description="Cantidad positiva de unidades.",
        json_schema_extra={"examples": [10]},
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Datos contextuales. Obligatorio para TRANSFER y ADJUSTMENT.",
        json_schema_extra={"examples": [{"supplier": "ACME"}]},
    )
    reference: str | None = Field(
        default=None,
        max_length=255,
        description="Referencia externa opcional (orden, nota, etc.).",
        json_schema_extra={"examples": ["PO-12345"]},
    )

    @model_validator(mode="after")
    def validate_movement_metadata(self) -> "CreateMovementInput":
        """Valida metadata condicional segun el tipo de movimiento.

        TRANSFER requiere 'origin' y 'destination' en metadata.
        ADJUSTMENT requiere 'reason' en metadata.

        Raises:
            ValueError: Si la metadata es insuficiente para el tipo.
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
- `quantity: int` (no `int | float`) en el input — la API solo acepta enteros. El use case puede convertir si es necesario. Si en el futuro se necesitan decimales, se cambia a `int | float` sin romper el contrato.
- `metadata: dict[str, str]` — valores como strings para simplicidad. El use case puede interpretar los valores según el contexto.
- `@model_validator(mode="after")` se ejecuta después de la validación de campos individuales. Si `movement_type` es inválido, Pydantic ya lanzó antes de llegar aquí.

#### Output: `MovementOutput`

```python
from datetime import datetime

from pydantic import BaseModel, Field


class MovementOutput(BaseModel):
    """Datos de salida de un movimiento de stock.

    Ejemplo::

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

    id: int = Field(description="Identificador unico del movimiento.")
    product_id: int = Field(description="ID del producto afectado.")
    movement_type: str = Field(description="Tipo de movimiento.")
    quantity: int = Field(description="Cantidad de unidades.")
    metadata: dict[str, str] = Field(description="Datos contextuales.")
    reference: str | None = Field(description="Referencia externa.")
    created_at: datetime = Field(description="Fecha y hora UTC del movimiento.")
```

#### List Output: `MovementListOutput`

```python
from pydantic import BaseModel, Field


class MovementListOutput(BaseModel):
    """Respuesta paginada de lista de movimientos.

    Ejemplo::

        {
            "items": [...],
            "total": 150,
            "limit": 50,
            "offset": 0
        }
    """

    items: list[MovementOutput] = Field(description="Lista de movimientos.")
    total: int = Field(description="Total de movimientos disponibles.")
    limit: int = Field(description="Limite aplicado en la consulta.")
    offset: int = Field(description="Desplazamiento aplicado en la consulta.")
```

---

### Stock

#### Output: `CurrentStockOutput`

```python
from pydantic import BaseModel, Field


class CurrentStockOutput(BaseModel):
    """Stock actual de un producto.

    Ejemplo::

        {
            "product_id": 1,
            "current_stock": 42.0
        }
    """

    product_id: int = Field(description="ID del producto.")
    current_stock: float = Field(description="Stock actual (puede ser decimal).")
```

#### Output: `StockAtDateOutput`

```python
from datetime import datetime

from pydantic import BaseModel, Field


class StockAtDateOutput(BaseModel):
    """Stock de un producto en una fecha historica.

    Ejemplo::

        {
            "product_id": 1,
            "stock": 15.0,
            "date": "2025-01-01T00:00:00Z"
        }
    """

    product_id: int = Field(description="ID del producto.")
    stock: float = Field(description="Stock en la fecha especificada.")
    date: datetime = Field(description="Fecha de consulta.")
```

---

### Products

#### Input: `CreateProductInput`

```python
from pydantic import BaseModel, ConfigDict, Field


class CreateProductInput(BaseModel):
    """Datos de entrada para crear un producto.

    Ejemplo::

        {
            "sku": "PROD-001",
            "name": "Widget A",
            "unit_of_measure": "unit",
            "category_id": 1,
            "description": "Widget de prueba",
            "min_stock_threshold": 10
        }
    """

    model_config = ConfigDict(strict=True)

    sku: str = Field(
        min_length=1,
        max_length=50,
        pattern=r"^[A-Za-z0-9\-_]{1,50}$",
        description="Codigo SKU unico del producto.",
        json_schema_extra={"examples": ["PROD-001"]},
    )
    name: str = Field(
        min_length=1,
        max_length=255,
        description="Nombre del producto.",
        json_schema_extra={"examples": ["Widget A"]},
    )
    unit_of_measure: str = Field(
        min_length=1,
        max_length=50,
        description="Unidad de medida (e.g., 'unit', 'kg', 'liter').",
        json_schema_extra={"examples": ["unit"]},
    )
    category_id: int = Field(
        gt=0,
        description="ID de la categoria a la que pertenece.",
        json_schema_extra={"examples": [1]},
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
        description="Descripcion opcional del producto.",
        json_schema_extra={"examples": ["Widget de prueba"]},
    )
    min_stock_threshold: int = Field(
        default=0,
        ge=0,
        description="Umbral minimo de stock para alertas.",
        json_schema_extra={"examples": [10]},
    )
```

**Design Notes:**
- El patrón regex del SKU es idéntico al del VO `SKU` (`^[A-Za-z0-9\-_]{1,50}$`) para consistencia
- `category_id: int > 0` — el use case verificará que la categoría existe
- `min_stock_threshold: int >= 0` — validación de dominio reflejada en el DTO

#### Output: `ProductOutput`

```python
from datetime import datetime

from pydantic import BaseModel, Field


class ProductOutput(BaseModel):
    """Datos de salida de un producto.

    Ejemplo::

        {
            "id": 1,
            "sku": "PROD-001",
            "name": "Widget A",
            "description": "Widget de prueba",
            "unit_of_measure": "unit",
            "category_id": 1,
            "min_stock_threshold": 10,
            "created_at": "2025-05-18T14:30:00Z"
        }
    """

    id: int = Field(description="Identificador unico del producto.")
    sku: str = Field(description="Codigo SKU.")
    name: str = Field(description="Nombre del producto.")
    description: str | None = Field(description="Descripcion opcional.")
    unit_of_measure: str = Field(description="Unidad de medida.")
    category_id: int = Field(description="ID de la categoria.")
    min_stock_threshold: int = Field(description="Umbral minimo de stock.")
    created_at: datetime = Field(description="Fecha y hora UTC de creacion.")
```

#### List Output: `ProductListOutput`

```python
from pydantic import BaseModel, Field


class ProductListOutput(BaseModel):
    """Respuesta paginada de lista de productos.

    Ejemplo::

        {
            "items": [...],
            "total": 85,
            "limit": 50,
            "offset": 0
        }
    """

    items: list[ProductOutput] = Field(description="Lista de productos.")
    total: int = Field(description="Total de productos disponibles.")
    limit: int = Field(description="Limite aplicado en la consulta.")
    offset: int = Field(description="Desplazamiento aplicado en la consulta.")
```

---

### Categories

#### Input: `CreateCategoryInput`

```python
from pydantic import BaseModel, ConfigDict, Field


class CreateCategoryInput(BaseModel):
    """Datos de entrada para crear una categoria.

    Ejemplo::

        {
            "name": "Electronics",
            "description": "Productos electronicos"
        }
    """

    model_config = ConfigDict(strict=True)

    name: str = Field(
        min_length=1,
        max_length=100,
        description="Nombre de la categoria.",
        json_schema_extra={"examples": ["Electronics"]},
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Descripcion opcional de la categoria.",
        json_schema_extra={"examples": ["Productos electronicos"]},
    )
```

#### Output: `CategoryOutput`

```python
from datetime import datetime

from pydantic import BaseModel, Field


class CategoryOutput(BaseModel):
    """Datos de salida de una categoria.

    Ejemplo::

        {
            "id": 1,
            "name": "Electronics",
            "description": "Productos electronicos",
            "created_at": "2025-05-18T14:30:00Z"
        }
    """

    id: int = Field(description="Identificador unico de la categoria.")
    name: str = Field(description="Nombre de la categoria.")
    description: str | None = Field(description="Descripcion opcional.")
    created_at: datetime = Field(description="Fecha y hora UTC de creacion.")
```

---

### Error

#### `ErrorResponse`

```python
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detalle de un error de API.

    Ejemplo::

        {
            "code": "INSUFFICIENT_STOCK",
            "message": "Insufficient stock for product 1: requested 10, available 3",
            "details": {"product_id": 1, "requested": 10, "available": 3}
        }
    """

    code: str = Field(
        description="Codigo de error machine-readable (UPPER_SNAKE_CASE)."
    )
    message: str = Field(description="Mensaje legible para humanos.")
    details: dict[str, str | int | float] | None = Field(
        default=None,
        description="Contexto adicional del error (opcional).",
    )


class ErrorResponse(BaseModel):
    """Envoltura de respuesta de error.

    Todos los endpoints retornan este formato en caso de error.

    Ejemplo::

        {
            "error": {
                "code": "NOT_FOUND",
                "message": "Product 999 not found"
            }
        }
    """

    error: ErrorDetail = Field(description="Detalle del error.")
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
| `src/application/dtos/__init__.py` | Re-exports: todos los DTOs |

---

## Acceptance Criteria

- [ ] Todos los input DTOs usan `ConfigDict(strict=True)` para evitar coerction silenciosa
- [ ] `CreateMovementInput` valida metadata condicionalmente via `@model_validator(mode="after")`
- [ ] `CreateProductInput` valida SKU con regex `^[A-Za-z0-9\-_]{1,50}$` (mismo patron que VO `SKU`)
- [ ] Los input DTOs NO tienen campos `id` ni `created_at` (los genera el servidor)
- [ ] Los output DTOs SI tienen campos `id` y `created_at`
- [ ] `ErrorResponse` tiene formato consistente: `{error: {code, message, details?}}`
- [ ] Todos los DTOs incluyen `json_schema_extra` con ejemplos para OpenAPI
- [ ] `src/application/dtos/__init__.py` exporta todos los DTOs publicos
- [ ] `make lint` pasa sin errores en todos los archivos de DTOs

---

## Testing Strategy

- **Tests unitarios de validación de input** — Para cada input DTO:
  - Datos válidos: se construye sin error
  - Datos inválidos: lanza `ValidationError` con mensaje descriptivo
  - Campos requeridos omitidos: lanza `ValidationError`
  - Constraints (`gt=0`, `ge=0`, `min_length`, `max_length`, `pattern`): validar que se aplican

- **`CreateMovementInput` — validación condicional:**
  - TRANSFER sin origin/destination: `ValueError`
  - TRANSFER con origin y destination: OK
  - ADJUSTMENT sin reason: `ValueError`
  - ADJUSTMENT con reason: OK
  - IN/OUT con metadata vacía: OK
  - IN/OUT sin metadata: OK (default Factory)

- **`CreateProductInput` — SKU validation:**
  - SKU válido (`PROD-001`): OK
  - SKU vacío: `ValidationError`
  - SKU con caracteres especiales (`PROD@001`): `ValidationError`
  - SKU > 50 chars: `ValidationError`

- **Tests de serialización de output** — Construir cada output DTO, verificar que `model.model_dump_json()` produce JSON válido con los campos esperados

- **Tests de `ErrorResponse`** — Construir con cada tipo de error, verificar formato consistente

---

## Resolved Questions

1. **¿La API usa snake_case o camelCase para los campos JSON?** → **snake_case.** Consistente con Python, más simple (sin aliases), y el consumidor de la API es controlado por el equipo. Si en el futuro se necesita soporte para clientes frontend que exigen camelCase, se pueden añadir aliases sin romper el contrato interno.

2. **¿Incluir `CreateCategoryInput` y `CategoryOutput` en F4 o deferir?** → **Incluir en F4.** La categoría es un prerrequisito para crear productos (`CreateProductUseCase` verifica que la categoría existe). Sin un endpoint para crear categorías, el sistema no sería funcional para un cliente HTTP.

3. **¿`MovementListOutput` necesita paginación con `total`/`total_pages`?** → **Sí, con `total`, `limit`, `offset`.** El patrón consistente con `ProductListOutput`. `total_pages` no se incluye porque el cliente puede calcularlo (`ceil(total / limit)`). Añadirlo en el DTO añade ambigüedad (¿redondea hacia arriba? ¿hacia abajo?). El cálculo total/items es suficiente.
