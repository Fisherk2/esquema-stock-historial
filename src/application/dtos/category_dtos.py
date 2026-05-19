"""DTOs de categorias — input para crear, output para consultar."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — Pydantic needs runtime datetime

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
