"""PostgresUnitOfWork — context manager para transacciones asyncpg.

Adquiere una conexion del pool al entrar, inicia una transaccion,
y al salir:
- Commit si no hubo excepcion
- Rollback si hubo excepcion
- Siempre libera la conexion al pool

No expone metodos commit() ni rollback() — el control es automatico
via el context manager.

Ejemplo de uso::

    async with PostgresUnitOfWork(pool) as uow:
        movement_repo = PostgresMovementRepository(
            pool, connection=uow.connection
        )
        product_repo = PostgresProductRepository(
            pool, connection=uow.connection
        )

        movement = await movement_repo.create(new_movement)
        product = await product_repo.get_by_id(movement.product_id)
        # commit automatico al salir del with
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.domain.ports.unit_of_work import IUnitOfWork

if TYPE_CHECKING:
    import asyncpg

logger = logging.getLogger(__name__)


class PostgresUnitOfWork(IUnitOfWork):
    """Context manager asincrono para transacciones asyncpg.

    Adquiere una conexion del pool al entrar, inicia una transaccion,
    y al salir:
    - Commit si no hubo excepcion
    - Rollback si hubo excepcion
    - Siempre libera la conexion al pool
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """Inicializa con el pool de conexiones.

        Args:
            pool: Pool de conexiones asyncpg para adquirir conexion.
        """
        self._pool = pool
        self._connection: asyncpg.Connection | None = None
        self._transaction: asyncpg.Transaction | None = None

    @property
    def connection(self) -> asyncpg.Connection | None:
        """La conexion activa dentro de la transaccion."""
        return self._connection

    async def __aenter__(self) -> PostgresUnitOfWork:
        """Adquiere conexion del pool e inicia transaccion."""
        self._connection = await self._pool.acquire()
        self._transaction = self._connection.transaction()
        await self._transaction.start()
        logger.debug("UnitOfWork transaction started")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Commit si no hay excepcion, rollback si la hay."""
        try:
            if exc_type is None:
                await self._transaction.commit()
                logger.debug("UnitOfWork transaction committed")
            else:
                await self._transaction.rollback()
                logger.debug("UnitOfWork transaction rolled back")
        except Exception:
            logger.exception("Error during transaction commit/rollback")
            raise
        finally:
            if self._connection is not None:
                await self._pool.release(self._connection)
                self._connection = None
                self._transaction = None
                logger.debug("UnitOfWork connection released to pool")
