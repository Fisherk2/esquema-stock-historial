"""SKU value object — identificador unico de producto.

Representa el Stock Keeping Unit (SKU) de un producto. El valor debe
ser no vacio, maximo 50 caracteres, y solo contener alfanumericos,
guiones y guiones bajos: ``[A-Za-z0-9\\-_]{1,50}``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.domain.exceptions.invalid_sku import InvalidSKUError

_SKU_PATTERN = re.compile(r"^[A-Za-z0-9\-_]{1,50}$")


@dataclass(frozen=True)
class SKU:
    """Identificador unico de producto (Stock Keeping Unit).

    Invariante: ``value`` debe coincidir con ``[A-Za-z0-9\\-_]{1,50}``.

    Args:
        value: Codigo SKU del producto.

    Raises:
        InvalidSKUError: Si el valor no cumple el patron.

    Example::

        >>> SKU("PROD-001")
        SKU(value='PROD-001')
        >>> SKU("")  # doctest: +IGNORE_EXCEPTION_DETAIL
        InvalidSKUError: Invalid SKU format:
    """

    value: str

    def __post_init__(self) -> None:
        """Valida que el SKU cumpla el patron requerido.

        Raises:
            InvalidSKUError: Si el valor no es valido.
        """
        if not _SKU_PATTERN.match(self.value):
            raise InvalidSKUError(
                f"Invalid SKU format: '{self.value}'. "
                "Must be 1-50 chars, alphanumeric with hyphens/underscores."
            )
