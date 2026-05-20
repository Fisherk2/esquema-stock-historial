"""Excepcion para conflictos de concurrencia.

Se lanza cuando una operación falla debido a un conflicto de
concurrencia (ej: dos transacciones intentando modificar los
mismos datos simultaneamente). El caller debe reintentar la
operación.

Ejemplo::

    from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError

    raise ConcurrencyConflictError(
        operation="refresh_view",
        detail="serialization failure",
    )
"""

from src.domain.exceptions.domain_error import DomainError


class ConcurrencyConflictError(DomainError):
    """Conflicto de concurrencia en operacion.

    Indica que la operacion no pudo completarse porque otro proceso
    modifico los mismos datos simultaneamente. Se recomienda reintentar
    con backoff exponencial.

    Args:
        operation: Nombre de la operacion que genero el conflicto.
        detail: Detalle adicional del conflicto (opcional).

    Ejemplo::

        >>> raise ConcurrencyConflictError(operation="refresh_view")
        Traceback (most recent call last):
        ...
        ConcurrencyConflictError: Concurrency conflict on 'refresh_view'
    """

    def __init__(self, operation: str, detail: str | None = None) -> None:
        self.operation = operation
        self.detail = detail
        message = f"Concurrency conflict on '{operation}'"
        if detail:
            message = f"{message}: {detail}"
        super().__init__(message)
