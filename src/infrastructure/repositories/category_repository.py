"""PostgresCategoryRepository — implementacion concreta de ICategoryRepository.

Repositorio de categorias con asyncpg y SQL explicito. Sin paginacion
en list_all: se espera un conjunto pequeno de categorias.

Ejemplo de uso sin transacción::

    repo = PostgresCategoryRepository(pool)
    category = await repo.create(Category(id=None, name="Electronics", ...))

Ejemplo de uso con Unit of Work::

    async with PostgresUnitOfWork(pool) as uow:
        repo = PostgresCategoryRepository(pool, connection=uow.connection)
        category = await repo.create(new_category)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.ports.category_repository import ICategoryRepository
from src.infrastructure.repositories.mappers import map_category_row

if TYPE_CHECKING:
    import asyncpg

    from src.domain.entities.category import Category


class PostgresCategoryRepository(ICategoryRepository):
    """Repositorio de categorias con asyncpg y SQL explicito."""

    _CREATE_SQL = """
        INSERT INTO categories (name, description, created_at)
        VALUES ($1, $2, $3)
        RETURNING id, name, description, created_at
    """

    _GET_BY_ID_SQL = """
        SELECT id, name, description, created_at
        FROM categories
        WHERE id = $1
    """

    _LIST_ALL_SQL = """
        SELECT id, name, description, created_at
        FROM categories
        ORDER BY name
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        connection: asyncpg.Connection | None = None,
    ) -> None:
        """Inicializa el repositorio con pool y conexion opcional.

        Args:
            pool: Pool de conexiones asyncpg (requerido).
            connection: Conexion activa para transacciones (opcional).
        """
        self._pool = pool
        self._connection = connection

    def _get_conn(self) -> asyncpg.Pool | asyncpg.Connection:
        """Retorna la conexion activa o el pool."""
        return self._connection if self._connection else self._pool

    async def create(self, category: Category) -> Category:
        """Persiste una nueva categoria y retorna la entidad con id asignado."""
        row = await self._get_conn().fetchrow(
            self._CREATE_SQL,
            category.name,
            category.description,
            category.created_at,
        )
        return map_category_row(row)

    async def get_by_id(self, category_id: int) -> Category | None:
        """Recupera una categoria por su ID."""
        row = await self._get_conn().fetchrow(self._GET_BY_ID_SQL, category_id)
        if row is None:
            return None
        return map_category_row(row)

    async def list_all(self) -> list[Category]:
        """Lista todas las categorias ordenadas por nombre."""
        rows = await self._get_conn().fetch(self._LIST_ALL_SQL)
        return [map_category_row(r) for r in rows]
