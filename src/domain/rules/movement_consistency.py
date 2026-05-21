"""Regla de consistencia de tipo de movimiento — valida metadata requerida.

Funcion pura que verifica que el metadata de un movimiento sea consistente
con su tipo. Es la **unica fuente de verdad** para esta validacion.

Se invoca desde ``Movement.__post_init__`` al construir la entidad.
Los use cases NO llaman esta funcion directamente (evita duplicacion).
"""

from typing import Any

from src.domain.value_objects.movement_type import MovementType


def validate_movement_type_consistency(
    movement_type: MovementType,
    metadata: dict[str, Any],
) -> None:
    """Valida que el metadata sea consistente con el tipo de movimiento.

    Unica fuente de verdad para esta regla — se invoca desde
    ``Movement.__post_init__``. Los use cases NO deben llamarla
    directamente.

    Args:
        movement_type: Tipo de movimiento.
        metadata: Diccionario de metadata del movimiento.

    Raises:
        ValueError: Si TRANSFER no tiene origin/destination o
            ADJUSTMENT no tiene reason.
    """
    if movement_type == MovementType.TRANSFER and (
        "origin" not in metadata or "destination" not in metadata
    ):
        raise ValueError("TRANSFER requires 'origin' and 'destination' in metadata")
    elif movement_type == MovementType.ADJUSTMENT and "reason" not in metadata:
        raise ValueError("ADJUSTMENT requires 'reason' in metadata")
