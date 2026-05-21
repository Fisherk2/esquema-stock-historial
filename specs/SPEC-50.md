# SPEC-50: APScheduler Integration

**Phase:** F5 — Scheduler & Concurrency  
**Dependencies:** Spec-31 (Materialized Views) ✅ Completed, Spec-42 (FastAPI Routes) ✅ Completed  
**Priority:** Medium  
**Status:** Pending  

---

## Objective

Integrate **APScheduler 3.11** as the background task engine within the FastAPI lifecycle. The scheduler will manage the periodic refresh of the materialized view `mv_stock_historical` with a configurable policy, event listeners for logging, and graceful shutdown. The scheduler is a swappable infrastructure detail — its interface with the application is limited to the lifespan configuration.

**Design principles:**
- **AsyncIOScheduler** — uses FastAPI's existing event loop, does not create separate threads
- **Resource isolation** — the scheduler gets its own connection from the pool, does not share with requests
- **Graceful shutdown** — when stopping the app, the scheduler stops pending jobs before closing
- **Configurable via Settings** — refresh interval, enable/disable, all via `.env`
- **Does not block request/response** — tasks run in the background, zero impact on API latency
- **Swap-ready** — the architecture allows replacing APScheduler with Celery/RQ without touching the domain

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| `AsyncIOScheduler` (not `BackgroundScheduler`) | Compatible with native asyncio. Does not create a separate thread pool. Better integration with FastAPI |
| Scheduler lives in FastAPI's `lifespan` | Lifecycle managed by the framework. Start on startup, shutdown on cleanup |
| Refresh every 5 minutes by default | Balance between data freshness and DB load. Configurable via `SCHEDULER_REFRESH_INTERVAL_MINUTES` |
| Fixed job ID (`refresh_stock_view`) | Idempotent. If the job already exists, it is replaced (not duplicated). Easy to monitor |
| `replace_existing=True` | When restarting the app, the job is re-registered without error. Idempotency on startup |
| Event listener for logging | Each job execution is logged with timing. Allows detecting failures without polling |
| `misfire_grace_time=60` | If the scheduler is delayed (slow startup, busy DB), tolerates up to 60s of delay |
| Disableable in tests | Variable `SCHEDULER_ENABLED=false` in tests. Tests do not need a real scheduler |

---

## Settings Extensions

Add scheduler configuration fields in `src/core/config.py`:

```python
# Scheduler fields (add to the existing Settings class)
scheduler_enabled: bool = True
scheduler_refresh_interval_minutes: int = 5
scheduler_misfire_grace_time_seconds: int = 60
# Note: statement_timeout is configured via pool server_settings in connection.py
# (see Spec-52 for details). No longer passed as a parameter to the scheduler.
```

Corresponding environment variables:
- `SCHEDULER_ENABLED=true|false`
- `SCHEDULER_REFRESH_INTERVAL_MINUTES=5`
- `SCHEDULER_MISFIRE_GRACE_TIME_SECONDS=60`

> **Note:** `SCHEDULER_STATEMENT_TIMEOUT_SECONDS` is no longer used directly.
> The timeout is inherited from the pool via `server_settings={"statement_timeout": ...}` configured
> in `init_pool()`. If the refresh needs more time, adjust `API_STATEMENT_TIMEOUT_SECONDS`.

---

## Scheduler Module

### `src/infrastructure/scheduler/scheduler.py`

Main module that creates and manages the `AsyncIOScheduler`:

```python
"""APScheduler integration — background task scheduler management.

Creates and configures an AsyncIOScheduler that executes periodic tasks
within FastAPI's event loop. Currently manages the refresh
of the materialized view mv_stock_historical.

The scheduler integrates into FastAPI's lifespan:
- start_scheduler(): called on startup
- shutdown_scheduler(): called on cleanup
"""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler

if TYPE_CHECKING:
    from asyncpg import Pool

_logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _refresh_job(pool: Pool) -> None:
    """Job that refreshes the materialized view.

    Delegates execution to _do_refresh with automatic retries.
    The statement_timeout is inherited from the pool via ``server_settings``
    configured in ``create_pool()``. The retry_with_backoff in
    _do_refresh tolerates timeouts and conflicts.
    """
    from src.infrastructure.db.refresh import refresh_stock_view

    start = time.monotonic()
    _logger.info("Starting mv_stock_historical refresh")
    try:
        await refresh_stock_view(pool)
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
    """Creates and configures the AsyncIOScheduler."""
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
    """Initializes and starts the scheduler."""
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
    """Stops the scheduler gracefully."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=True)
        _logger.info("Scheduler shut down")
        _scheduler = None
```

---

## Lifespan Integration

Update `src/main.py` to include the scheduler in the lifecycle:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook for resource initialization and cleanup.

    Initializes the asyncpg connection pool and the scheduler on startup.
    Closes the scheduler and the pool when shutting down the application.
    """
    settings = Settings()
    await init_pool(settings)

    # F5: Start scheduler
    from src.infrastructure.db.connection import get_pool
    from src.infrastructure.scheduler.scheduler import (
        shutdown_scheduler,
        start_scheduler,
    )

    pool = await get_pool()
    await start_scheduler(
        pool=pool,
        enabled=settings.scheduler_enabled,
        refresh_interval_minutes=settings.scheduler_refresh_interval_minutes,
        misfire_grace_time=settings.scheduler_misfire_grace_time_seconds,
    )

    try:
        yield
    finally:
        # F5: Stop scheduler before closing pool
        await shutdown_scheduler()
        await close_pool()
```

---

## Refresh Policy

### Interval-Based Refresh Policy

The scheduler executes `REFRESH MATERIALIZED VIEW CONCURRENTLY` every N minutes (configurable). This strategy is simple and sufficient for the current phase.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SCHEDULER_ENABLED` | `true` | Enable/disable scheduler |
| `SCHEDULER_REFRESH_INTERVAL_MINUTES` | `5` | Minutes between refreshes |
| `SCHEDULER_MISFIRE_GRACE_TIME_SECONDS` | `60` | Delay tolerance |
| `SCHEDULER_STATEMENT_TIMEOUT_SECONDS` | `30` | Timeout in seconds for the refresh job |

### Future Improvements (F6+)

- **On-demand refresh**: Admin endpoint `POST /v1/admin/refresh-stock-view` for manual trigger
- **Smart refresh**: Detect if there are new movements since the last refresh and only refresh if there are changes
- **Event-driven refresh**: Trigger refresh when registering a movement (30s debounce)

---

## Files

| File | Description |
|------|-------------|
| `src/core/config.py` | Add scheduler configuration fields |
| `src/infrastructure/scheduler/scheduler.py` | Main scheduler module |
| `src/infrastructure/scheduler/__init__.py` | Public re-exports |
| `src/main.py` | Integrate scheduler into lifespan |

---

## Acceptance Criteria

- [ ] `AsyncIOScheduler` starts in FastAPI's `lifespan`
- [ ] `refresh_stock_view` job is registered with configurable interval
- [ ] `SCHEDULER_ENABLED=false` disables the scheduler without error
- [ ] `shutdown_scheduler()` stops the scheduler gracefully before closing the pool
- [ ] View refresh executes periodically according to the configured interval
- [ ] Logs record start, end, duration, and errors of each refresh
- [ ] Only one instance of the job can execute at a time (`max_instances=1`)
- [ ] Unit tests validate scheduler creation with mocks
- [ ] `make lint` passes without errors

---

## Testing Strategy

- **Unit test for `create_scheduler()`**: verify that the job is registered with the correct parameters (mock the scheduler)
- **Unit test for `_refresh_job()`**: mock `refresh_stock_view` and verify it is called with the correct pool
- **Unit test for `start_scheduler()`**: with `enabled=False`, verify that no scheduler is created
- **Unit test for `shutdown_scheduler()`**: verify that `scheduler.shutdown(wait=True)` is called
- **Integration test**: start the app with testcontainers, verify that the scheduler is running and that the job executes (use `freezegun` or a very short interval of 1s)

### Example: Unit test for create_scheduler

```python
from unittest.mock import patch, MagicMock
from src.infrastructure.scheduler.scheduler import create_scheduler

def test_create_scheduler_registers_job():
    pool = MagicMock()
    scheduler = create_scheduler(pool, refresh_interval_minutes=10, misfire_grace_time=30)

    jobs = scheduler.get_jobs()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "refresh_stock_view"
    assert job.max_instances == 1
```

---

## Resolved Questions

1. **Use `AsyncIOScheduler` or `BackgroundScheduler`?** → **`AsyncIOScheduler`.** Uses FastAPI's existing event loop. `BackgroundScheduler` creates a separate thread pool that adds unnecessary complexity and potential for race conditions with async code.

2. **Should the scheduler have its own connection pool?** → **No.** Uses the application's shared pool. `REFRESH CONCURRENTLY` does not block reads, so there is no conflict with requests. Adding a separate pool would consume additional resources without benefit.

3. **What happens if the refresh fails?** → **The error is logged and retried on the next cycle.** The scheduler is not stopped. The fallback (direct calculation) remains available for stock endpoints while the view is stale. In F5, structured logging is added; in F6+, retry with backoff can be added (Spec-51).

4. **Should there be an admin endpoint for manual refresh?** → **Not in F5.** Manual refresh can be executed via the `refresh_stock_view()` function directly or by the scheduler. An endpoint adds complexity (auth, access control) that does not justify the current benefit. It can be added in F6+ if needed.

5. **Use `CronTrigger` or `IntervalTrigger`?** → **`IntervalTrigger`.** Simpler and sufficient for periodic refresh. `CronTrigger` would be useful if refresh is needed at specific times (e.g., every hour on the hour), but in F5 a fixed interval is sufficient. It can be changed to cron in the future without breaking the contract.
