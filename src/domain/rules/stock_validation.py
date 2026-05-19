"""Reglas de validacion de stock — funciones puras sin estado ni I/O.

Estas funciones calculan deltas de stock y validan que las operaciones
no resulten en stock negativo. Son puras: no modifican estado, no hacen
I/O, y su salida depende exclusivamente de sus parametros de entrada.
"""

from src.domain.exceptions.insufficient_stock import InsufficientStockError
from src.domain.value_objects.movement_type import MovementType


def calculate_stock_delta(
    movement_type: MovementType,
    quantity: int | float,
) -> int | float:
    """Calcula el delta de stock que produce un movimiento.

    Args:
        movement_type: Tipo de movimiento.
        quantity: Cantidad del movimiento (siempre positiva).

    Returns:
        Delta de stock: positivo para IN/ADJUSTMENT, negativo para
        OUT/TRANSFER.
    """
    if movement_type in (MovementType.IN, MovementType.ADJUSTMENT):
        return quantity
    return -quantity


def validate_stock_not_negative(
    movement_type: MovementType,
    quantity: int | float,
    current_stock: int | float,
    product_id: int,
) -> None:
    """Valida que un movimiento no resulte en stock negativo.

    Solo aplica a movimientos que reducen stock (OUT, TRANSFER).
    IN y ADJUSTMENT siempre incrementan stock y nunca fallan.

    Args:
        movement_type: Tipo de movimiento.
        quantity: Cantidad del movimiento.
        current_stock: Stock actual disponible del producto.
        product_id: ID del producto para incluir en el error.

    Raises:
        InsufficientStockError: Si el movimiento dejaria el stock
            en negativo.
    """
    delta = calculate_stock_delta(movement_type, quantity)
    if current_stock + delta < 0:
        raise InsufficientStockError(
            product_id=product_id,
            requested=quantity,
            available=current_stock,
        )
