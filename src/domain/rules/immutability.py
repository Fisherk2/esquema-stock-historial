"""Regla de inmutabilidad — valida que no se modifiquen entidades inmutables.

Funcion pura que verifica que las operaciones de modificacion o eliminacion
no se apliquen a entidades marcadas como inmutables (e.g., Movement).
"""

from src.domain.exceptions.immutability_violation import (
    ImmutabilityViolationError,
)

_IMMUTABLE_TYPES = frozenset({"Movement"})


def enforce_immutability(
    *,
    entity_type: str,
    entity_id: int,
    operation: str,
) -> None:
    """Valida que no se intente modificar una entidad inmutable.

    Args:
        entity_type: Nombre del tipo de entidad (e.g., "Movement").
        entity_id: ID de la entidad.
        operation: Operacion intentada ("create", "update", "delete").

    Raises:
        ImmutabilityViolationError: Si se intenta update o delete en una
            entidad inmutable.
    """
    if entity_type in _IMMUTABLE_TYPES and operation in ("update", "delete"):
        raise ImmutabilityViolationError(
            entity_type=entity_type,
            entity_id=entity_id,
        )
