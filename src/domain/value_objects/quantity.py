"""Quantity value object — cantidad positiva de un movimiento de stock.

Representa la cantidad de unidades en un movimiento de inventario.
El valor debe ser estrictamente positivo (> 0). Valores cero o negativos
violan el invariante del dominio y lanzan ``InvalidQuantityError``.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.exceptions.invalid_quantity import InvalidQuantityError


@dataclass(frozen=True)
class Quantity:
    """Cantidad positiva de unidades en un movimiento.

    Invariante: ``value > 0``. Se valida en ``__post_init__``.

    Args:
        value: Valor numerico de la cantidad (int o float, debe ser > 0).

    Raises:
        InvalidQuantityError: Si el valor es cero o negativo.

    Example::

        >>> Quantity(10)
        Quantity(value=10)
        >>> Quantity(0)  # doctest: +IGNORE_EXCEPTION_DETAIL
        InvalidQuantityError: Quantity must be positive, got 0
    """

    value: int | float

    def __post_init__(self) -> None:
        """Valida que el valor sea estrictamente positivo.

        Raises:
            InvalidQuantityError: Si value <= 0.
        """
        if self.value <= 0:
            raise InvalidQuantityError(f"Quantity must be positive, got {self.value}")
