# Implementation Plan: F5 — Scheduler & Concurrencia

## Overview

F5 integrates three infrastructure components that provide resilience and observability: (1) **APScheduler** as a background task engine for periodic refresh of the `mv_stock_historical` materialized view, (2) a **retry decorator with exponential backoff + jitter** to handle transactional conflicts, and (3) **structured logging with request correlation and configurable DB timeouts**.

**What's done (baseline from F0–F4):**
- 235 tests (147 unit + 88 integration), `make lint` clean, version 0.4.0
- `apscheduler==3.11.2` already in `requirements.txt`
- `src/infrastructure/scheduler/__init__.py` — empty placeholder with comment
- `src/infrastructure/logging/__init__.py` — empty placeholder with comment
- `src/infrastructure/db/refresh.py` — `refresh_stock_view(pool)` function exists
- `src/adapters/api/middleware/error_handler.py` — 6 exception handlers registered
- `src/core/config.py` — Settings class with 6 fields
- Domain exceptions: `DomainError` base + 4 concrete exceptions

**What's missing (this plan):**
- Extend Settings with 6 new F5 fields (scheduler, logging, timeouts)
- Create `ConcurrencyConflictError` domain exception
- Implement `@retry_with_backoff` async decorator
- Implement logging infrastructure (JSONFormatter + `setup_logging()`)
- Implement `RequestLoggingMiddleware` with `contextvars` for `request_id`
- Add `ConcurrencyConflictError` → HTTP 409 handler in error_handler.py + `request_id` in error responses
- Configure `statement_timeout` on the DB pool
- Implement scheduler module (create/start/shutdown + `_refresh_job`)
- Integrate logging + middleware + scheduler in `main.py` lifespan
- Enforce `SCHEDULER_ENABLED=false` in `tests/conftest.py`
- Version bump to 0.5.0
- Documentation updates (WORKFLOW.md, spec-tracking.md, roadmap-phases.md, AGENTS.md, SPEC.md)

## Architecture Decisions (4 Resolved Questions)

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| F5-Q11 | `SET LOCAL` scope in `_refresh_job`? | `pool.acquire() + conn.transaction()` | Ensures statement_timeout is scoped to the refresh transaction only |
| F5-Q12 | Scheduler test isolation? | `SCHEDULER_ENABLED=false` in `tests/conftest.py` | Prevents scheduler from starting during tests |
| F5-Q13 | File destination for plan/todo? | Overwrite `tasks/plan.md` and `tasks/todo.md` | F4 completed; files are historical working documents |
| F5-Q14 | Retry scope? | Only on `_refresh_job`, not on use cases | Spec-40 use cases are completed; adding retry would break existing tests |

## Dependency Graph

```
Domain (F2) + Infrastructure (F3) + Application Layer (F4) + API (F4)
│
├── Settings Extension (Task 1) ←─────────────────────────────────────┐
│   └── config.py: 6 new fields                                       │
│       └── .env.example: 6 new vars                                  │
│                                                                     │
├── ConcurrencyConflictError (Task 2) ←── DomainError (F2)            │
│   └── domain/exceptions/                                            │
│       └── __init__.py re-exports                                    │
│                                                                     │
├── @retry_with_backoff (Task 3) ←── ConcurrencyConflictError (T2) ───┤
│   └── core/retry.py                                                 │
│       └── tests/unit/core/test_retry.py                             │
│                                                                     │
├── Logging Infrastructure (Task 4) ←── Settings (T1)                 │
│   └── infrastructure/logging/config.py                              │
│       └── tests/unit/infrastructure/logging/test_config.py          │
│                                                                     │
├── RequestLoggingMiddleware (Task 5) ←── contextvars                 │
│   └── adapters/api/middleware/request_logging.py                    │
│       └── tests/integration/api/test_request_logging.py             │
│                                                                     │
├── Error Handler Update (Task 6) ←── ConcurrencyConflictError (T2) ──┤
│   └── adapters/api/middleware/error_handler.py                      │
│       └── request_id from get_request_id() (T5)                     │
│                                                                     │
├── statement_timeout (Task 7) ←── Settings (T1)                      │
│   └── infrastructure/db/connection.py                               │
│                                                                     │
├── Scheduler Module (Task 8) ←── retry (T3) + refresh (F3) + T7 ────┤
│   └── infrastructure/scheduler/scheduler.py                         │
│       └── tests/unit/infrastructure/scheduler/test_scheduler.py     │
│                                                                     │
├── Main Integration (Task 9) ←── T1+T4+T5+T8                         │
│   └── main.py: lifespan + middleware + version bump                 │
│       └── tests/conftest.py: SCHEDULER_ENABLED=false                │
│                                                                     │
└── Build Validation (Task 10) ←── ALL PREVIOUS ──────────────────────┘
    └── Documentation (Task 11) ←── Task 10
```

## Vertical Slicing Strategy

Each slice tests one complete feature path from configuration to integration:

```
Slice 1: Settings extension (shared foundation) — Task 1
Slice 2: ConcurrencyConflictError (domain exception) — Task 2 (independent, parallel with T1)
Slice 3: Retry decorator (core infrastructure) — Task 3
Slice 4: Logging infrastructure (observability) — Task 4
Slice 5: Request middleware (HTTP layer) — Task 5
Slice 6: Error handler update (HTTP layer) — Task 6
Slice 7: statement_timeout (DB layer) — Task 7
Slice 8: Scheduler module (task engine) — Task 8
Slice 9: Main integration (glue) — Task 9
Slice 10: Build validation (quality gate) — Task 10
Slice 11: Documentation (knowledge) — Task 11
```

---

## Phase 1: Foundation

### Task 1: Extend Settings (SPEC-52)

**Description:** Add 6 new fields to `src/core/config.py` Settings class for F5: scheduler configuration, logging format, and DB timeout settings. Update `.env.example` with the corresponding environment variables and comments.

**Acceptance criteria:**
- [ ] `scheduler_enabled: bool = True` — Master toggle for scheduler
- [ ] `scheduler_refresh_interval_minutes: int = 5` — Refresh interval
- [ ] `scheduler_misfire_grace_time_seconds: int = 30` — Misfire tolerance
- [ ] `scheduler_statement_timeout_seconds: int = 30` — Refresh job timeout
- [ ] `log_format: str = "text"` — "text" or "json"
- [ ] `api_statement_timeout_seconds: int = 5` — API request timeout
- [ ] `.env.example` updated with 6 new variables and comments
- [ ] Docstrings updated on Settings class
- [ ] `make lint` passes

**Verification:**
- [ ] `python -c "from src.core.config import Settings; s = Settings(); print(s.scheduler_enabled, s.log_format)"` succeeds
- [ ] `.env.example` contains all 6 new variables

**Dependencies:** None

**Files likely touched:**
- `src/core/config.py`
- `.env.example`

**Estimated scope:** S (2 files)

---

### Task 2: Create ConcurrencyConflictError (SPEC-51)

**Description:** Create a new domain exception class `ConcurrencyConflictError` that inherits from `DomainError`. It has attributes `operation: str` and `detail: str | None`. The message format is `"Concurrency conflict on '{operation}'"`. Update re-exports in `__init__.py` files.

**Acceptance criteria:**
- [ ] `src/domain/exceptions/concurrency_conflict.py` exists with class
- [ ] Inherits from `DomainError`
- [ ] Has `operation: str` attribute
- [ ] Has `detail: str | None = None` attribute
- [ ] Message format: `"Concurrency conflict on '{operation}'"`
- [ ] Re-exported in `src/domain/exceptions/__init__.py`
- [ ] Re-exported in `src/domain/__init__.py` (imports + `__all__`)
- [ ] `make lint` passes

**Verification:**
- [ ] `python -c "from src.domain import ConcurrencyConflictError; e = ConcurrencyConflictError('test'); assert isinstance(e, DomainError)"` succeeds

**Dependencies:** None (DomainError from F2 already exists)

**Files likely touched:**
- `src/domain/exceptions/concurrency_conflict.py` (new)
- `src/domain/exceptions/__init__.py`
- `src/domain/__init__.py`

**Estimated scope:** XS (3 files, 1 new class)

---

### Checkpoint: Foundation Ready
- [ ] All 6 Settings fields accessible
- [ ] ConcurrencyConflictError is instantiable and inherits DomainError
- [ ] `.env.example` has all new variables
- [ ] `make lint` passes

---

## Phase 2: Core Infrastructure

### Task 3: Implement @retry_with_backoff + tests (SPEC-51)

**Description:** Create an async retry decorator factory in `src/core/retry.py`. The decorator wraps async functions, catches specified exceptions, and retries with exponential backoff + jitter. Formula: `delay = min(base_delay * 2^attempt + random.uniform(0, jitter), max_delay)`. Logs WARNING per retry and ERROR on final failure. Uses `functools.wraps`.

**Acceptance criteria:**
- [ ] `src/core/retry.py` exists with `retry_with_backoff()` decorator factory
- [ ] Parameters: `max_retries: int = 3`, `base_delay: float = 1.0`, `max_delay: float = 10.0`, `jitter: float = 0.5`, `exceptions: tuple[type[Exception], ...]`
- [ ] Formula: `min(base_delay * 2^attempt + random.uniform(0, jitter), max_delay)`
- [ ] Uses `functools.wraps` to preserve function metadata
- [ ] Logs WARNING for each retry attempt (include attempt number, delay, exception)
- [ ] Logs ERROR on final failure
- [ ] Non-retryable exceptions propagate immediately without retry
- [ ] `src/core/__init__.py` re-exports `retry_with_backoff`
- [ ] `tests/unit/core/__init__.py` exists
- [ ] `tests/unit/core/test_retry.py` with 5+ tests:
  - Success on first attempt
  - Success after retry
  - Final failure after max retries
  - Non-retryable exception propagates immediately
  - Default parameters work
  - Delay pattern follows formula
- [ ] Tests mock `asyncio.sleep` for fast execution
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/unit/core/test_retry.py -v` passes
- [ ] `python -c "from src.core import retry_with_backoff; print('OK')"` succeeds

**Dependencies:** Task 1 (Settings for log references), Task 2 (not required but retry may catch ConcurrencyConflictError)

**Files likely touched:**
- `src/core/retry.py` (new)
- `src/core/__init__.py`
- `tests/unit/core/__init__.py` (new)
- `tests/unit/core/test_retry.py` (new)

**Estimated scope:** M (4 files, decorator + 5+ tests)

---

### Task 4: Implement logging infrastructure + tests (SPEC-52)

**Description:** Create `src/infrastructure/logging/config.py` with a `JSONFormatter` class (subclass of `logging.Formatter`) that produces structured JSON output with fields: timestamp (ISO 8601 UTC), level, logger, message, module, function, line, request_id (from contextvar if present), exception (if exc_info). The `setup_logging(log_level, log_format)` function configures the root logger with a stdout handler, supports text or JSON format, silences `uvicorn.access` and `asyncio` to WARNING, and sets `apscheduler` to INFO.

**Acceptance criteria:**
- [ ] `src/infrastructure/logging/config.py` exists
- [ ] `JSONFormatter(logging.Formatter)` produces JSON with required fields
- [ ] Timestamp is ISO 8601 UTC (e.g., `2024-01-15T10:30:00.000Z`)
- [ ] `request_id` included when present in contextvar
- [ ] `exception` field included when `exc_info` is present
- [ ] `setup_logging(log_level: str, log_format: str)` configures root logger
- [ ] Text format for development, JSON for production
- [ ] `uvicorn.access` and `asyncio` loggers silenced to WARNING
- [ ] `apscheduler` logger set to INFO
- [ ] `src/infrastructure/logging/__init__.py` re-exports `setup_logging`
- [ ] `tests/unit/infrastructure/logging/__init__.py` exists
- [ ] `tests/unit/infrastructure/logging/test_config.py` with 4+ tests:
  - JSON formatter produces valid JSON
  - JSON formatter includes request_id
  - JSON formatter includes exception on error
  - `setup_logging` configures root logger correctly
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/unit/infrastructure/logging/test_config.py -v` passes
- [ ] `python -c "from src.infrastructure.logging import setup_logging; print('OK')"` succeeds

**Dependencies:** Task 1 (`setup_logging` reads log_level/log_format from Settings)

**Files likely touched:**
- `src/infrastructure/logging/config.py` (new)
- `src/infrastructure/logging/__init__.py`
- `tests/unit/infrastructure/logging/__init__.py` (new)
- `tests/unit/infrastructure/logging/test_config.py` (new)

**Estimated scope:** M (4 files, formatter + setup + 4+ tests)

---

### Checkpoint: Core Infrastructure Ready
- [ ] Retry decorator works and tests pass
- [ ] JSON formatter produces valid JSON with all required fields
- [ ] `setup_logging` configures root logger correctly
- [ ] `make lint` passes

---

## Phase 3: HTTP Layer

### Task 5: Implement RequestLoggingMiddleware + integration tests (SPEC-52)

**Description:** Create `src/adapters/api/middleware/request_logging.py` with a `ContextVar[str | None]` named `request_id_ctx`, a `RequestLoggingMiddleware` class (subclass of `BaseHTTPMiddleware`), and a `get_request_id()` helper function. The middleware generates a UUID4 for each request, sets it in the contextvar, logs the start and completion of each request with method, path, status, and duration, adds `X-Request-ID` header to the response, and excludes `/v1/health` and `/health` from logging.

**Acceptance criteria:**
- [ ] `src/adapters/api/middleware/request_logging.py` exists
- [ ] `request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)`
- [ ] `RequestLoggingMiddleware(BaseHTTPMiddleware)` class
- [ ] `EXCLUDED_PATHS: frozenset[str] = frozenset({"/v1/health", "/health"})`
- [ ] Middleware generates UUID4 for each non-excluded request
- [ ] Sets `request_id_ctx` with the UUID
- [ ] Logs request start: method, path
- [ ] Logs request completion: method, path, status code, duration (ms)
- [ ] Adds `X-Request-ID` header to response
- [ ] Excluded paths pass through without logging or header
- [ ] `get_request_id() -> str | None` helper returns current contextvar value
- [ ] `tests/integration/api/test_request_logging.py` with 3 tests:
  - `X-Request-ID` header present in response for normal endpoints
  - `/v1/health` response has no `X-Request-ID` header
  - Each request gets a unique request_id
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/integration/api/test_request_logging.py -v` passes
- [ ] `python -c "from src.adapters.api.middleware.request_logging import get_request_id; print('OK')"` succeeds

**Dependencies:** Task 1 (Settings for middleware config, if needed)

**Files likely touched:**
- `src/adapters/api/middleware/request_logging.py` (new)
- `tests/integration/api/test_request_logging.py` (new)

**Estimated scope:** M (2 files, middleware + 3 tests)

---

### Task 6: Update error handler (SPEC-51)

**Description:** Update `src/adapters/api/middleware/error_handler.py` to add a handler for `ConcurrencyConflictError` that returns HTTP 409 with error code `CONCURRENCY_CONFLICT` and details (`operation`, `detail`). Add `request_id` from `get_request_id()` to error responses (at minimum to `InsufficientStockError` handler). The new handler must be registered **BEFORE** the generic `DomainError` handler (FastAPI evaluates handlers in registration order).

**Acceptance criteria:**
- [ ] `ConcurrencyConflictError` imported in error_handler.py
- [ ] Handler registered **BEFORE** `DomainError` handler
- [ ] Returns HTTP 409 with `CONCURRENCY_CONFLICT` code
- [ ] Details include `operation` and `detail` attributes
- [ ] `request_id` added to error responses (from `get_request_id()`)
- [ ] `InsufficientStockError` handler includes `request_id` in details
- [ ] Tests added: ConcurrencyConflictError → 409 in appropriate test file
- [ ] `make lint` passes

**Verification:**
- [ ] `python -c "from src.adapters.api.middleware.error_handler import register_error_handlers; print('OK')"` succeeds
- [ ] Existing error handler tests still pass

**Dependencies:** Task 2 (`ConcurrencyConflictError`), Task 5 (`get_request_id`)

**Files likely touched:**
- `src/adapters/api/middleware/error_handler.py`

**Estimated scope:** S (1 file, 1 new handler + request_id in existing handlers)

---

### Checkpoint: HTTP Layer Ready
- [ ] RequestLoggingMiddleware adds X-Request-ID to responses
- [ ] Health endpoints excluded from logging
- [ ] ConcurrencyConflictError handler returns 409
- [ ] `request_id` included in error responses
- [ ] `make lint` passes

---

## Phase 4: Scheduler & Integration

### Task 7: Configure statement_timeout (SPEC-52)

**Description:** Update `src/infrastructure/db/connection.py` `init_pool()` to execute `SET statement_timeout = '{settings.api_statement_timeout_seconds * 1000}'` on the pool after creation. This sets a default timeout for all API queries. Include graceful fallback with log warning if the SET fails.

**Acceptance criteria:**
- [ ] `init_pool()` executes `SET statement_timeout` after pool creation
- [ ] Timeout value: `settings.api_statement_timeout_seconds * 1000` (ms)
- [ ] Default timeout: 5000ms (5s) from Settings default
- [ ] Graceful fallback: if SET fails, log warning and continue
- [ ] `make lint` passes

**Verification:**
- [ ] `python -c "import asyncio; from src.core.config import Settings; from src.infrastructure.db.connection import init_pool; asyncio.run(init_pool(Settings()))"` succeeds (with DB running)

**Dependencies:** Task 1 (`api_statement_timeout_seconds` setting)

**Files likely touched:**
- `src/infrastructure/db/connection.py`

**Estimated scope:** S (1 file)

---

### Task 8: Implement scheduler module + tests (SPEC-50)

**Description:** Create `src/infrastructure/scheduler/scheduler.py` with the scheduler integration. Define `_RETRYABLE_EXCEPTIONS` as a tuple of `(ConcurrencyConflictError, asyncpg.SerializationFailure, asyncpg.DeadlockDetectedError)`. The `_refresh_job()` function is decorated with `@retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0, jitter=0.5, exceptions=_RETRYABLE_EXCEPTIONS)`. Inside `_refresh_job`, use `async with pool.acquire() as conn: async with conn.transaction():` to execute `SET LOCAL statement_timeout` and call `refresh_stock_view()`. `create_scheduler()` returns an `AsyncIOScheduler` instance with `IntervalTrigger`, job id `refresh_stock_view`, `replace_existing=True`, `max_instances=1`. `start_scheduler()` checks `enabled` flag before starting. `shutdown_scheduler()` calls `shutdown(wait=True)`.

**Acceptance criteria:**
- [ ] `src/infrastructure/scheduler/scheduler.py` exists
- [ ] `_RETRYABLE_EXCEPTIONS` tuple defined
- [ ] `_refresh_job()` decorated with `@retry_with_backoff`
- [ ] `_refresh_job` uses `pool.acquire() + conn.transaction()` for `SET LOCAL` scope
- [ ] `create_scheduler(pool, interval_minutes, misfire_grace_time, statement_timeout)` returns `AsyncIOScheduler`
- [ ] Job registered with `IntervalTrigger`, id `refresh_stock_view`, `replace_existing=True`, `max_instances=1`
- [ ] `start_scheduler(scheduler, enabled: bool)` checks flag before starting
- [ ] `shutdown_scheduler(scheduler)` calls `scheduler.shutdown(wait=True)`
- [ ] Logs: start, completion with duration, errors
- [ ] `src/infrastructure/scheduler/__init__.py` re-exports `create_scheduler`, `start_scheduler`, `shutdown_scheduler`
- [ ] `tests/unit/infrastructure/scheduler/__init__.py` exists
- [ ] `tests/unit/infrastructure/scheduler/test_scheduler.py` with 5+ tests:
  - `create_scheduler` returns AsyncIOScheduler instance
  - Job registered with correct parameters (interval, max_instances, replace_existing)
  - `start_scheduler` does nothing when `enabled=False`
  - `start_scheduler` starts scheduler when `enabled=True`
  - `shutdown_scheduler` calls `shutdown(wait=True)`
  - `_refresh_job` calls refresh_stock_view
- [ ] All tests with mocked scheduler/pool
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/unit/infrastructure/scheduler/test_scheduler.py -v` passes
- [ ] `python -c "from src.infrastructure.scheduler import create_scheduler; print('OK')"` succeeds

**Dependencies:** Task 3 (`retry_with_backoff`), Task 7 (statement_timeout concept), existing `refresh_stock_view()` from F3

**Files likely touched:**
- `src/infrastructure/scheduler/scheduler.py` (new)
- `src/infrastructure/scheduler/__init__.py`
- `tests/unit/infrastructure/scheduler/__init__.py` (new)
- `tests/unit/infrastructure/scheduler/test_scheduler.py` (new)

**Estimated scope:** M (4 files, scheduler module + 5+ tests)

---

### Task 9: Integrate in main.py + test isolation (SPEC-50, SPEC-52)

**Description:** Update `src/main.py` to integrate all F5 components: call `setup_logging()` before `init_pool()` in lifespan, add `RequestLoggingMiddleware` in `create_app()`, start/shutdown scheduler in lifespan, and bump version to `0.5.0`. Update `tests/conftest.py` to set `SCHEDULER_ENABLED=false` via monkeypatch or environment override to prevent scheduler from starting during tests.

**Acceptance criteria:**
- [ ] `setup_logging(settings.log_level, settings.log_format)` called before `init_pool()` in lifespan
- [ ] `RequestLoggingMiddleware` added in `create_app()` (before error handlers for LIFO)
- [ ] Scheduler created with pool and settings in lifespan
- [ ] `start_scheduler()` called on startup
- [ ] `shutdown_scheduler()` called on shutdown (before `close_pool()`)
- [ ] Version bumped to `0.5.0` in FastAPI constructor
- [ ] `tests/conftest.py` sets `SCHEDULER_ENABLED=false` via monkeypatch
- [ ] All existing F0-F4 tests still pass
- [ ] `make lint` passes

**Verification:**
- [ ] `pytest tests/ -v --co -q` collects all tests (no import errors)
- [ ] `python -c "from src.main import create_app; app = create_app(); print(app.version)"` shows 0.5.0

**Dependencies:** Tasks 1, 4, 5, 8 (all F5 components)

**Files likely touched:**
- `src/main.py`
- `tests/conftest.py`

**Estimated scope:** M (2 files)

---

### Checkpoint: Integration Complete
- [ ] Scheduler starts and stops with application lifecycle
- [ ] Logging configured at startup
- [ ] Request middleware active
- [ ] `SCHEDULER_ENABLED=false` prevents scheduler in tests
- [ ] `make lint` passes

---

## Phase 5: Validation & Documentation

### Task 10: Full build validation

**Description:** Run the complete build pipeline. Verify all existing F0-F4 tests pass, new F5 tests pass, coverage targets are met, and no import violations exist.

**Acceptance criteria:**
- [ ] `make lint` passes with 0 errors
- [ ] `make test` passes (unit + integration, F0-F5)
- [ ] Coverage for `src/core/retry.py` > 80%
- [ ] Coverage for `src/infrastructure/scheduler/` > 70%
- [ ] Coverage for `src/infrastructure/logging/` > 70%
- [ ] No import violations (domain never imports infrastructure)
- [ ] Total test count: 235 + 20+ new F5 tests = 255+ tests
- [ ] Version is 0.5.0 in `main.py`
- [ ] OpenAPI `/docs` accessible with all existing endpoints

**Verification:**
- [ ] `make build` exit code 0
- [ ] `make test-cov` shows coverage targets met

**Dependencies:** All previous tasks

**Files likely touched:** None (validation only)

**Estimated scope:** XS (validation only)

---

### Task 11: Update project documentation

**Description:** Update project documentation files to reflect F5 completion. Update WORKFLOW.md, spec-tracking.md (Spec-50/51/52 checklists), roadmap-phases.md (F5 status → Completado), AGENTS.md (phase update), and SPEC.md (F5 success criteria checkboxes).

**Acceptance criteria:**
- [ ] `WORKFLOW.md` — F5 status updated with accurate description
- [ ] `docs/workflow/spec-tracking.md` — Spec-50/51/52 checklists fully verified
- [ ] `docs/workflow/roadmap-phases.md` — F5 status "Completado"
- [ ] `AGENTS.md` — Phase updated to F5 completed
- [ ] `SPEC.md` — F5 success criteria checkboxes verified

**Verification:**
- [ ] Review updated files for accuracy

**Dependencies:** Task 10

**Files likely touched:**
- `WORKFLOW.md`
- `docs/workflow/spec-tracking.md`
- `docs/workflow/roadmap-phases.md`
- `AGENTS.md`
- `SPEC.md` (F5 success criteria section only)

**Estimated scope:** S (5 files, documentation only)

---

### Checkpoint: F5 Complete
- [ ] All Spec-50/51/52 acceptance criteria met
- [ ] `make build` passes
- [ ] Coverage targets met for all new modules
- [ ] 20+ new tests pass (unit + integration)
- [ ] No regressions in existing F0-F4 tests
- [ ] Documentation accurate and up-to-date
- [ ] Ready for human review → F6

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `BaseHTTPMiddleware` + streaming responses incompatible | High | Monitor for streaming issues; migrate to pure ASGI middleware if needed |
| `AsyncIOScheduler` compatibility with FastAPI event loop | High | Use `AsyncIOScheduler` (not `BackgroundScheduler`); test in lifespan context |
| `apscheduler` 3.11.2 deprecation warnings | Medium | Pin to exact version; consider migration to 4.x in F6+ |
| `SET LOCAL` not scoped correctly in `_refresh_job` | Medium | Use `async with conn.transaction():` to ensure scope (Task 8) |
| Middleware registration order (LIFO in FastAPI) | Low | Add `RequestLoggingMiddleware` before error handlers so it runs first |

## Parallelization Opportunities

**Safe to parallelize (no shared files):**
- Tasks 1 and 2 (Settings + ConcurrencyConflictError) — completely independent
- Tasks 3 and 4 (retry + logging) — can run after T1+T2
- Tasks 5 and 6 (middleware + error handler) — can run after T2+T5 dependencies met
- Task 7 (statement_timeout) — independent after T1
- Task 11 (documentation) — parallel with T10

**Must be sequential:**
- Task 9 (main integration) after Tasks 1, 4, 5, 8 (all components it glues)
- Task 10 (build validation) after Task 9
- Task 11 (documentation) after Task 10 (needs final test counts)

## Implementation Order Reference

```
Tasks 1, 2 (parallel)
    ↓
Tasks 3, 4, 5, 7 (parallel after T1+T2)
    ↓
Task 6 (after T2+T5)
    ↓
Task 8 (after T3+T7)
    ↓
Task 9 (after T1+T4+T5+T8)
    ↓
Task 10 (after T9)
    ↓
Task 11 (after T10)
```
