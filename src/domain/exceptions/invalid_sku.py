"""InvalidSKUError — formato de SKU invalido.

Se lanza cuando un codigo SKU no cumple el patron requerido: no vacio,
maximo 50 caracteres, solo alfanumericos con guiones y guiones bajos.
"""

from src.domain.exceptions.domain_error import DomainError


class InvalidSKUError(DomainError):
    """Excepcion lanzada cuando un valor de SKU es invalido.

    El SKU debe coincidir con el patron ``[A-Za-z0-9\\\\-_]{1,50}``.

    Args:
        message: Descripcion legible del fallo de validacion.

    Ejemplo::

        >>> raise InvalidSKUError("Formato de SKU invalido")
        Traceback (most recent call last):
        ...
        InvalidSKUError: Formato de SKU invalido
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
