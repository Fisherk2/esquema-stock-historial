"""PostgresMovementRepository — implementacion concreta de IMovementRepository.

Repositorio de movimientos con asyncpg y SQL explicito. Los movimientos
son inmutables (Source of Truth): este repositorio solo tiene metodos de
creacion y lectura — **no tiene** update() ni delete() porque los movimientos
son registros append-only que nunca se alteran.

Ejemplo de uso sin transaccion::

    repo = PostgresMovementRepository(pool)
    movement = await repo.create(Movement(id=None, ...))

Ejemplo de uso con Unit of Work::

    async with PostgresUnitOfWork(pool) as uow:
        repo = PostgresMovementRepository(pool, connection=uow.connection)
        movement = await repo.create(new_movement)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.domain.ports.movement_repository import IMovementRepository
from src.infrastructure.repositories.base_repository import BasePostgresRepository
from src.infrastructure.repositories.mappers import map_movement_row

if TYPE_CHECKING:
    from src.domain.entities.movement import Movement


class PostgresMovementRepository(BasePostgresRepository, IMovementRepository):
    """Repositorio de movimientos con asyncpg y SQL explicito."""

    _CREATE_SQL = """
        INSERT INTO movements (
            product_id, movement_type, quantity, metadata,
            reference, created_at
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING
            id, product_id, movement_type, quantity, metadata,
            reference, created_at
    """

    _GET_BY_ID_SQL = """
        SELECT
            id, product_id, movement_type, quantity, metadata,
            reference, created_at
        FROM movements
        WHERE id = $1
    """

    _LIST_BY_PRODUCT_SQL = """
        SELECT
            id, product_id, movement_type, quantity, metadata,
            reference, created_at
        FROM movements
        WHERE product_id = $1
        ORDER BY created_at DESC
        LIMIT $2 OFFSET $3
    """

    _COUNT_BY_PRODUCT_SQL = """
        SELECT COUNT(*) FROM movements WHERE product_id = $1
    """

    async def create(self, movement: Movement) -> Movement:
        """Persiste un nuevo movimiento y retorna la entidad con id asignado."""
        row = await self._get_conn().fetchrow(
            self._CREATE_SQL,
            movement.product_id,
            movement.movement_type.value,
            movement.quantity.value,
            movement.metadata,
            movement.reference,
            movement.created_at,
        )
        return map_movement_row(row)

    async def get_by_id(self, movement_id: int) -> Movement | None:
        """Recupera un movimiento por su ID."""
        row = await self._get_conn().fetchrow(self._GET_BY_ID_SQL, movement_id)
        if row is None:
            return None
        return map_movement_row(row)

    async def list_by_product(
        self,
        product_id: int,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Movement]:
        """Lista movimientos de un producto con paginacion."""
        rows = await self._get_conn().fetch(
            self._LIST_BY_PRODUCT_SQL, product_id, limit, offset
        )
        return [map_movement_row(r) for r in rows]

    async def count_by_product(self, product_id: int) -> int:
        """Cuenta el total de movimientos de un producto."""
        row = await self._get_conn().fetchrow(self._COUNT_BY_PRODUCT_SQL, product_id)
        return row["count"] if row else 0
