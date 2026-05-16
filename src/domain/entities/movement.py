"""Movement entity — registros atomicos e inmutables de movimiento de stock.

Cada movimiento representa una operacion atomica sobre el inventario:
entrada, salida, ajuste o transferencia. La entidad es inmutable
(frozen dataclass) para garantizar la integridad del Source of Truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from src.domain.value_objects.movement_type import MovementType

if TYPE_CHECKING:
    from src.domain.value_objects.quantity import Quantity


def _utc_now() -> datetime:
    """Devuelve la fecha y hora actual en UTC."""
    return datetime.now(tz=UTC)


@dataclass(frozen=True)
class Movement:
    """Registro inmutable de un movimiento de inventario.

    Cada movimiento es atomico e inalterable. No existen operaciones
    de update ni delete — solo creacion.

    Invariantes:
        - TRANSFER requiere metadata con ``origin`` y ``destination``.
        - ADJUSTMENT requiere metadata con ``reason``.
        - ``__hash__ = None`` — la entidad se identifica por id, no por valor.

    Args:
        id: Identificador unico (None antes de persistir).
        product_id: ID del producto afectado.
        movement_type: Tipo de movimiento (IN, OUT, ADJUSTMENT, TRANSFER).
        quantity: Cantidad de unidades (siempre positiva).
        metadata: Datos adicionales segun el tipo de movimiento.
        created_at: Marca de tiempo UTC del movimiento.
        reference: Referencia externa opcional (numero de orden, etc.).
    """

    id: int | None
    product_id: int
    movement_type: MovementType
    quantity: Quantity
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)
    reference: str | None = None

    __hash__ = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        """Valida consistencia de metadata segun el tipo de movimiento.

        Raises:
            ValueError: Si TRANSFER no tiene origin/destination o
                ADJUSTMENT no tiene reason en metadata.
        """
        if self.movement_type == MovementType.TRANSFER and (
            "origin" not in self.metadata or "destination" not in self.metadata
        ):
            raise ValueError(
                "TRANSFER movement requires 'origin' and " "'destination' in metadata"
            )
        if (
            self.movement_type == MovementType.ADJUSTMENT
            and "reason" not in self.metadata
        ):
            raise ValueError("ADJUSTMENT movement requires 'reason' in metadata")
