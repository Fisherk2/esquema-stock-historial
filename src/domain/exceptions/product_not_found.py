"""Error cuando un producto no existe en el repositorio.

Se lanza cuando un caso de uso intenta acceder a un producto
por ID y no se encuentra en la base de datos.
"""

from src.domain.exceptions.domain_error import DomainError


class ProductNotFoundError(DomainError):
    """El producto solicitado no existe.

    Args:
        product_id: ID del producto que no fue encontrado.
    """

    def __init__(self, product_id: int) -> None:
        self.product_id = product_id
        super().__init__(f"Product {product_id} not found")
