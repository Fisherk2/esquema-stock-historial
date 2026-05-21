"""Error cuando una categoria no existe en el repositorio.

Se lanza cuando un caso de uso intenta acceder a una categoria
por ID y no se encuentra en la base de datos.
"""

from src.domain.exceptions.domain_error import DomainError


class CategoryNotFoundError(DomainError):
    """La categoria solicitada no existe.

    Args:
        category_id: ID de la categoria que no fue encontrada.
    """

    def __init__(self, category_id: int) -> None:
        self.category_id = category_id
        super().__init__(f"Category {category_id} not found")
