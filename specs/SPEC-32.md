# SPEC-32: Unit of Work & Transactions

**Phase:** F3 — Data Adapters  
**Dependencies:** Spec-30 (Repository) ✅ Completed  
**Priority:** Medium  
**Status:** Pending  

---

## Objective

Implement `PostgresUnitOfWork` as an async context manager that manages `asyncpg` transactions with deterministic commit/rollback. Allows sharing a single connection across multiple repositories, guaranteeing atomicity in operations that affect multiple tables.

**Design principles:**
- **Explicit connection** — no thread-local, no magic global state
- **Automatic rollback on exception** — `__aexit__` detects exception and reverts
- **Automatic commit on clean exit** — no explicit `commit()` call required
- **Always releases connection to pool** — even if exception occurs in `__aexit__`
- **Protocol in domain** — `IUnitOfWork` defined as `typing.Protocol`

---

## Protocol: `IUnitOfWork`

Defined in `src/domain/ports/unit_of_work.py`:

```python
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IUnitOfWork(Protocol):
    """Protocol for transaction management.

    Allows sharing a connection between repositories and guaranteeing
    atomicity with deterministic commit/rollback.

    Usage example::

        async with unit_of_work as uow:
            repo = PostgresMovementRepository(pool, connection=uow.connection)
            await repo.create(movement)
            # On context exit: automatic commit
    """

    @property
    def connection(self) -> "asyncpg.Connection | None":
        """The active connection within the transaction."""
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
    """Async context manager for asyncpg transactions.

    Acquires a connection from the pool on entry, starts a transaction,
    and on exit:
    - Commit if no exception occurred
    - Rollback if exception occurred
    - Always releases the connection to the pool

    Attributes:
        connection: The active connection (None outside the context).

    Usage example::

        async with PostgresUnitOfWork(pool) as uow:
            movement_repo = PostgresMovementRepository(pool, connection=uow.connection)
            product_repo = PostgresProductRepository(pool, connection=uow.connection)

            movement = await movement_repo.create(new_movement)
            product = await product_repo.get_by_id(movement.product_id)
            # automatic commit on with block exit
    """

    def __init__(self, pool: asyncpg.Pool) -> None:
        """Initialize with the connection pool.

        Args:
            pool: asyncpg connection pool to acquire connection from.
        """
        self._pool = pool
        self._connection: asyncpg.Connection | None = None
        self._transaction: asyncpg.Transaction | None = None

    @property
    def connection(self) -> asyncpg.Connection | None:
        """The active connection within the transaction."""
        return self._connection

    async def __aenter__(self) -> PostgresUnitOfWork:
        """Acquire connection from pool and start transaction."""
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
        """Commit if no exception, rollback if there is one.

        If rollback fails and there was already an active exception, the
        rollback error is logged but the original exception is re-raised
        (which is more important for the caller).
        """
        if self._transaction is None:
            return
        try:
            if exc_type is None:
                await self._transaction.commit()
                logger.debug("UnitOfWork transaction committed")
            else:
                await self._transaction.rollback()
                logger.debug("UnitOfWork transaction rolled back")
        except Exception as tx_exc:
            if exc_type is not None:
                # There was already an active exception: log the rollback
                # error but re-raise the original exception.
                logger.exception(
                    "Error during rollback (original exception preserved): %s", tx_exc
                )
            else:
                # No prior exception: the commit/rollback error is
                # the main problem.
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

## Usage Pattern

### Atomic operation: create movement and verify product

```python
async with PostgresUnitOfWork(pool) as uow:
    # All repositories share the same connection
    movement_repo = PostgresMovementRepository(pool, connection=uow.connection)
    product_repo = PostgresProductRepository(pool, connection=uow.connection)

    # Verify that the product exists within the same transaction
    product = await product_repo.get_by_id(new_movement.product_id)
    if product is None:
        raise ValueError(f"Product {new_movement.product_id} not found")

    # Create the movement — automatic commit on exit
    result = await movement_repo.create(new_movement)
```

### Automatic rollback on error

```python
try:
    async with PostgresUnitOfWork(pool) as uow:
        repo = PostgresMovementRepository(pool, connection=uow.connection)
        await repo.create(invalid_movement)  # This raises an exception
        # Automatic rollback executes in __aexit__
except Exception:
    # The transaction was rolled back, no changes persisted
    pass
```

### Without Unit of Work (individual operations)

```python
# When no transaction is needed across multiple operations:
repo = PostgresMovementRepository(pool, connection=None)
movement = await repo.create(new_movement)
# Each operation acquires and releases its own connection from the pool
```

---

## Files

| File | Description |
|------|-------------|
| `src/domain/ports/unit_of_work.py` | `IUnitOfWork` Protocol |
| `src/infrastructure/db/uow.py` | `PostgresUnitOfWork` implementation |
| `src/domain/ports/__init__.py` | Re-export: `IUnitOfWork` |

---

## Acceptance Criteria

- [ ] `PostgresUnitOfWork` works as an async context manager (`async with`)
- [ ] Automatic rollback when an exception occurs within the context
- [ ] Automatic commit when exiting the context without exception
- [ ] **If rollback fails with active exception:** error is logged but original exception is preserved (not suppressed)
- [ ] Shared connection across multiple repositories injected in constructor
- [ ] Connection always released to pool (even if `__aexit__` fails)
- [ ] `__aexit__` returns early if `self._transaction is None` (idempotency)
- [ ] Integration tests with `testcontainers.postgres` validate: commit, rollback, shared connection, failed rollback
- [ ] `IUnitOfWork` is verifiable as Protocol with `isinstance(uow, IUnitOfWork)`

---

## Testing Strategy

- **Commit test**: create movement within UoW, verify it persists after exiting context
- **Rollback test**: raise exception within UoW, verify it does not persist
- **Shared connection test**: create 2 repos with the same connection, insert and verify both operate in the same transaction
- **Isolation test**: verify that operations outside UoW do not see uncommitted changes
- **Failed rollback test**: simulate error in rollback with active exception, verify original exception is preserved

---

## Resolved Questions

1. **Should `PostgresUnitOfWork` expose explicit `commit()` and `rollback()` methods?** → **Automatic only.** Commit and rollback are handled exclusively via the context manager (`async with`). If an intermediate savepoint is needed in the future, it can be added without breaking the existing pattern. Simple and explicit.

2. **Should the `IUnitOfWork` Protocol include `commit()` and `rollback()`?** → **Only the `connection` property.** The Protocol defines the minimum contract: access to the active transaction connection. The `commit()`/`rollback()` methods are implementation details of the context manager, not part of the public contract.

3. **Should there be a `UnitOfWorkFactory`?** → **No.** The caller instantiates repositories manually by passing `uow.connection` to the constructor. This pattern is explicit and easy to understand. A factory would add an unnecessary layer of indirection with no tangible benefit.
