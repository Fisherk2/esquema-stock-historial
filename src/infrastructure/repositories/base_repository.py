"""Repositorio base para implementaciones Postgres con asyncpg.

Proporciona la gestion de conexion compartida entre repositorios:
un pool de conexiones y una conexion opcional para transacciones
(Unit of Work). Todos los repositorios concretos heredan de esta
clase para evitar duplicacion de ``__init__`` y ``_get_conn()``.

Ejemplo de uso::

    class MyRepository(BasePostgresRepository):
        _SOME_SQL = "SELECT * FROM my_table WHERE id = $1"

        async def get_by_id(self, entity_id: int) -> MyEntity | None:
            row = await self._get_conn().fetchrow(self._SOME_SQL, entity_id)
            return map_row(row) if row else None
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg


class BasePostgresRepository:
    """Clase base para repositorios que usan asyncpg.

    Args:
        pool: Pool de conexiones asyncpg (requerido).
        connection: Conexion activa para transacciones (opcional).
    """

    def __init__(
        self,
        pool: asyncpg.Pool,
        connection: asyncpg.Connection | None = None,
    ) -> None:
        self._pool = pool
        self._connection = connection

    def _get_conn(self) -> asyncpg.Pool | asyncpg.Connection:
        """Retorna la conexion activa o el pool."""
        return self._connection if self._connection else self._pool
