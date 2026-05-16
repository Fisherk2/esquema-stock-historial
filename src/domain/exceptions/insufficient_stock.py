"""InsufficientStockError — stock insuficiente para un movimiento.

Se lanza cuando un movimiento de stock resultaria en un valor negativo,
violando el invariante del dominio de que el stock nunca puede ser menor
a cero.
"""

from src.domain.exceptions.domain_error import DomainError


class InsufficientStockError(DomainError):
    """Excepcion lanzada cuando un movimiento causaria stock negativo.

    Lleva el contexto del producto, cantidad solicitada y stock disponible
    para que el caso de uso pueda construir una respuesta de error
    significativa.

    Args:
        product_id: ID del producto con stock insuficiente.
        requested: Cantidad solicitada en el movimiento.
        available: Stock actual disponible.

    Ejemplo::

        >>> raise InsufficientStockError(product_id=1, requested=10, available=3)
        Traceback (most recent call last):
        ...
        InsufficientStockError: Insufficient stock for product 1: ...  # noqa: E501
    """

    def __init__(
        self, *, product_id: int, requested: int | float, available: int | float
    ) -> None:
        self.product_id = product_id
        self.requested = requested
        self.available = available
        message = (
            f"Insufficient stock for product {product_id}: "
            f"requested {requested}, available {available}"
        )
        super().__init__(message)
