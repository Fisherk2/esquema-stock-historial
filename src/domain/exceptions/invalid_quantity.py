"""InvalidQuantityError — cantidad invalida en un movimiento.

Se lanza cuando una cantidad es cero o negativa, violando el invariante
del dominio de que todos los movimientos de stock deben involucrar
cantidades estrictamente positivas.
"""

from src.domain.exceptions.domain_error import DomainError


class InvalidQuantityError(DomainError):
    """Excepcion lanzada cuando un valor de cantidad es invalido.

    Las cantidades deben ser estrictamente positivas (> 0). Los valores
    cero y negativos se rechazan a nivel del objeto de valor.

    Args:
        message: Descripcion legible del fallo de validacion.

    Ejemplo::

        >>> raise InvalidQuantityError("La cantidad debe ser positiva")
        Traceback (most recent call last):
        ...
        InvalidQuantityError: La cantidad debe ser positiva
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
