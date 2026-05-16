"""ImmutabilityViolationError — intento de modificacion de entidad inmutable.

Se lanza cuando se intenta actualizar o eliminar una entidad marcada
como inmutable a nivel de arquitectura (por ejemplo, los registros
de Movement).
"""

from src.domain.exceptions.domain_error import DomainError


class ImmutabilityViolationError(DomainError):
    """Excepcion lanzada cuando se modifica una entidad inmutable.

    Lleva el tipo de entidad y su ID para registro y reporte de errores.

    Args:
        entity_type: Nombre del tipo de entidad (p. ej., "Movement").
        entity_id: ID de la entidad que se intento modificar.

    Ejemplo::

        >>> raise ImmutabilityViolationError(entity_type="Movement", entity_id=42)
        Traceback (most recent call last):
        ...
        ImmutabilityViolationError: Cannot modify immutable Movement (id=42)
    """

    def __init__(self, *, entity_type: str, entity_id: int) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        message = f"Cannot modify immutable {entity_type} (id={entity_id})"
        super().__init__(message)
