# SPEC-51: Optimistic Concurrency & Retry

**Fase:** F5 — Scheduler & Concurrencia  
**Dependencias:** Spec-40 (Casos de Uso) ✅ Completado, Spec-50 (APScheduler) ✅ Completado  
**Prioridad:** Alta  
**Estado:** Pendiente  

---

## Objective

Implementar un decorador `@retry_with_backoff` con backoff exponencial y jitter para manejar conflictos de concurrencia de forma resiliente. Añadir la excepción de dominio `ConcurrencyConflictError` para representar conflictos de concurrencia (HTTP 409). **En F5, el decorador se aplica exclusivamente al refresh job del scheduler** — no se modifica `RecordMovementUseCase` ni otros use cases ya completados en Spec-40.

**Principios de diseño:**
- **Backoff exponencial con jitter** — evita thundering herd cuando múltiples instancias reintentan simultáneamente
- **Async-compatible** — funciona con funciones `async def`
- **Configurable** — max retries, base delay, max delay, y tipos de excepción a capturar
- **Logging por reintento** — cada reintento se loggea con el delay y el número de intento
- **Fail-fast para errores no-retryables** — solo se reintentan excepciones específicas
- **Separación de responsabilidades** — el decorador es utilitario genérico, no específico del dominio

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| Decorador genérico (no específico de DB) | Reutilizable en cualquier operación retryable (refresh, HTTP calls, etc.) |
| Backoff exponencial con jitter | `delay = min(base * 2^attempt + random(0, jitter), max_delay)`. Estándar de la industria (AWS, Google Cloud) |
| Excepciones configurables por defecto | Por defecto captura `ConcurrencyConflictError` y `asyncpg.SerializationError`. Caller puede añadir más |
| No captura `Exception` genérica | Solo reintentar errores known-retryable. Errores desconocidos deben propagarse |
| Logging en WARNING para reintentos | INFO para éxito, WARNING para reintentos, ERROR para fallo final |
| Máximo 3 reintentos por defecto | Balance entre resiliencia y latencia. 3 reintentos con base 1s = máx ~7s de delay total |
| Jitter de 500ms por defecto | Suficiente para desincronizar reintentos concurrentes sin añadir demasiado delay |

---

## Domain Exception: `ConcurrencyConflictError`

### `src/domain/exceptions/concurrency_conflict.py`

```python
"""Excepcion para conflictos de concurrencia.

Se lanza cuando una operación falla debido a un conflicto de
concurrencia (ej: dos transacciones intentando modificar los
mismos datos simultaneamente). El caller debe reintentar la
operación.
"""
from __future__ import annotations

from src.domain.exceptions.domain_error import DomainError


class ConcurrencyConflictError(DomainError):
    """Conflicto de concurrencia en operacion.

    Indica que la operacion no pudo completarse porque otro proceso
    modifico los mismos datos simultaneamente. Se recomienda reintentar
    con backoff exponencial.
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
"""Decorador de reintentos con backoff exponencial y jitter.

Proporciona un decorador reutilizable para funciones async que
pueden fallar transitoriamente. Implementa backoff exponencial
con jitter para evitar thundering herd en reintentos concurrentes.

Ejemplo::

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
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorador de reintentos con backoff exponencial y jitter.

    Reintenta la funcion decorada hasta ``max_retries`` veces cuando
    se lanza una de las excepciones especificadas. El delay entre
    reintentos sigue la formula::

        delay = min(base_delay * 2^attempt + random(0, jitter), max_delay)

    Args:
        max_retries: Numero maximo de reintentos (no cuenta el intento inicial).
        base_delay: Delay base en segundos para el primer reintento.
        max_delay: Delay maximo en segundos (tope del backoff).
        jitter: Rango de aleatoriedad añadido a cada delay (segundos).
        exceptions: Tupla de excepciones que disparan el reintento.

    Returns:
        Decorador que envuelve la funcion con logica de reintento.

    Ejemplo::

        @retry_with_backoff(
            max_retries=3,
            base_delay=1.0,
            exceptions=(ConcurrencyConflictError,),
        )
        async def risky_operation():
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
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

## Application: Refresh con Retry

El decorador se aplica al job del scheduler para que el refresh de la vista sea resiliente a conflictos transaccionales:

### Actualización de `src/infrastructure/scheduler/scheduler.py`

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
    """Job que refresca la vista materializada con reintentos."""
    from src.infrastructure.db.refresh import refresh_stock_view
    import time

    start = time.monotonic()
    _logger.info("Starting mv_stock_historical refresh")
    await refresh_stock_view(pool)  # Puede lanzar asyncpg.SerializationFailure
    elapsed = time.monotonic() - start
    _logger.info("mv_stock_historical refreshed in %.2fs", elapsed)
```

---

## Error Handler Mapping

Actualizar el error handler de Spec-42 para mapear `ConcurrencyConflictError` a HTTP 409:

### Actualización en `src/adapters/api/middleware/error_handler.py`

```python
from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError

@app.exception_handler(ConcurrencyConflictError)
async def handle_concurrency_conflict(
    request, exc: ConcurrencyConflictError
) -> JSONResponse:
    """Mapea ConcurrencyConflictError a HTTP 409 Conflict."""
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

### Tabla de Errores Actualizada

| Excepción Dominio | HTTP Status | Error Code | Contexto |
|-------------------|-------------|------------|----------|
| `ConcurrencyConflictError` | 409 Conflict | `CONCURRENCY_CONFLICT` | Dos operaciones concurrentes en el mismo recurso |

---

## Retry Parameter Guide

| Escenario | max_retries | base_delay | max_delay | Rationale |
|-----------|-------------|------------|-----------|-----------|
| Refresh de vista (F5) | 3 | 1.0s | 10.0s | Operación background, puede esperar |

> **Nota:** En F5 el retry solo se aplica al refresh job. Si en F6+ se detectan conflictos de concurrencia en use cases de escritura, se añadirá retry con parámetros más conservadores (ej: 2 reintentos, base 0.5s).

---

## Files

| File | Description |
|------|-------------|
| `src/domain/exceptions/concurrency_conflict.py` | Nueva excepción de dominio |
| `src/domain/exceptions/__init__.py` | Re-export: `ConcurrencyConflictError` |
| `src/core/retry.py` | Decorador `@retry_with_backoff` |
| `src/core/__init__.py` | Re-export: `retry_with_backoff` |
| `src/infrastructure/scheduler/scheduler.py` | Aplicar retry al refresh job |
| `src/adapters/api/middleware/error_handler.py` | Handler para `ConcurrencyConflictError` |

---

## Acceptance Criteria

- [ ] `ConcurrencyConflictError` se puede instanciar con `operation` y `detail` opcionales
- [ ] `ConcurrencyConflictError` hereda de `DomainError` y es capturada por el handler genérico
- [ ] `@retry_with_backoff` reintenta con backoff exponencial + jitter
- [ ] El decorador solo captura las excepciones especificadas (no `Exception` genérica)
- [ ] Cada reintento se loggea con nivel WARNING incluyendo número de intento y delay
- [ ] El último fallo se loggea con nivel ERROR
- [ ] El refresh job del scheduler usa retry con 3 reintentos
- [ ] `ConcurrencyConflictError` se mapea a HTTP 409 con código `CONCURRENCY_CONFLICT`
- [ ] Tests unitarios validan el comportamiento de retry (mock sleep)
- [ ] `make lint` pasa sin errores

---

## Testing Strategy

- **Test unitario de `ConcurrencyConflictError`**: verificar mensaje, atributos, herencia de `DomainError`
- **Test unitario de `@retry_with_backoff` (éxito al reintento)**: mock de función que falla 2 veces y éxito a la tercera, verificar que se llama 3 veces
- **Test unitario de `@retry_with_backoff` (fallo final)**: mock de función que siempre falla, verificar que se llama `max_retries + 1` veces y que la excepción se propaga
- **Test unitario de `@retry_with_backoff` (excepción no-retryable)**: mock de función que lanza `ValueError`, verificar que se llama solo 1 vez y la excepción se propaga inmediatamente
- **Test unitario de delay**: con mock de `asyncio.sleep`, verificar que los delays siguen el patrón exponencial
- **Test de error handler**: simular `ConcurrencyConflictError` y verificar respuesta 409

### Ejemplo: Test de retry con éxito al reintento

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
        base_delay=0.01,  # delay mínimo para tests rápidos
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

1. **¿El decorador debe ser síncrono o asíncrono?** → **Asíncrono.** El proyecto usa FastAPI + asyncpg, todas las operaciones que necesitan retry son async. Un decorador sync que envuelve async sería innecesariamente complejo.

2. **¿Debe incluirse jitter o es opcional?** → **Siempre jitter.** Sin jitter, múltiples instancias reintentan al mismo tiempo (thundering herd). El jitter por defecto de 500ms es suficiente para desincronizar sin afectar significativamente la latencia.

3. **¿Qué excepciones de asyncpg son retryables?** → **`SerializationFailure` y `DeadlockDetectedError`.** Ambas indican conflictos transaccionales que se resuelven reintentando. Otros errores (connection loss, syntax error) no son retryables y deben propagarse.

4. **¿El decorador debe aceptar una función callback para logging custom?** → **No en F5.** El logging por defecto es suficiente. Si en el futuro se necesita logging específico por operación, se puede añadir un parámetro `logger` opcional al decorador.

5. **¿Debe existir un middleware HTTP de retry?** → **No.** El retry es a nivel de operación (función), no a nivel HTTP. El cliente HTTP (navegador, Postman) decide si reintentar requests. El servidor solo debe ser idempotente en operaciones que lo requieran.

6. **¿Debe aplicarse retry a los use cases de movimiento en F5?** → **No.** En F5 el retry se aplica exclusivamente al refresh job del scheduler. Los use cases de movimiento (Spec-40) ya están completados y no se modifican. Si en F6 se detectan conflictos de concurrencia en escrituras, se añadirá retry como una extensión sin romper los tests existentes.
