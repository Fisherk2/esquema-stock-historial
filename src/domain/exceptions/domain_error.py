"""Excepcion base para todos los errores de la capa de dominio.

Todas las excepciones de dominio heredan de esta clase, lo que permite
capturar errores del dominio de forma agrupada en el limite de la
aplicacion.

Ejemplo::

    try:
        validate_stock_not_negative(MovementType.OUT, 10, 5)
    except DomainError as e:
        logger.error(f"Violacion de dominio: {e}")
"""


class DomainError(Exception):
    """Excepcion base para errores de la capa de dominio.

    Raiz de la jerarquia de excepciones del dominio. Todas las excepciones
    especificas (``InsufficientStockError``, ``InvalidSKUError``, etc.)
    heredan de esta clase.

    Args:
        message: Descripcion legible de la violacion de dominio.

    Ejemplo::

        >>> raise DomainError("El stock no puede ser negativo")
        Traceback (most recent call last):
        ...
        DomainError: El stock no puede ser negativo
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
