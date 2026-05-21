# SPEC-52: Structured Logging & Errors

**Phase:** F5 — Scheduler & Concurrency  
**Dependencies:** Spec-42 (FastAPI Routes) ✅ Completed, Spec-51 (Retry/Conc) ✅ Completed  
**Priority:** Medium  
**Status:** Pending  

---

## Objective

Configure a structured logging system that provides complete visibility into application behavior in development and production. Implement JSON logging in production, readable logging in development, request logging middleware for FastAPI, and DB timeout configuration. Logging is the foundation for debugging, monitoring, and alerting.

**Design principles:**
- **Structured logging** — each log entry is an object with consistent fields (timestamp, level, module, message, extra)
- **Environment-based format** — readable in development (color, text), JSON in production (parseable by tools)
- **Request correlation** — each HTTP request has a unique `request_id` that propagates to all related logs
- **Zero sensitive data** — never log passwords, tokens, or personal data
- **Performance aware** — async or buffered logging to avoid blocking the event loop
- **Graceful degradation** — if logging fails, the application continues functioning

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| Python standard `logging` (no structlog in F5) | No extra dependency. `logging` is sufficient for F5. Can migrate to structlog in F6+ if more power is needed |
| JSON formatter in production | Compatible with ELK, Datadog, CloudWatch. Each line is parseable JSON |
| Colored output in development | Readability for developers. `logging` with custom formatter |
| Request ID via middleware | Log correlation per request. UUID4 per request, passed to handlers via contextvars |
| `contextvars` for request_id | Thread-safe and async-safe. Automatic propagation within the same request |
| DB `statement_timeout` configured | Prevent infinite queries. Configurable via Settings: 5s for API, 30s for refresh |
| Exclude `/v1/health` from request logging | Health checks are frequent (K8s/Docker) and add no value to logs |
| Log level per module | `uvicorn` at WARNING (verbose), `asyncpg` at WARNING, app modules at INFO/DEBUG |

---

## Settings Extensions

Add logging configuration field in `src/core/config.py`:

```python
# Logging field (add to existing Settings class)
log_format: str = "text"  # "text" | "json"

# Timeout fields (add to existing Settings class)
api_statement_timeout_seconds: int = 5  # Timeout for API queries
```

Environment variables:
- `LOG_FORMAT=text|json`
- `API_STATEMENT_TIMEOUT_SECONDS=5`

> **Note:** `SCHEDULER_STATEMENT_TIMEOUT_SECONDS` is defined in Spec-50.

---

## Logging Module

### `src/infrastructure/logging/config.py`

Centralized logging configuration:

```python
"""Structured logging configuration.

Configures the application's handlers, formatters, and log levels.
In development it uses a readable format with colors; in production it uses
JSON format for automatic parsing by monitoring tools.

Example::

    from src.infrastructure.logging.config import setup_logging

    setup_logging(log_level="info", log_format="json")
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Formatter that produces JSON for each log entry."""

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

        # Add request_id if it exists in the record
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        # Add exception info if it exists
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    log_level: str = "info",
    log_format: str = "text",
) -> None:
    """Configure application logging.

    Args:
        log_level: Logging level (debug, info, warning, error).
        log_format: Output format ("text" or "json").
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

    # Silence verbose third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
```

---

## Request ID Middleware

### `src/adapters/api/middleware/request_logging.py`

Middleware that generates a `request_id` per request and logs information for each request:

```python
"""Request logging middleware.

Generates a unique ``request_id`` per HTTP request and propagates it
to all request logs via ``contextvars``. Logs the
start and end of each request with method, path, status code and
duration.

Example::

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

# Request ID propagated via contextvar for log correlation
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs each request with request_id and duration.

    Excludes health check routes to reduce noise in logs.
    """

    EXCLUDED_PATHS: set[str] = {"/v1/health", "/health"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> None:
        # Exclude health checks from logging
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

        # Add request_id to response headers for debugging
        response.headers["X-Request-ID"] = req_id

        return response


def get_request_id() -> str | None:
    """Get the current request_id from context.

    Returns:
        The request_id of the current request, or None if there is no request.
    """
    return request_id_ctx.get()
```

---

## DB Timeout Configuration

### Update to `src/infrastructure/db/connection.py`

`statement_timeout` is configured via `server_settings` in `create_pool()`, not via `SET statement_timeout` after creating the pool. This ensures the timeout applies to **all** pool connections, not just the first one.

```python
# In the init_pool() function, when creating the pool:
_pool = await asyncpg.create_pool(
    dsn=settings.database_url,
    min_size=settings.db_pool_min_size,
    max_size=settings.db_pool_max_size,
    server_settings={
        "statement_timeout": str(settings.api_statement_timeout_seconds * 1000)
    },
)
```

**Bug fixed:** The previous approach (`SET statement_timeout = $1` after creating the pool) only affected the first connection, leaving the rest without a timeout. With `server_settings`, each pool connection inherits the timeout automatically.

**Double-init guard:** If `init_pool()` is called when a pool already exists (e.g., in tests or hot reload), the existing pool is closed before creating a new one, with a warning log.

### Timeout per operation

| Operation | Timeout | Configuration |
|-----------|---------|---------------|
| API queries (GET/POST) | 5s (default) | `API_STATEMENT_TIMEOUT_SECONDS` via pool `server_settings` |

**Note:** The refresh job no longer uses `SET LOCAL statement_timeout` because it did not work with `pool.execute()` without a transaction. It now inherits the pool timeout via `server_settings`. The `retry_with_backoff` in `_do_refresh` handles timeouts and conflicts.

---

## Application Logging Module

### `src/infrastructure/logging/__init__.py`

```python
"""Logging module — logging configuration and utilities."""
from __future__ import annotations

from src.infrastructure.logging.config import setup_logging

__all__ = ["setup_logging"]
```

---

## Lifespan Integration

Update `src/main.py` to configure logging at startup:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()

    # F5: Configure logging
    from src.infrastructure.logging import setup_logging
    setup_logging(
        log_level=settings.log_level,
        log_format=settings.log_format,
    )

    await init_pool(settings)
    # ... rest of lifespan ...
```

---

## Error Enhancement

### Error Handler Update

Error handlers from Spec-42 are updated to include `request_id` in error responses:

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
                    "request_id": req_id,  # For debugging
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
| `src/core/config.py` | Add `log_format`, `api_statement_timeout_seconds` fields |
| `src/infrastructure/logging/config.py` | Logging setup + JSON formatter |
| `src/infrastructure/logging/__init__.py` | Public re-exports |
| `src/adapters/api/middleware/request_logging.py` | Request ID middleware (excludes `/v1/health`) |
| `src/infrastructure/db/connection.py` | Configure `statement_timeout` with Settings |
| `src/main.py` | Integrate logging setup in lifespan |
| `src/adapters/api/middleware/error_handler.py` | Add request_id to errors |

---

## Acceptance Criteria

- [ ] `setup_logging()` configures logging with text or JSON format based on `LOG_FORMAT`
- [ ] JSON format produces valid JSON per line with timestamp, level, logger, message
- [ ] Text format produces readable output with timestamp, level, logger name, message
- [ ] `RequestLoggingMiddleware` generates a unique `request_id` per request
- [ ] `request_id` is included in response headers (`X-Request-ID`)
- [ ] `request_id` propagates to all request logs via `contextvars`
- [ ] `/v1/health` is excluded from request logging (does not generate logs or request_id)
- [ ] `statement_timeout` is configured on the pool using `API_STATEMENT_TIMEOUT_SECONDS`
- [ ] Third-party loggers (uvicorn.access, asyncio) are silenced to WARNING
- [ ] Unit tests validate JSON formatter output
- [ ] Integration tests validate that `X-Request-ID` is returned in responses
- [ ] `make lint` passes without errors

---

## Testing Strategy

- **Unit test for `JSONFormatter`**: verify it produces valid JSON with expected fields
- **Unit test for `setup_logging()`**: verify handlers are configured correctly (mock root logger)
- **Unit test for `get_request_id()`**: verify it returns None outside a request and the correct ID inside
- **Middleware integration test**: make a request to the app, verify `X-Request-ID` is in the headers
- **Correlation test**: verify the same `request_id` appears in multiple log entries from the same request

### Example: JSON formatter test

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

1. **Use `structlog` or standard `logging`?** → **Standard `logging` in F5.** Sufficient for current requirements. `structlog` adds an extra dependency and complexity that is not needed yet. Can migrate in F6+ if more powerful structured logging is needed.

2. **Should the logging middleware affect latency?** → **Minimally.** It only generates a UUID4, logs, and adds a header. `time.monotonic()` has negligible overhead. In production, JSON logging adds ~0.1ms per request, which is acceptable.

3. **Should distributed tracing (OpenTelemetry) be included?** → **Not in F5.** Too complex for the current phase. The local request_id is sufficient for correlation within the application. OpenTelemetry can be added in F6+ if cross-service tracing is needed.

4. **Should logs go to a file in addition to stdout?** → **Only stdout.** In Docker containers, stdout is captured by the runtime (Docker, K8s) and directed to the centralized logging system. Writing to a file adds rotation and space management complexity.

5. **Should request bodies be logged?** → **No.** Risk of logging sensitive data. Only method, path, status code, duration, and request_id are logged. If payload debugging is needed, the request_id is used to search in tracing.

6. **Should `/v1/health` be excluded from request logging?** → **Yes.** Health checks are very frequent (every 10-30s in K8s/Docker) and provide no diagnostic value. They are excluded from the request logging middleware to reduce noise. The route continues to function normally, it just does not generate logs.
