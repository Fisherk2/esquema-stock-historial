# SPEC-50: Integración APScheduler

**Fase:** F5 — Scheduler & Concurrencia  
**Dependencias:** Spec-31 (Vistas Materializadas) ✅ Completado, Spec-42 (Rutas FastAPI) ✅ Completado  
**Prioridad:** Media  
**Estado:** Pendiente  

---

## Objective

Integrar **APScheduler 3.11** como motor de tareas en background dentro del ciclo de vida de FastAPI. El scheduler gestionará el refresh periódico de la vista materializada `mv_stock_historical` con una política configurable, listeners de eventos para logging, y shutdown graceful. El scheduler es un detalle de infraestructura intercambiable — su interfaz con la aplicación se limita a la configuración del lifespan.

**Principios de diseño:**
- **AsyncIOScheduler** — usa el event loop existente de FastAPI, no crea hilos separados
- **Isolation de resources** — el scheduler obtiene su propia conexión del pool, no comparte con requests
- **Shutdown graceful** — al parar la app, el scheduler detiene jobs pendientes antes de cerrar
- **Configurable via Settings** — intervalo de refresh, habilitar/deshabilitar, todo via `.env`
- **No bloquea request/response** — las tareas corren en background, cero impacto en latencia de API
- **Swap-ready** — la arquitectura permite reemplazar APScheduler por Celery/RQ sin tocar dominio

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| `AsyncIOScheduler` (no `BackgroundScheduler`) | Compatible con asyncio nativo. No crea thread pool separado. Mejor integración con FastAPI |
| Scheduler vive en el `lifespan` de FastAPI | Ciclo de vida gestionado por el framework. Start en startup, shutdown en cleanup |
| Refresh cada 5 minutos por defecto | Balance entre frescura de datos y carga en DB. Configurable via `SCHEDULER_REFRESH_INTERVAL_MINUTES` |
| Job ID fijo (`refresh_stock_view`) | Idempotente. Si el job ya existe, se reemplaza (no se duplica). Fácil de monitorizar |
| `replace_existing=True` | Al reiniciar la app, el job se re-registra sin error. Idempotencia en arranque |
| Event listener para logging | Cada ejecución del job se loggea con timing. Permite detectar fallos sin polling |
| `misfire_grace_time=60` | Si el scheduler se retrasa (startup lento, DB ocupada), tolera hasta 60s de retraso |
| Deshabilitable en tests | Variable `SCHEDULER_ENABLED=false` en tests. Los tests no necesitan scheduler real |

---

## Settings Extensions

Añadir campos de configuración del scheduler en `src/core/config.py`:

```python
# Campos de scheduler (añadir a la clase Settings existente)
scheduler_enabled: bool = True
scheduler_refresh_interval_minutes: int = 5
scheduler_misfire_grace_time_seconds: int = 60
# Nota: statement_timeout se configura via pool server_settings en connection.py
# (ver Spec-52 para detalles). Ya no se pasa como parametro al scheduler.
```

Variables de entorno correspondientes:
- `SCHEDULER_ENABLED=true|false`
- `SCHEDULER_REFRESH_INTERVAL_MINUTES=5`
- `SCHEDULER_MISFIRE_GRACE_TIME_SECONDS=60`

> **Nota v1.0.2:** `SCHEDULER_STATEMENT_TIMEOUT_SECONDS` ya no se usa directamente.
> El timeout se hereda del pool via `server_settings={"statement_timeout": ...}` configurado
> en `init_pool()`. Si el refresh necesita más tiempo, ajustar `API_STATEMENT_TIMEOUT_SECONDS`.

---

## Scheduler Module

### `src/infrastructure/scheduler/scheduler.py`

Módulo principal que crea y gestiona el `AsyncIOScheduler`:

```python
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

from apscheduler.schedulers.asyncio import AsyncIOScheduler

if TYPE_CHECKING:
    from asyncpg import Pool

_logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _refresh_job(pool: Pool) -> None:
    """Job que refresca la vista materializada.

    Delega la ejecucion a _do_refresh con reintentos automaticos.
    El statement_timeout esta heredado del pool via ``server_settings``
    configurado en ``create_pool()``. El retry_with_backoff en
    _do_refresh tolera timeouts y conflictos.
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
    """Crea y configura el AsyncIOScheduler."""
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
    """Inicializa y arranca el scheduler."""
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
```

---

## Lifespan Integration

Actualizar `src/main.py` para incluir el scheduler en el lifecycle:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook para inicializacion y limpieza de recursos.

    Inicializa el pool de conexiones asyncpg y el scheduler al arrancar.
    Cierra el scheduler y el pool al apagar la aplicacion.
    """
    settings = Settings()
    await init_pool(settings)

    # F5: Iniciar scheduler
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
        # F5: Detener scheduler antes de cerrar pool
        await shutdown_scheduler()
        await close_pool()
```

---

## Refresh Policy

### Política de Refresh por Intervalo

El scheduler ejecuta `REFRESH MATERIALIZED VIEW CONCURRENTLY` cada N minutos (configurable). Esta estrategia es simple y suficiente para la fase actual.

| Parámetro | Default | Descripción |
|-----------|---------|-------------|
| `SCHEDULER_ENABLED` | `true` | Habilitar/deshabilitar scheduler |
| `SCHEDULER_REFRESH_INTERVAL_MINUTES` | `5` | Minutos entre refreshes |
| `SCHEDULER_MISFIRE_GRACE_TIME_SECONDS` | `60` | Tolerancia de retraso |
| `SCHEDULER_STATEMENT_TIMEOUT_SECONDS` | `30` | Timeout en segundos para el refresh job |

### Futuras Mejoras (F6+)

- **Refresh on-demand**: Endpoint admin `POST /v1/admin/refresh-stock-view` para trigger manual
- **Refresh inteligente**: Detectar si hay movimientos nuevos desde el último refresh y solo refrescar si hay cambios
- **Refresh por evento**: Trigger de refresh al registrar un movimiento (debounce de 30s)

---

## Files

| File | Description |
|------|-------------|
| `src/core/config.py` | Añadir campos de configuración del scheduler |
| `src/infrastructure/scheduler/scheduler.py` | Módulo principal del scheduler |
| `src/infrastructure/scheduler/__init__.py` | Re-exports públicos |
| `src/main.py` | Integrar scheduler en lifespan |

---

## Acceptance Criteria

- [ ] `AsyncIOScheduler` se inicia en el `lifespan` de FastAPI
- [ ] Job `refresh_stock_view` se registra con intervalo configurable
- [ ] `SCHEDULER_ENABLED=false` deshabilita el scheduler sin error
- [ ] `shutdown_scheduler()` detiene el scheduler gracefulmente antes de cerrar el pool
- [ ] El refresh de la vista se ejecuta periódicamente según el intervalo configurado
- [ ] Los logs registran inicio, fin, duración y errores de cada refresh
- [ ] Solo una instancia del job puede ejecutarse a la vez (`max_instances=1`)
- [ ] Tests unitarios validan la creación del scheduler con mocks
- [ ] `make lint` pasa sin errores

---

## Testing Strategy

- **Test unitario de `create_scheduler()`**: verificar que el job se registra con los parámetros correctos (mock del scheduler)
- **Test unitario de `_refresh_job()`**: mock de `refresh_stock_view` y verificar que se llama con el pool correcto
- **Test unitario de `start_scheduler()`**: con `enabled=False`, verificar que no se crea scheduler
- **Test unitario de `shutdown_scheduler()`**: verificar que `scheduler.shutdown(wait=True)` se llama
- **Test de integración**: arrancar la app con testcontainers, verificar que el scheduler está running y que el job se ejecuta (usar `freezegun` o intervalo muy corto de 1s)

### Ejemplo: Test unitario de create_scheduler

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

1. **¿Usar `AsyncIOScheduler` o `BackgroundScheduler`?** → **`AsyncIOScheduler`.** Usa el event loop existente de FastAPI. `BackgroundScheduler` crea un thread pool separado que añade complejidad innecesaria y potencial de race conditions con código async.

2. **¿El scheduler debe tener su propio pool de conexiones?** → **No.** Usa el pool compartido de la aplicación. `REFRESH CONCURRENTLY` no bloquea lecturas, así que no hay conflicto con los requests. Añadir un pool separado consumiría recursos adicionales sin beneficio.

3. **¿Qué pasa si el refresh falla?** → **Se loggea el error y se reintenta en el próximo ciclo.** No se detiene el scheduler. El fallback (cálculo directo) sigue disponible para los endpoints de stock mientras la vista está stale. En F5 se añade logging estructurado; en F6+ se puede añadir retry con backoff (Spec-51).

4. **¿Debe existir un endpoint admin para refresh manual?** → **No en F5.** El refresh manual se puede ejecutar vía la función `refresh_stock_view()` directamente o por el scheduler. Un endpoint añade complejidad (auth, access control) que no justifica el beneficio actual. Se puede añadir en F6+ si se necesita.

5. **¿Usar `CronTrigger` o `IntervalTrigger`?** → **`IntervalTrigger`.** Más simple y suficiente para refresh periódico. `CronTrigger` sería útil si se necesita refresh a horas específicas (ej: cada hora en punto), pero en F5 un intervalo fijo es suficiente. Se puede cambiar a cron en el futuro sin romper el contrato.
