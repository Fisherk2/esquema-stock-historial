"""DTOs de productos — input para crear, output para consultar."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — Pydantic needs runtime datetime

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
