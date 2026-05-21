"""APScheduler integration — gestion del scheduler de tareas en background.

Crea y configura un AsyncIOScheduler que ejecuta tareas periodicas
dentro del event loop de FastAPI. Actualmente gestiona el refresh
de la vista materializada mv_stock_historical.

El scheduler se integra en el lifespan de FastAPI:
- start_scheduler(): se llama en startup
- shutdown_scheduler(): se llama en cleanup
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

import asyncpg
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.core.retry import retry_with_backoff
from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError

if TYPE_CHECKING:
    from asyncpg import Pool

_logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

# Excepciones retryables para el refresh de la vista materializada.
_RETRYABLE_EXCEPTIONS = (
    ConcurrencyConflictError,
    asyncpg.SerializationError,
    asyncpg.DeadlockDetectedError,
)


@retry_with_backoff(
    max_retries=3,
    base_delay=1.0,
    max_delay=10.0,
    jitter=0.5,
    exceptions=_RETRYABLE_EXCEPTIONS,
)
async def _do_refresh(pool: Pool) -> None:
    """Refresca la vista materializada con reintentos automaticos.

    Envuelto con retry_with_backoff para tolerar conflictos transaccionales
    (SerializationFailure, DeadlockDetectedError).

    Args:
        pool: Pool de conexiones asyncpg.
    """
    from src.infrastructure.db.refresh import refresh_stock_view

    await refresh_stock_view(pool)


async def _refresh_job(pool: Pool) -> None:
    """Job que refresca la vista materializada.

    Delega la ejecucion a _do_refresh con reintentos automaticos.
    El statement_timeout esta heredado del pool via ``server_settings``
    configurado en ``create_pool()``. El retry_with_backoff en
    _do_refresh tolera timeouts y conflictos.

    Args:
        pool: Pool de conexiones asyncpg.
    """
    start = time.monotonic()
    _logger.info("Starting mv_stock_historical refresh")
    try:
        await _do_refresh(pool)
        elapsed = time.monotonic() - start
        _logger.info("mv_stock_historical refreshed in %.2fs", elapsed)
    except Exception:
        elapsed = time.monotonic() - start
        _logger.exception("mv_stock_historical refresh failed after %.2fs", elapsed)


def create_scheduler(
    pool: Pool,
    refresh_interval_minutes: int = 5,
    misfire_grace_time: int = 60,
) -> AsyncIOScheduler:
    """Crea y configura el AsyncIOScheduler.

    Registra un unico job para el refresh periodico de la vista
    materializada mv_stock_historical.

    Args:
        pool: Pool de conexiones asyncpg para el refresh.
        refresh_interval_minutes: Intervalo entre refreshes de la vista.
        misfire_grace_time: Tolerancia en segundos para jobs retrasados.

    Returns:
        AsyncIOScheduler configurado y listo para iniciar.
    """
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        _refresh_job,
        trigger="interval",
        minutes=refresh_interval_minutes,
        args=[pool],
        id="refresh_stock_view",
        replace_existing=True,
        misfire_grace_time=misfire_grace_time,
        max_instances=1,
    )

    return scheduler


async def start_scheduler(
    pool: Pool,
    enabled: bool = True,
    refresh_interval_minutes: int = 5,
    misfire_grace_time: int = 60,
) -> None:
    """Inicializa y arranca el scheduler.

    Args:
        pool: Pool de conexiones asyncpg.
        enabled: Si False, no arranca el scheduler (util en tests).
        refresh_interval_minutes: Intervalo entre refreshes.
        misfire_grace_time: Tolerancia para jobs retrasados.
    """
    global _scheduler

    if not enabled:
        _logger.info("Scheduler disabled (SCHEDULER_ENABLED=false)")
        return

    _scheduler = create_scheduler(
        pool, refresh_interval_minutes, misfire_grace_time
    )
    _scheduler.start()
    _logger.info(
        "Scheduler started — refresh every %d minutes",
        refresh_interval_minutes,
    )


async def shutdown_scheduler() -> None:
    """Detiene el scheduler gracefulmente."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)
        _logger.info("Scheduler shut down")
        _scheduler = None
