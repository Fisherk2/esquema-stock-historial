# TODO — F5: Scheduler & Concurrencia

## Progress: [0/11] ░░░░░░░░░░░ PENDIENTE

## Phase 1: Foundation [0/2]

- [ ] **Task 1:** Extender Settings con 6 campos F5
  - `src/core/config.py` — añadir: `scheduler_enabled`, `scheduler_refresh_interval_minutes`, `scheduler_misfire_grace_time_seconds`, `scheduler_statement_timeout_seconds`, `log_format`, `api_statement_timeout_seconds`
  - `.env.example` — añadir 6 variables con comentarios
  - Docstrings actualizados en Settings
  - Verify: `python -c "from src.core.config import Settings; s = Settings(); print(s.scheduler_enabled)"`

- [ ] **Task 2:** Crear ConcurrencyConflictError
  - `src/domain/exceptions/concurrency_conflict.py` — hereda DomainError, attrs `operation`, `detail`
  - `src/domain/exceptions/__init__.py` — re-export
  - `src/domain/__init__.py` — re-export + `__all__`
  - Verify: `from src.domain import ConcurrencyConflictError; assert issubclass(ConcurrencyConflictError, DomainError)`

### Checkpoint: Foundation Ready [ ]
- [ ] 6 campos Settings accesibles
- [ ] ConcurrencyConflictError instanciable y hereda DomainError
- [ ] `.env.example` con todas las variables nuevas
- [ ] `make lint` pasa

---

## Phase 2: Core Infrastructure [0/2]

- [ ] **Task 3:** Implementar @retry_with_backoff + tests
  - `src/core/retry.py` — decorador factory async con backoff exponencial + jitter
  - `src/core/__init__.py` — re-export `retry_with_backoff`
  - `tests/unit/core/__init__.py` — nuevo
  - `tests/unit/core/test_retry.py` — 5+ tests (éxito, reintento, fallo final, no-retryable, delay pattern)
  - Mock `asyncio.sleep` para tests rápidos
  - Verify: `pytest tests/unit/core/test_retry.py -v`

- [ ] **Task 4:** Implementar logging + tests
  - `src/infrastructure/logging/config.py` — `JSONFormatter` + `setup_logging()`
  - `src/infrastructure/logging/__init__.py` — re-export `setup_logging`
  - `tests/unit/infrastructure/logging/__init__.py` — nuevo
  - `tests/unit/infrastructure/logging/test_config.py` — 4+ tests (JSON válido, request_id, exception, setup_logging)
  - Verify: `pytest tests/unit/infrastructure/logging/test_config.py -v`

### Checkpoint: Core Infrastructure Ready [ ]
- [ ] Retry decorator funciona y tests pasan
- [ ] JSON formatter produce JSON válido con todos los campos
- [ ] `setup_logging` configura logger root correctamente
- [ ] `make lint` pasa

---

## Phase 3: HTTP Layer [0/2]

- [ ] **Task 5:** Implementar RequestLoggingMiddleware + tests integración
  - `src/adapters/api/middleware/request_logging.py` — `request_id_ctx`, `RequestLoggingMiddleware`, `get_request_id()`
  - Excluye `/v1/health` y `/health`
  - UUID4 + contextvars + `X-Request-ID` header + timing
  - `tests/integration/api/test_request_logging.py` — 3 tests (X-Request-ID presente, health excluido, unique per request)
  - Verify: `pytest tests/integration/api/test_request_logging.py -v`

- [ ] **Task 6:** Actualizar error handler
  - `src/adapters/api/middleware/error_handler.py` — handler `ConcurrencyConflictError` → HTTP 409 `CONCURRENCY_CONFLICT`
  - Handler registrado **ANTES** de `DomainError` genérico
  - `request_id` de `get_request_id()` en respuestas de error
  - Tests de ConcurrencyConflictError añadidos
  - Verify: `pytest tests/unit/domain/test_exceptions.py -v` (o archivo apropiado)

### Checkpoint: HTTP Layer Ready [ ]
- [ ] RequestLoggingMiddleware añade X-Request-ID a respuestas
- [ ] Health endpoints excluidos del logging
- [ ] ConcurrencyConflictError handler retorna 409
- [ ] `request_id` incluido en respuestas de error
- [ ] `make lint` pasa

---

## Phase 4: Scheduler & Integration [0/3]

- [ ] **Task 7:** Configurar statement_timeout
  - `src/infrastructure/db/connection.py` — `init_pool()` ejecuta `SET statement_timeout`
  - Valor: `settings.api_statement_timeout_seconds * 1000` (ms)
  - Default 5000ms, fallback graceful con log warning
  - Verify: `python -c "from src.infrastructure.db.connection import init_pool; ..."`

- [ ] **Task 8:** Implementar scheduler module + tests
  - `src/infrastructure/scheduler/scheduler.py` — `_RETRYABLE_EXCEPTIONS`, `_refresh_job()` con `@retry_with_backoff`, `create_scheduler()`, `start_scheduler()`, `shutdown_scheduler()`
  - `_refresh_job` usa `pool.acquire() + conn.transaction()` para `SET LOCAL statement_timeout`
  - `src/infrastructure/scheduler/__init__.py` — re-exports
  - `tests/unit/infrastructure/scheduler/__init__.py` — nuevo
  - `tests/unit/infrastructure/scheduler/test_scheduler.py` — 5+ tests (create, job params, enabled/disabled, shutdown, refresh)
  - Todos los tests con mocks
  - Verify: `pytest tests/unit/infrastructure/scheduler/test_scheduler.py -v`

- [ ] **Task 9:** Integrar en main.py + aislamiento de tests
  - `src/main.py` — `setup_logging()` antes de `init_pool()`, `RequestLoggingMiddleware` en `create_app()`, scheduler en lifespan, version 0.5.0
  - `tests/conftest.py` — `SCHEDULER_ENABLED=false` via monkeypatch
  - Todos los tests F0-F4 siguen pasando
  - Verify: `pytest tests/ -v --co -q` sin errores de import

### Checkpoint: Integration Complete [ ]
- [ ] Scheduler inicia y para con lifecycle de la app
- [ ] Logging configurado al startup
- [ ] Request middleware activo
- [ ] `SCHEDULER_ENABLED=false` previene scheduler en tests
- [ ] `make lint` pasa

---

## Phase 5: Validación & Documentación [0/2]

- [ ] **Task 10:** Build completo con cobertura
  - `make lint` → 0 errores
  - `make test` → todos verdes (F0-F5)
  - Coverage `src/core/retry.py` > 80%
  - Coverage `src/infrastructure/scheduler/` > 70%
  - Coverage `src/infrastructure/logging/` > 70%
  - Total tests: 255+ (235 existentes + 20+ nuevos)
  - Version 0.5.0 en `main.py`
  - Verify: `make build` exit code 0; `make test-cov` targets cumplidos

- [ ] **Task 11:** Actualizar documentación del proyecto
  - `WORKFLOW.md` — F5 status con descripción precisa
  - `docs/workflow/spec-tracking.md` — Spec-50/51/52 verificados
  - `docs/workflow/roadmap-phases.md` — F5 status "Completado"
  - `AGENTS.md` — Fase actualizada
  - `SPEC.md` — F5 success criteria verificados
  - Verify: revisión de archivos actualizados

### Checkpoint: F5 Complete [ ]
- [ ] Todos los criterios de Spec-50/51/52 cumplidos
- [ ] `make build` pasa
- [ ] Coverage targets cumplidos para todos los módulos nuevos
- [ ] 20+ nuevos tests pasan
- [ ] Sin regresiones en tests F0-F4 existentes
- [ ] Documentación actualizada y precisa
- [ ] Listo para revisión humana → F6

---

## Summary

| Phase | Tasks | Completed |
|-------|-------|-----------|
| Phase 1: Foundation | 2 | 0/2 |
| Phase 2: Core Infrastructure | 2 | 0/2 |
| Phase 3: HTTP Layer | 2 | 0/2 |
| Phase 4: Scheduler & Integration | 3 | 0/3 |
| Phase 5: Validación & Docs | 2 | 0/2 |
| **Total** | **11** | **0/11** |

---

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

## Resolved Decisions (F5-Q11 through F5-Q14)

All 4 decisions from the implementation questionnaire are confirmed:
- `SET LOCAL` scoped via `pool.acquire() + conn.transaction()` in `_refresh_job` (F5-Q11)
- `SCHEDULER_ENABLED=false` in `tests/conftest.py` via monkeypatch (F5-Q12)
- Overwrite F4 plan/todo files (historical) (F5-Q13)
- Retry only on `_refresh_job`, not on use cases (F5-Q14)
