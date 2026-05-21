"""PostgresProductRepository — implementacion concreta de IProductRepository.

Repositorio de productos con asyncpg y SQL explicito. Incluye consulta
de stock bajo mediante CASE/SUM contra movimientos (optimizable con
vista materializada en Spec-31).

Ejemplo de uso sin transaccion::

    repo = PostgresProductRepository(pool)
    product = await repo.create(Product(id=None, sku=SKU("PROD-001"), ...))

Ejemplo de uso con Unit of Work::

    async with PostgresUnitOfWork(pool) as uow:
        repo = PostgresProductRepository(pool, connection=uow.connection)
        product = await repo.get_by_id(1)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.ports.product_repository import IProductRepository
from src.infrastructure.repositories.base_repository import BasePostgresRepository
from src.infrastructure.repositories.mappers import map_product_row

if TYPE_CHECKING:
    from src.domain.entities.product import Product


class PostgresProductRepository(BasePostgresRepository, IProductRepository):
    """Repositorio de productos con asyncpg y SQL explicito."""

    async def create(self, product: Product) -> Product:
        """Persiste un nuevo producto y retorna la entidad con id asignado."""
        row = await self._get_conn().fetchrow(
            self._CREATE_SQL,
            product.sku.value,
            product.name,
            product.description,
            product.unit_of_measure,
            product.category_id,
            product.min_stock_threshold,
            product.created_at,
        )
        return map_product_row(row)

    async def get_by_id(self, product_id: int) -> Product | None:
        """Recupera un producto por su ID."""
        row = await self._get_conn().fetchrow(self._GET_BY_ID_SQL, product_id)
        return map_product_row(row) if row else None

    async def get_by_sku(self, sku: str) -> Product | None:
        """Recupera un producto por su SKU."""
        row = await self._get_conn().fetchrow(self._GET_BY_SKU_SQL, sku)
        return map_product_row(row) if row else None

    async def list_all(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Product]:
        """Lista productos con paginacion."""
        rows = await self._get_conn().fetch(self._LIST_ALL_SQL, limit, offset)
        return [map_product_row(r) for r in rows]

    async def count_all(self) -> int:
        """Cuenta el total de productos en el inventario."""
        row = await self._get_conn().fetchrow(self._COUNT_ALL_SQL)
        return row["count"] if row else 0

    async def list_below_threshold(
        self,
        *,
        limit: int = 100,
    ) -> list[Product]:
        """Lista productos con stock por debajo del umbral minimo."""
        rows = await self._get_conn().fetch(self._LIST_BELOW_THRESHOLD_SQL, limit)
        return [map_product_row(r) for r in rows]
