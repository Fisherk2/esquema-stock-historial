"""IUnitOfWork port — interfaz para gestion de transacciones.

Define el contrato minimo para compartir una conexion entre
repositorios y garantizar atomicidad con commit/rollback
deterministico. Solo expone la propiedad ``connection``.

Ejemplo de uso::

    async with unit_of_work as uow:
        repo = PostgresMovementRepository(pool, connection=uow.connection)
        await repo.create(movement)
        # Al salir del context: commit automatico
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import asyncpg


@runtime_checkable
class IUnitOfWork(Protocol):
    """Protocolo para gestion de transacciones.

    Permite compartir una conexion entre repositorios y garantizar
    atomicidad con commit/rollback deterministico.
    """

    @property
    def connection(self) -> asyncpg.Connection | None:
        """La conexion activa dentro de la transaccion."""
        ...

    async def __aenter__(self) -> IUnitOfWork:
        """Adquiere conexion e inicia transaccion."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Commit si no hay excepcion, rollback si la hay."""
        ...
