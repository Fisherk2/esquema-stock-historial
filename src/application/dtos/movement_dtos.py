"""DTOs de movimientos — input para crear, output para consultar."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — Pydantic needs runtime datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MovementTypeInput(str, Enum):  # noqa: UP042 — Pydantic serialization needs str mixin
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
    def validate_movement_metadata(self) -> CreateMovementInput:
        """Valida metadata condicional segun el tipo de movimiento.

        TRANSFER requiere 'origin' y 'destination' en metadata.
        ADJUSTMENT requiere 'reason' en metadata.

        Raises:
            ValueError: Si la metadata es insuficiente para el tipo.
        """
        if self.movement_type == MovementTypeInput.TRANSFER and (
            "origin" not in self.metadata or "destination" not in self.metadata
        ):
            raise ValueError(
                "TRANSFER movement requires 'origin' and 'destination' in metadata"
            )
        elif (
            self.movement_type == MovementTypeInput.ADJUSTMENT
            and "reason" not in self.metadata
        ):
            raise ValueError("ADJUSTMENT movement requires 'reason' in metadata")
        return self


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
