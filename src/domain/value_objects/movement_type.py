"""MovementType enum — tipos atomicos de movimiento de inventario.

Los 4 valores mapean 1:1 al ENUM de PostgreSQL ``movement_type``.
Cada movimiento es inmutable y representa una operacion atomica
sobre el stock de un producto.
"""

from enum import Enum


class MovementType(str, Enum):  # noqa: UP042 — plan specifies Enum, not StrEnum
    """Tipo de movimiento de inventario.

    Attributes:
        IN: Entrada de stock (compra, devolucion, produccion).
        OUT: Salida de stock (venta, consumo, merma).
        ADJUSTMENT: Ajuste de stock (correccion de inventario, siempre +qty).
        TRANSFER: Transferencia entre ubicaciones (un solo registro atomico).
    """

    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"
    TRANSFER = "TRANSFER"
