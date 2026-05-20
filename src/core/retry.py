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
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

# TypeVar para funcion callable async con tipo de retorno generico
T = TypeVar("T")


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: float = 0.5,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorador de reintentos con backoff exponencial y jitter.

    Reintenta la funcion decorada hasta ``max_retries`` veces cuando
    se lanza una de las excepciones especificadas. El delay entre
    reintentos sigue la formula::

        delay = min(base_delay * 2^attempt + random(0, jitter), max_delay)

    Args:
        max_retries: Numero maximo de reintentos (no cuenta el intento
            inicial).
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

    def decorator(
        func: Callable[..., Awaitable[T]],
    ) -> Callable[..., Awaitable[T]]:
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

            # last_exception is guaranteed to be set here because we only
            # reach this point after catching at least one exception
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
