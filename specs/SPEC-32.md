# SPEC-32: Unit of Work & Transacciones

**Fase:** F3 — Adaptadores de Datos  
**Dependencias:** Spec-30 (Repositorio) ✅ Completado  
**Prioridad:** Media  
**Estado:** Pendiente  

---

## Objective

Implementar `PostgresUnitOfWork` como context manager asíncrono que gestiona transacciones `asyncpg` con commit/rollback determinístico. Permite compartir una conexión única entre múltiples repositorios, garantizando atomicidad en operaciones que afectan varias tablas.

**Principios de diseño:**
- **Conexión explícita** — no thread-local, no magic global state
- **Rollback automático en excepción** — `__aexit__` detecta excepción y revierte
- **Commit automático al salir limpiamente** — no requiere llamada explícita a `commit()`
- **Siempre libera la conexión al pool** — incluso si hay excepción en `__aexit__`
- **Protocolo en dominio** — `IUnitOfWork` definido como `typing.Protocol`

---

## Protocol: `IUnitOfWork`

Definido en `src/domain/ports/unit_of_work.py`:

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IUnitOfWork(Protocol):
    """Protocolo para gestión de transacciones.

    Permite compartir una conexión entre repositorios y garantizar
    atomicidad con commit/rollback determinístico.

    Ejemplo de uso::

        async with unit_of_work as uow:
            repo = PostgresMovementRepository(pool, connection=uow.connection)
            await repo.create(movement)
            # Al salir del context: commit automático
    """

    @property
    def connection(self) -> "asyncpg.Connection | None":
        """La conexión activa dentro de la transacción."""
        ...
```

---

## Implementation: `PostgresUnitOfWork`

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import asyncpg

from src.domain.ports.unit_of_work import IUnitOfWork

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class PostgresUnitOfWork(IUnitOfWork):
    """Context manager asíncrono para transacciones asyncpg.

    Adquiere una conexión del pool al entrar, inicia una transacción,
    y al salir:
    - Commit si no hubo excepción
    - Rollback si hubo excepción
    - Siempre libera la conexión al pool

    Atributos:
        connection: La conexión activa (None fuera del context).

    Ejemplo de uso::

        async with PostgresUnitOfWork(pool) as uow:
            movement_repo = PostgresMovementRepository(pool, connection=uow.connection)
            product_repo = PostgresProductRepository(pool, connection=uow.connection)

            movement = await movement_repo.create(new_movement)
            product = await product_repo.get_by_id(movement.product_id)
            # commit automático al salir del with
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """Inicializa con el pool de conexiones.

        Args:
            pool: Pool de conexiones asyncpg para adquirir conexión.
        """
        self._pool = pool
        self._connection: asyncpg.Connection | None = None
        self._transaction: asyncpg.Transaction | None = None

    @property
    def connection(self) -> asyncpg.Connection | None:
        """La conexión activa dentro de la transacción."""
        return self._connection

    async def __aenter__(self) -> PostgresUnitOfWork:
        """Adquiere conexión del pool e inicia transacción."""
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
        """Commit si no hay excepción, rollback si la hay."""
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
```

---

## Patrón de Uso

### Operación atómica: crear movimiento y verificar producto

```python
async with PostgresUnitOfWork(pool) as uow:
    # Todos los repos comparten la misma conexión
    movement_repo = PostgresMovementRepository(pool, connection=uow.connection)
    product_repo = PostgresProductRepository(pool, connection=uow.connection)

    # Verificar que el producto existe dentro de la misma transacción
    product = await product_repo.get_by_id(new_movement.product_id)
    if product is None:
        raise ValueError(f"Product {new_movement.product_id} not found")

    # Crear el movimiento — commit automático al salir
    result = await movement_repo.create(new_movement)
```

### Rollback automático en caso de error

```python
try:
    async with PostgresUnitOfWork(pool) as uow:
        repo = PostgresMovementRepository(pool, connection=uow.connection)
        await repo.create(invalid_movement)  # Esto lanza excepción
        # El rollback automático se ejecuta en __aexit__
except Exception:
    # La transacción se revirtió, ningún cambio persistido
    pass
```

### Sin Unit of Work (operaciones individuales)

```python
# Cuando no se necesita transacción entre múltiples operaciones:
repo = PostgresMovementRepository(pool, connection=None)
movement = await repo.create(new_movement)
# Cada operación obtiene y libera su propia conexión del pool
```

---

## Files

| File | Description |
|------|-------------|
| `src/domain/ports/unit_of_work.py` | `IUnitOfWork` Protocol |
| `src/infrastructure/db/uow.py` | `PostgresUnitOfWork` implementación |
| `src/domain/ports/__init__.py` | Re-export: `IUnitOfWork` |

---

## Acceptance Criteria

- [ ] `PostgresUnitOfWork` funciona como context manager asíncrono (`async with`)
- [ ] Rollback automático cuando una excepción ocurre dentro del context
- [ ] Commit automático al salir del context sin excepción
- [ ] Conexión compartida entre múltiples repositorios inyectada en constructor
- [ ] Conexión siempre liberada al pool (incluso si `__aexit__` falla)
- [ ] Tests de integración con `testcontainers.postgres` validan: commit, rollback, conexión compartida
- [ ] `IUnitOfWork` es verificable como Protocol con `isinstance(uow, IUnitOfWork)`

---

## Testing Strategy

- **Test de commit**: crear movimiento dentro de UoW, verificar que persiste tras salir del context
- **Test de rollback**: lanzar excepción dentro de UoW, verificar que no persiste
- **Test de conexión compartida**: crear 2 repos con la misma conexión, insertar y verificar que ambos operan en la misma transacción
- **Test de aislamiento**: verificar que operaciones fuera de UoW no ven cambios no commiteados

---

## Open Questions

1. ¿Debe `PostgresUnitOfWork` exponer métodos explícitos `commit()` y `rollback()` además del commit automático, para casos donde se necesite control manual?
2. ¿Debe el Protocol `IUnitOfWork` incluir los métodos async `commit()` y `rollback()` como parte del contrato, o solo la propiedad `connection`?
3. ¿Debe existir un `UnitOfWorkFactory` que cree los repositorios ya configurados con la conexión, en lugar de que el caller los instancie manualmente?
