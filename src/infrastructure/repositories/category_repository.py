"""PostgresCategoryRepository — implementacion concreta de ICategoryRepository.

Repositorio de categorias con asyncpg y SQL explicito.

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
from src.infrastructure.repositories.base_repository import BasePostgresRepository
from src.infrastructure.repositories.mappers import map_category_row

if TYPE_CHECKING:
    from src.domain.entities.category import Category


class PostgresCategoryRepository(BasePostgresRepository, ICategoryRepository):
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
        LIMIT $1 OFFSET $2
    """

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

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Category]:
        """Lista categorias con paginacion en base de datos."""
        rows = await self._get_conn().fetch(self._LIST_ALL_SQL, limit, offset)
        return [map_category_row(r) for r in rows]
