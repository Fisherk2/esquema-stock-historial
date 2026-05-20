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

import json  # Serializa dict → str para columna JSONB (asyncpg 0.31.0 + Python 3.14)
from typing import TYPE_CHECKING

import asyncpg

from src.domain.ports.movement_repository import IMovementRepository
from src.infrastructure.repositories.mappers import map_movement_row

if TYPE_CHECKING:

    from src.domain.entities.movement import Movement


class PostgresMovementRepository(IMovementRepository):
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

    async def create(self, movement: Movement) -> Movement:
        """Persiste un nuevo movimiento y retorna la entidad con id asignado."""
        try:
            row = await self._get_conn().fetchrow(
                self._CREATE_SQL,
                movement.product_id,
                movement.movement_type.value,
                movement.quantity.value,
                json.dumps(movement.metadata),
                movement.reference,
                movement.created_at,
            )
        except asyncpg.PostgresError as exc:
            raise ValueError(f"Database error: {exc}") from exc
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
