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
from src.infrastructure.repositories.mappers import map_product_row

if TYPE_CHECKING:
    import asyncpg

    from src.domain.entities.product import Product


class PostgresProductRepository(IProductRepository):
    """Repositorio de productos con asyncpg y SQL explicito."""

    _CREATE_SQL = """
        INSERT INTO products (
            sku, name, description, unit_of_measure,
            category_id, min_stock_threshold, created_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING
            id, sku, name, description, unit_of_measure,
            category_id, min_stock_threshold, created_at
    """

    _GET_BY_ID_SQL = """
        SELECT
            id, sku, name, description, unit_of_measure,
            category_id, min_stock_threshold, created_at
        FROM products
        WHERE id = $1
    """

    _GET_BY_SKU_SQL = """
        SELECT
            id, sku, name, description, unit_of_measure,
            category_id, min_stock_threshold, created_at
        FROM products
        WHERE sku = $1
    """

    _LIST_ALL_SQL = """
        SELECT
            id, sku, name, description, unit_of_measure,
            category_id, min_stock_threshold, created_at
        FROM products
        ORDER BY id
        LIMIT $1 OFFSET $2
    """

    _LIST_BELOW_THRESHOLD_SQL = """
        SELECT
            p.id, p.sku, p.name, p.description,
            p.unit_of_measure, p.category_id,
            p.min_stock_threshold, p.created_at
        FROM products p
        LEFT JOIN movements m ON m.product_id = p.id
        GROUP BY p.id
        HAVING COALESCE(
            SUM(
                CASE m.movement_type
                    WHEN 'IN' THEN m.quantity
                    WHEN 'OUT' THEN -m.quantity
                    WHEN 'ADJUSTMENT' THEN m.quantity
                    WHEN 'TRANSFER' THEN -m.quantity
                    ELSE 0
                END
            ), 0
        ) < p.min_stock_threshold
        LIMIT $1
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

    async def list_below_threshold(
        self,
        *,
        limit: int = 100,
    ) -> list[Product]:
        """Lista productos con stock por debajo del umbral minimo."""
        rows = await self._get_conn().fetch(
            self._LIST_BELOW_THRESHOLD_SQL, limit
        )
        return [map_product_row(r) for r in rows]
