# SPEC-51: Optimistic Concurrency & Retry

**Phase:** F5 — Scheduler & Concurrency  
**Dependencies:** Spec-40 (Use Cases) ✅ Completed, Spec-50 (APScheduler) ✅ Completed  
**Priority:** High  
**Status:** Pending  

---

## Objective

Implement a `@retry_with_backoff` decorator with exponential backoff and jitter to handle concurrency conflicts resiliently. Add the `ConcurrencyConflictError` domain exception to represent concurrency conflicts (HTTP 409). **In F5, the decorator is applied exclusively to the scheduler's refresh job** — `RecordMovementUseCase` and other use cases already completed in Spec-40 are not modified.

**Design principles:**
- **Exponential backoff with jitter** — prevents thundering herd when multiple instances retry simultaneously
- **Async-compatible** — works with `async def` functions
- **Configurable** — max retries, base delay, max delay, and exception types to catch
- **Retry logging** — each retry is logged with the delay and attempt number
- **Fail-fast for non-retryable errors** — only specific exceptions are retried
- **Separation of concerns** — the decorator is a generic utility, not domain-specific

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| Generic decorator (not DB-specific) | Reusable in any retryable operation (refresh, HTTP calls, etc.) |
| Exponential backoff with jitter | `delay = min(base * 2^attempt + random(0, jitter), max_delay)`. Industry standard (AWS, Google Cloud) |
| Configurable exceptions by default | By default catches `ConcurrencyConflictError` and `asyncpg.SerializationError`. Caller can add more |
| Does not catch generic `Exception` | Only retry known-retryable errors. Unknown errors must propagate |
| WARNING logging for retries | INFO for success, WARNING for retries, ERROR for final failure |
| Maximum 3 retries by default | Balance between resilience and latency. 3 retries with 1s base = max ~7s total delay |
| 500ms jitter by default | Sufficient to desynchronize concurrent retries without adding too much delay |

---

## Domain Exception: `ConcurrencyConflictError`

### `src/domain/exceptions/concurrency_conflict.py`

```python
"""Exception for concurrency conflicts.

Raised when an operation fails due to a concurrency
conflict (e.g., two transactions attempting to modify the
same data simultaneously). The caller should retry the
operation.
"""
from __future__ import annotations

from src.domain.exceptions.domain_error import DomainError


class ConcurrencyConflictError(DomainError):
    """Concurrency conflict in operation.

    Indicates that the operation could not complete because another process
    modified the same data simultaneously. It is recommended to retry
    with exponential backoff.
    """

    def __init__(self, operation: str, detail: str | None = None) -> None:
        self.operation = operation
        self.detail = detail
        message = f"Concurrency conflict on '{operation}'"
        if detail:
            message = f"{message}: {detail}"
        super().__init__(message)
```

---

## Retry Decorator

### `src/core/retry.py`

```python
"""Retry decorator with exponential backoff and jitter.

Provides a reusable decorator for async functions that
may fail transiently. Implements exponential backoff
with jitter to prevent thundering herd on concurrent retries.

Example::

    from src.core.retry import retry_with_backoff
    from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError

    @retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(ConcurrencyConflictError,),
    )
    async def refresh_view(pool):
        await pool.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY ...")
"""
from __future__ import annotations

import asyncio
import functools
import logging
import random
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: float = 0.5,
    exceptions: tuple[type[Exception], ...] = (),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Retry decorator with exponential backoff and jitter.

    Retries the decorated function up to ``max_retries`` times when
    one of the specified exceptions is raised. The delay between
    retries follows the formula::

        delay = min(base_delay * 2^attempt + random(0, jitter), max_delay)

    Args:
        max_retries: Maximum number of retries (does not count the
            initial attempt).
        base_delay: Base delay in seconds for the first retry.
        max_delay: Maximum delay in seconds (backoff cap).
        jitter: Randomness range added to each delay (seconds).
        exceptions: Tuple of exceptions that trigger a retry.
            **Required** — do not use the empty default value, as
            catching all exceptions would retry non-recoverable
            errors (ValueError, logic errors, etc.).

    Raises:
        ValueError: If ``exceptions`` is empty (at least one
            exception type must be configured).

    Returns:
        Decorator that wraps the function with retry logic.

    Example::

        @retry_with_backoff(
            max_retries=3,
            base_delay=1.0,
            exceptions=(ConcurrencyConflictError,),
        )
        async def risky_operation():
            ...
    """
    if not exceptions:
        raise ValueError(
            "exceptions must specify at least one exception type. "
            "Capturing Exception is unsafe — it would retry non-recoverable "
            "errors (ValueError, logic errors, etc.)."
        )

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc

                    if attempt < max_retries:
                        delay = min(
                            base_delay * (2**attempt) + random.uniform(0, jitter),
                            max_delay,
                        )
                        logger.warning(
                            "%s failed (attempt %d/%d): %s. Retrying in %.2fs",
                            func.__name__,
                            attempt + 1,
                            max_retries + 1,
                            exc,
                            delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__,
                            max_retries + 1,
                            exc,
                        )

            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator
```

---

## Application: Refresh with Retry

The decorator is applied to the scheduler job so that the view refresh is resilient to transactional conflicts:

### Update to `src/infrastructure/scheduler/scheduler.py`

```python
from src.core.retry import retry_with_backoff
from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError
import asyncpg


_RETRYABLE_EXCEPTIONS = (
    ConcurrencyConflictError,
    asyncpg.SerializationFailure,
    asyncpg.DeadlockDetectedError,
)


@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    max_delay=10.0,
    jitter=0.5,
    exceptions=_RETRYABLE_EXCEPTIONS,
)
async def _refresh_job(pool: Pool) -> None:
    """Job that refreshes the materialized view with retries."""
    from src.infrastructure.db.refresh import refresh_stock_view
    import time

    start = time.monotonic()
    _logger.info("Starting mv_stock_historical refresh")
    await refresh_stock_view(pool)  # Can raise asyncpg.SerializationFailure
    elapsed = time.monotonic() - start
    _logger.info("mv_stock_historical refreshed in %.2fs", elapsed)
```

---

## Error Handler Mapping

Update the error handler from Spec-42 to map `ConcurrencyConflictError` to HTTP 409:

### Update in `src/adapters/api/middleware/error_handler.py`

```python
from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError

@app.exception_handler(ConcurrencyConflictError)
async def handle_concurrency_conflict(
    request, exc: ConcurrencyConflictError
) -> JSONResponse:
    """Maps ConcurrencyConflictError to HTTP 409 Conflict."""
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            error=ErrorDetail(
                code="CONCURRENCY_CONFLICT",
                message=str(exc),
                details={
                    "operation": exc.operation,
                    "detail": exc.detail,
                },
            )
        ).model_dump(),
    )
```

### Updated Error Table

| Domain Exception | HTTP Status | Error Code | Context |
|-------------------|-------------|------------|----------|
| `ConcurrencyConflictError` | 409 Conflict | `CONCURRENCY_CONFLICT` | Two concurrent operations on the same resource |

---

## Retry Parameter Guide

| Scenario | max_retries | base_delay | max_delay | Rationale |
|-----------|-------------|------------|-----------|-----------|
| View refresh (F5) | 3 | 1.0s | 10.0s | Background operation, can wait |

> **Note:** In F5 the retry is only applied to the refresh job. If in F6+ concurrency conflicts are detected in write use cases, retry will be added with more conservative parameters (e.g., 2 retries, 0.5s base).

---

## Files

| File | Description |
|------|-------------|
| `src/domain/exceptions/concurrency_conflict.py` | New domain exception |
| `src/domain/exceptions/__init__.py` | Re-export: `ConcurrencyConflictError` |
| `src/core/retry.py` | `@retry_with_backoff` decorator |
| `src/core/__init__.py` | Re-export: `retry_with_backoff` |
| `src/infrastructure/scheduler/scheduler.py` | Apply retry to refresh job |
| `src/adapters/api/middleware/error_handler.py` | Handler for `ConcurrencyConflictError` |

---

## Acceptance Criteria

- [ ] `ConcurrencyConflictError` can be instantiated with optional `operation` and `detail`
- [ ] `ConcurrencyConflictError` inherits from `DomainError` and is caught by the generic handler
- [ ] `@retry_with_backoff` retries with exponential backoff + jitter
- [ ] The decorator only catches specified exceptions (not generic `Exception`)
- [ ] Each retry is logged at WARNING level including attempt number and delay
- [ ] The final failure is logged at ERROR level
- [ ] The scheduler refresh job uses retry with 3 retries
- [ ] `ConcurrencyConflictError` maps to HTTP 409 with code `CONCURRENCY_CONFLICT`
- [ ] Unit tests validate retry behavior (mock sleep)
- [ ] `make lint` passes without errors

---

## Testing Strategy

- **Unit test for `ConcurrencyConflictError`**: verify message, attributes, inheritance from `DomainError`
- **Unit test for `@retry_with_backoff` (success on retry)**: mock function that fails 2 times and succeeds on the third, verify it is called 3 times
- **Unit test for `@retry_with_backoff` (final failure)**: mock function that always fails, verify it is called `max_retries + 1` times and that the exception propagates
- **Unit test for `@retry_with_backoff` (non-retryable exception)**: mock function that raises `ValueError`, verify it is called only 1 time and the exception propagates immediately
- **Unit test for delay**: with mock of `asyncio.sleep`, verify that delays follow the exponential pattern
- **Error handler test**: simulate `ConcurrencyConflictError` and verify 409 response

### Example: Retry test with success on retry

```python
import pytest
from unittest.mock import AsyncMock, patch
from src.core.retry import retry_with_backoff
from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError

@pytest.mark.asyncio
async def test_retry_succeeds_on_third_attempt():
    call_count = 0

    @retry_with_backoff(
        max_retries=3,
        base_delay=0.01,  # minimum delay for fast tests
        jitter=0.0,
        exceptions=(ConcurrencyConflictError,),
    )
    async def flaky_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConcurrencyConflictError("test")
        return "ok"

    with patch("asyncio.sleep"):
        result = await flaky_func()

    assert result == "ok"
    assert call_count == 3
```

---

## Resolved Questions

1. **Should the decorator be synchronous or asynchronous?** → **Asynchronous.** The project uses FastAPI + asyncpg, all operations that need retry are async. A sync decorator wrapping async would be unnecessarily complex.

2. **Should jitter be included or is it optional?** → **Always jitter.** Without jitter, multiple instances retry at the same time (thundering herd). The default 500ms jitter is sufficient to desynchronize without significantly affecting latency.

3. **Which asyncpg exceptions are retryable?** → **`SerializationFailure` and `DeadlockDetectedError`.** Both indicate transactional conflicts that are resolved by retrying. Other errors (connection loss, syntax error) are not retryable and must propagate.

4. **Should the decorator accept a custom logging callback function?** → **Not in F5.** Default logging is sufficient. If in the future specific per-operation logging is needed, an optional `logger` parameter can be added to the decorator.

5. **Should there be an HTTP retry middleware?** → **No.** Retry is at the operation level (function), not at the HTTP level. The HTTP client (browser, Postman) decides whether to retry requests. The server should only be idempotent on operations that require it.

6. **Should retry be applied to movement use cases in F5?** → **No.** In F5 the retry is applied exclusively to the scheduler's refresh job. Movement use cases (Spec-40) are already completed and are not modified. If in F6 concurrency conflicts are detected in writes, retry will be added as an extension without breaking existing tests.
