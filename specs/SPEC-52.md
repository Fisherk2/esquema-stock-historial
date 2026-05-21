# SPEC-52: Logging Estructurado & Errors

**Fase:** F5 — Scheduler & Concurrencia  
**Dependencias:** Spec-42 (Rutas FastAPI) ✅ Completado, Spec-51 (Retry/Conc) ✅ Completado  
**Prioridad:** Media  
**Estado:** Pendiente  

---

## Objective

Configurar un sistema de logging estructurado que proporcione visibilidad completa del comportamiento de la aplicación en desarrollo y producción. Implementar logging JSON en producción, logging legible en desarrollo, middleware de request logging para FastAPI, y configuración de timeouts de DB. El logging es la base para debugging, monitoring, y alerting.

**Principios de diseño:**
- **Structured logging** — cada log entry es un objeto con campos consistentes (timestamp, level, module, message, extra)
- **Formato según entorno** — legible en development (color, texto), JSON en production (parseable por herramientas)
- **Request correlation** — cada request HTTP tiene un `request_id` único que se propaga a todos los logs relacionados
- **Zero sensitive data** — nunca loggear passwords, tokens, o datos personales
- **Performance consciente** — logging async o bufferado para no bloquear el event loop
- **Graceful degradation** — si el logging falla, la aplicación sigue funcionando

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| `logging` estándar de Python (no structlog en F5) | Sin dependencia extra. `logging` es suficiente para F5. Se puede migrar a structlog en F6+ si se necesita más potencia |
| JSON formatter en production | Compatible con ELK, Datadog, CloudWatch. Cada línea es un JSON parseable |
| Colored output en development | Legibilidad para desarrolladores. `logging` con formatter custom |
| Request ID via middleware | Correlación de logs por request. UUID4 por request, pasado a los handlers via contextvars |
| `contextvars` para request_id | Thread-safe y async-safe. Propagación automática dentro del mismo request |
| DB `statement_timeout` configurado | Prevenir queries infinitas. Configurable via Settings: 5s para API, 30s para refresh |
| Excluir `/v1/health` del request logging | Los health checks son frecuentes (K8s/Docker) y no aportan valor a los logs |
| Log level por módulo | `uvicorn` en WARNING (verbose), `asyncpg` en WARNING, app modules en INFO/DEBUG |

---

## Settings Extensions

Añadir campo de configuración de logging en `src/core/config.py`:

```python
# Campo de logging (añadir a la clase Settings existente)
log_format: str = "text"  # "text" | "json"

# Campos de timeout (añadir a la clase Settings existente)
api_statement_timeout_seconds: int = 5  # Timeout para queries de API
```

Variables de entorno:
- `LOG_FORMAT=text|json`
- `API_STATEMENT_TIMEOUT_SECONDS=5`

> **Nota:** `SCHEDULER_STATEMENT_TIMEOUT_SECONDS` se define en Spec-50.

---

## Logging Module

### `src/infrastructure/logging/config.py`

Configuración centralizada del logging:

```python
"""Configuracion de logging estructurado.

Configura los handlers, formatters y niveles de log de la aplicacion.
En desarrollo usa formato legible con colores; en produccion usa
formato JSON para parseo automatico por herramientas de monitoreo.

Ejemplo::

    from src.infrastructure.logging.config import setup_logging

    setup_logging(log_level="info", log_format="json")
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formatter que produce JSON para cada log entry."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Añadir request_id si existe en el record
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        # Añadir exception info si existe
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    log_level: str = "info",
    log_format: str = "text",
) -> None:
    """Configura el logging de la aplicacion.

    Args:
        log_level: Nivel de logging (debug, info, warning, error).
        log_format: Formato de salida ("text" o "json").
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Handler: stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silenciar loggers verbosos de terceros
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
```

---

## Request ID Middleware

### `src/adapters/api/middleware/request_logging.py`

Middleware que genera un `request_id` por request y loggea información de cada request:

```python
"""Middleware de logging de requests.

Genera un ``request_id`` unico por request HTTP y lo propaga
a todos los logs del request via ``contextvars``. Loggea el
inicio y fin de cada request con metodo, path, status code y
duracion.

Ejemplo::

    from src.adapters.api.middleware.request_logging import RequestLoggingMiddleware

    app.add_middleware(RequestLoggingMiddleware)
"""
from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Request ID propagado via contextvar para correlacion de logs
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware que loggea cada request con request_id y duracion.

    Excluye rutas de health check para reducir ruido en logs.
    """

    EXCLUDED_PATHS: set[str] = {"/v1/health", "/health"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> None:
        # Excluir health checks del logging
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        start_time = time.monotonic()
        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)

        # Log request start
        logger.info(
            "Request started: %s %s",
            request.method,
            request.url.path,
            extra={"request_id": req_id},
        )

        response = await call_next(request)

        # Log request end with duration
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "Request completed: %s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": req_id},
        )

        # Añadir request_id a los headers de respuesta para debugging
        response.headers["X-Request-ID"] = req_id

        return response


def get_request_id() -> str | None:
    """Obtiene el request_id actual del contexto.

    Returns:
        El request_id del request actual, o None si no hay request.
    """
    return request_id_ctx.get()
```

---

## DB Timeout Configuration

### Actualización de `src/infrastructure/db/connection.py`

`statement_timeout` se configura via `server_settings` en `create_pool()`, no via `SET statement_timeout` después de crear el pool. Esto asegura que el timeout se aplique a **todas** las conexiones del pool, no solo a la primera.

```python
# En la funcion init_pool(), al crear el pool:
_pool = await asyncpg.create_pool(
    dsn=settings.database_url,
    min_size=settings.db_pool_min_size,
    max_size=settings.db_pool_max_size,
    server_settings={
        "statement_timeout": str(settings.api_statement_timeout_seconds * 1000)
    },
)
```

**Bug corregido:** El enfoque anterior (`SET statement_timeout = $1` despues de crear el pool) solo afectaba la primera conexion, dejando las demas sin timeout. Con `server_settings`, cada conexion del pool hereda el timeout automaticamente.

**Double-init guard:** Si `init_pool()` se llama cuando ya existe un pool (ej: en tests o hot reload), se cierra el pool existente antes de crear uno nuevo, con un warning log.

### Timeout por operación

| Operación | Timeout | Configuración |
|-----------|---------|---------------|
| Queries de API (GET/POST) | 5s (default) | `API_STATEMENT_TIMEOUT_SECONDS` via pool `server_settings` |

**Nota:** El refresh job ya no usa `SET LOCAL statement_timeout` porque no funcionaba con `pool.execute()` sin transaccion. Ahora hereda el timeout del pool via `server_settings`. El `retry_with_backoff` en `_do_refresh` tolera timeouts y conflictos.

---

## Application Logging Module

### `src/infrastructure/logging/__init__.py`

```python
"""Logging module — configuracion y utilidades de logging."""
from __future__ import annotations

from src.infrastructure.logging.config import setup_logging

__all__ = ["setup_logging"]
```

---

## Lifespan Integration

Actualizar `src/main.py` para configurar logging al inicio:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()

    # F5: Configurar logging
    from src.infrastructure.logging import setup_logging
    setup_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    await init_pool(settings)
    # ... resto del lifespan ...
```

---

## Error Enhancement

### Actualización del Error Handler

Los error handlers de Spec-42 se actualizan para incluir `request_id` en las respuestas de error:

```python
from src.adapters.api.middleware.request_logging import get_request_id

@app.exception_handler(InsufficientStockError)
async def handle_insufficient_stock(
    request, exc: InsufficientStockError
) -> JSONResponse:
    req_id = get_request_id()
    logger.warning(
        "Insufficient stock: product_id=%s requested=%s available=%s",
        exc.product_id, exc.requested, exc.available,
        extra={"request_id": req_id},
    )
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INSUFFICIENT_STOCK",
                message=str(exc),
                details={
                    "product_id": exc.product_id,
                    "requested": exc.requested,
                    "available": exc.available,
                    "request_id": req_id,  # Para debugging
                },
            )
        ).model_dump(),
    )
```

---

## Log Format Examples

### Development (text)

```
2026-05-19 10:30:45 | INFO     | src.infrastructure.scheduler.scheduler | Scheduler started — refresh every 5 minutes
2026-05-19 10:30:46 | INFO     | src.adapters.api.middleware.request_logging | Request started: POST /v1/movements
2026-05-19 10:30:46 | INFO     | src.adapters.api.middleware.request_logging | Request completed: POST /v1/movements -> 201 (23.4ms)
2026-05-19 10:35:00 | INFO     | src.infrastructure.scheduler.scheduler | Starting mv_stock_historical refresh
2026-05-19 10:35:00 | INFO     | src.infrastructure.db.refresh           | mv_stock_historical refreshed successfully
2026-05-19 10:35:00 | INFO     | src.infrastructure.scheduler.scheduler | mv_stock_historical refreshed in 0.42s
```

### Production (JSON)

```json
{"timestamp": "2026-05-19T10:30:45.123456+00:00", "level": "INFO", "logger": "src.infrastructure.scheduler.scheduler", "message": "Scheduler started — refresh every 5 minutes", "module": "scheduler", "function": "start_scheduler", "line": 42}
{"timestamp": "2026-05-19T10:30:46.234567+00:00", "level": "INFO", "logger": "src.adapters.api.middleware.request_logging", "message": "Request started: POST /v1/movements", "module": "request_logging", "function": "dispatch", "line": 35, "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"}
```

---

## Files

| File | Description |
|------|-------------|
| `src/core/config.py` | Añadir campos `log_format`, `api_statement_timeout_seconds` |
| `src/infrastructure/logging/config.py` | Logging setup + JSON formatter |
| `src/infrastructure/logging/__init__.py` | Re-exports públicos |
| `src/adapters/api/middleware/request_logging.py` | Request ID middleware (excluye `/v1/health`) |
| `src/infrastructure/db/connection.py` | Configurar `statement_timeout` con Settings |
| `src/main.py` | Integrar logging setup en lifespan |
| `src/adapters/api/middleware/error_handler.py` | Añadir request_id a errores |

---

## Acceptance Criteria

- [ ] `setup_logging()` configura logging con formato text o JSON según `LOG_FORMAT`
- [ ] JSON format produce un JSON válido por línea con timestamp, level, logger, message
- [ ] Text format produce salida legible con timestamp, level, logger name, message
- [ ] `RequestLoggingMiddleware` genera un `request_id` único por request
- [ ] `request_id` se incluye en los headers de respuesta (`X-Request-ID`)
- [ ] `request_id` se propaga a todos los logs del request via `contextvars`
- [ ] `/v1/health` se excluye del request logging (no genera logs ni request_id)
- [ ] `statement_timeout` se configura en el pool usando `API_STATEMENT_TIMEOUT_SECONDS`
- [ ] Loggers de terceros (uvicorn.access, asyncio) se silencian a WARNING
- [ ] Tests unitarios validan JSON formatter output
- [ ] Tests de integración validan que `X-Request-ID` se devuelve en responses
- [ ] `make lint` pasa sin errores

---

## Testing Strategy

- **Test unitario de `JSONFormatter`**: verificar que produce JSON válido con los campos esperados
- **Test unitario de `setup_logging()`**: verificar que los handlers se configuran correctamente (mock de root logger)
- **Test unitario de `get_request_id()`**: verificar que retorna None fuera de request y el ID correcto dentro
- **Test de integración de middleware**: hacer request a la app, verificar que `X-Request-ID` está en los headers
- **Test de correlación**: verificar que el mismo `request_id` aparece en múltiples log entries del mismo request

### Ejemplo: Test de JSON formatter

```python
import json
import logging
from src.infrastructure.logging.config import JSONFormatter

def test_json_formatter_produces_valid_json():
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Hello %s",
        args=("world",),
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test.logger"
    assert parsed["message"] == "Hello world"
    assert parsed["module"] == "test"
    assert parsed["line"] == 42
    assert "timestamp" in parsed
```

---

## Resolved Questions

1. **¿Usar `structlog` o `logging` estándar?** → **`logging` estándar en F5.** Suficiente para los requisitos actuales. `structlog` añade una dependencia más y complejidad que no se necesita aún. Se puede migrar en F6+ si se necesita structured logging más potente.

2. **¿El middleware de logging debe afectar la latencia?** → **Mínimo.** Solo genera UUID4, loggea, y añade header. `time.monotonic()` tiene overhead negligible. En producción, el logging JSON añade ~0.1ms por request, aceptable.

3. **¿Debe incluirse tracing distribuido (OpenTelemetry)?** → **No en F5.** Demasiado complejo para la fase actual. El request_id local es suficiente para correlación dentro de la aplicación. OpenTelemetry se puede añadir en F6+ si se necesita tracing entre servicios.

4. **¿Los logs deben ir a archivo además de stdout?** → **Solo stdout.** En contenedores Docker, stdout es capturado por el runtime (Docker, K8s) y dirigido al sistema de logging centralizado. Escribir a archivo añade complejidad de rotación y gestión de espacio.

5. **¿Debe loggearse el body de los requests?** → **No.** Riesgo de loggear datos sensibles. Solo se loggea método, path, status code, duración y request_id. Si se necesita debugging de payloads, se usa el request_id para buscar en el tracing.

6. **¿Debe excluirse `/v1/health` del request logging?** → **Sí.** Los health checks son muy frecuentes (cada 10-30s en K8s/Docker) y no aportan valor diagnóstico. Se excluyen del middleware de request logging para reducir ruido. La ruta sigue funcionando normalmente, solo no genera logs.
