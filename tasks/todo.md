# TODO — F6: Testing Integral

## Progress: [0/20] ░░░░░░░░░░░░░░░░░░░░ PENDIENTE

## Phase 1: Foundation — Dependencies & Config [0/1]

- [ ] **Task 1:** Añadir dev dependencies + pyproject.toml config
  - `requirements.txt` — +hypothesis, +pytest-benchmark
  - `pyproject.toml` — `[tool.hypothesis] max_examples=100`, addopts `--hypothesis-seed=0`, markers benchmark/e2e/security
  - Verify: `pip install -r requirements.txt` OK, `python -c "import hypothesis; import pytest_benchmark"` OK

---

## Phase 2: SPEC-60 — Unit Tests + Hypothesis + mypy strict [0/4]

- [ ] **Task 2:** Crear módulo de Hypothesis strategies
  - `tests/unit/strategies.py` — 7 strategies + 2 profiles (ci=100, dev=1000)
  - `valid_quantity_strategy`, `invalid_quantity_strategy`, `valid_sku_strategy`, `invalid_sku_strategy`
  - `movement_type_strategy`, `stock_delta_strategy`, `product_id_strategy`, `current_stock_strategy`
  - Verify: `from tests.unit.strategies import valid_quantity_strategy; print('OK')`

- [ ] **Task 3:** Añadir property-based tests para domain value objects + rules
  - `tests/unit/domain/test_quantity.py` — +2 PBT tests (valid values, rejects non-positive)
  - `tests/unit/domain/test_sku.py` — +2 PBT tests (valid format, rejects invalid)
  - `tests/unit/domain/test_rules.py` — +3 PBT tests (delta sign, never zero, insufficient stock)
  - Verify: `pytest tests/unit/domain/ -v` — 7 new + 194 existing pass

- [ ] **Task 4:** Añadir edge case tests para use cases
  - `tests/unit/application/use_cases/test_record_movement.py` — +3 (product not found, stock=0, TRANSFER sin metadata)
  - `tests/unit/application/use_cases/test_create_product.py` — +2 (duplicate SKU, nonexistent category)
  - `tests/unit/application/use_cases/test_list_products.py` — +2 (offset>total, limit=0)
  - `tests/unit/application/use_cases/test_query_current_stock.py` — +1 (sin movimientos → 0.0)
  - `tests/unit/application/use_cases/test_query_stock_at_date.py` — +1 (fecha futura → 0.0)
  - `tests/unit/application/use_cases/test_create_category.py` — +1 (nombre duplicado)
  - Verify: `pytest tests/unit/application/use_cases/ -v` — 10 new pass

- [ ] **Task 5:** Activar mypy strict en src/ + Makefile typecheck
  - `pyproject.toml` — `strict = true`, overrides `tests.*` strict=false
  - `src/**/*.py` — type annotations para pasar mypy strict
  - `Makefile` — `typecheck: mypy src/ --strict`
  - Verify: `make typecheck` exit 0, `pytest tests/ -v` still passes

### Checkpoint: SPEC-60 Complete [ ]
- [ ] Hypothesis configurado (seed=0, max_examples=100)
- [ ] 7 PBT tests en domain
- [ ] 10 edge case tests en use cases
- [ ] mypy strict pasa
- [ ] Coverage domain/ ≥90%, application/ ≥85%
- [ ] 0 regresiones en 291 tests existentes
- [ ] `make lint` pasa

---

## Phase 3: SPEC-61 — Integration Edge Cases [0/5]

- [ ] **Task 6:** Crear módulo de integration helpers
  - `tests/integration/helpers.py` — `insert_batch_movements()`, `_create_test_product()`, `_create_test_movement()`
  - Verify: `from tests.integration.helpers import insert_batch_movements; print('OK')`

- [ ] **Task 7:** Añadir repository edge case tests (4 archivos)
  - `tests/integration/repositories/test_movement_repository_edge.py` — 6 tests
  - `tests/integration/repositories/test_product_repository_edge.py` — 5 tests
  - `tests/integration/repositories/test_category_repository_edge.py` — 3 tests
  - `tests/integration/repositories/test_stock_query_repository_edge.py` — 6 tests
  - Verify: `pytest tests/integration/repositories/ -v` — 20 new + 97 existing pass

- [ ] **Task 8:** Añadir MV edge case tests
  - `tests/integration/test_mv_stock_edge.py` — 5 tests (100 movements, concurrent refresh, truncate, multi-product, 500 batch)
  - Verify: `pytest tests/integration/test_mv_stock_edge.py -v` — 5 pass

- [ ] **Task 9:** Añadir UoW edge case tests
  - `tests/integration/test_uow_edge.py` — 4 tests (rollback, shared connection, nested, connection released)
  - Verify: `pytest tests/integration/test_uow_edge.py -v` — 4 pass

- [ ] **Task 10:** Añadir API edge case tests (4 archivos)
  - `tests/integration/api/test_movements_api_edge.py` — 6 tests
  - `tests/integration/api/test_stock_api_edge.py` — 3 tests
  - `tests/integration/api/test_products_api_edge.py` — 5 tests
  - `tests/integration/api/test_categories_api_edge.py` — 3 tests
  - Verify: `pytest tests/integration/api/ -v` — 17 new pass

### Checkpoint: SPEC-61 Complete [ ]
- [ ] Integration helpers con batch insert
- [ ] 20 repository edge tests (4 archivos)
- [ ] 5 MV edge tests
- [ ] 4 UoW edge tests
- [ ] 17 API edge tests (4 archivos)
- [ ] Coverage infrastructure/ ≥70%
- [ ] 0 regresiones en 97 tests de integración existentes
- [ ] `make lint` pasa

---

## Phase 4: SPEC-62 — E2E & Latencia <100ms [0/4]

- [ ] **Task 11:** Crear E2E conftest + SLA gate hook
  - `tests/e2e/conftest.py` — api_client fixture + `STOCK_SLA_MS=100.0` + `pytest_benchmark_compare_stats` hook
  - Verify: `pytest tests/e2e/ --co -q` — no import errors

- [ ] **Task 12:** Crear stock latency benchmark tests
  - `tests/e2e/test_stock_latency.py` — 3 benchmark tests (current, at-date, no movements)
  - Helper `_setup_product_with_movements(client)`
  - Verify: `pytest tests/e2e/test_stock_latency.py -v --benchmark-only` — p95 < 100ms

- [ ] **Task 13:** Crear full flow E2E tests
  - `tests/e2e/test_full_flows.py` — 3 tests (happy path, insufficient stock, historical consistency)
  - Verify: `pytest tests/e2e/test_full_flows.py -v` — 3 pass

- [ ] **Task 14:** Crear OpenAPI contract validation tests
  - `tests/e2e/test_openapi_contracts.py` — 4 tests (movement, stock, product list, category)
  - Uses `model_validate()` against Pydantic DTOs
  - Verify: `pytest tests/e2e/test_openapi_contracts.py -v` — 4 pass

### Checkpoint: SPEC-62 Complete [ ]
- [ ] SLA gate hook falla si p95 > 100ms
- [ ] 3 benchmark tests — p95 < 100ms
- [ ] 3 full flow tests
- [ ] 4 contract validation tests
- [ ] 0 regresiones
- [ ] `make lint` pasa

---

## Phase 5: SPEC-63 — Security Tests [0/4]

- [ ] **Task 15:** Crear security test conftest
  - `tests/security/__init__.py` — package marker
  - `tests/security/conftest.py` — reutiliza api_client + db_pool fixtures
  - Verify: `pytest tests/security/ --co -q` — no import errors

- [ ] **Task 16:** Crear SQL injection tests (OWASP 4 capas)
  - `tests/security/test_sql_injection.py` — 4 test classes
  - 7 path payloads + 13 string payloads
  - Path params (4×7=28 cases), query params (4), body fields (2×13=26 cases), repo level (3)
  - Verify: `pytest tests/security/test_sql_injection.py -v` — all pass, `movements` table still exists

- [ ] **Task 17:** Crear input validation tests
  - `tests/security/test_input_validation.py` — 5 test classes
  - Movement validation (12), product validation (4), category validation (3), malformed (5), Unicode (3)
  - Verify: `pytest tests/security/test_input_validation.py -v` — 27 tests pass

- [ ] **Task 18:** Crear error leakage + immutability tests
  - `tests/security/test_error_leakage.py` — 2 test classes
  - Error leakage (3) + immutability 405 (3)
  - 8 leakage patterns + 9 SQL leakage patterns
  - Verify: `pytest tests/security/test_error_leakage.py -v` — 6 tests pass

### Checkpoint: SPEC-63 Complete [ ]
- [ ] SQL injection: 4 capas validadas (path, query, body, repo)
- [ ] Input validation: 27 tests
- [ ] Error leakage: body-only checks, 6 tests
- [ ] Immutability: PUT/PATCH/DELETE → 405
- [ ] 0 regresiones
- [ ] `make lint` pasa

---

## Phase 6: Validación & Documentación [0/2]

- [ ] **Task 19:** Build completo con coverage gates
  - `make lint` → 0 errores
  - `make typecheck` → 0 errores
  - `make test` → todos verdes (F0-F6)
  - Coverage domain/ ≥90%, application/ ≥85%, infrastructure/ ≥70%, global ≥80%
  - Total tests: 370+ (291 existentes + 80+ nuevos)
  - Verify: `make build` exit 0

- [ ] **Task 20:** Actualizar documentación del proyecto
  - `WORKFLOW.md` — F6 status "Completada"
  - `docs/workflow/spec-tracking.md` — SPEC-60/61/62/63 verificados
  - `SPEC.md` — F6 success criteria verificados
  - `AGENTS.md` — Fase actualizada
  - Verify: revisión de archivos actualizados

### Checkpoint: F6 Complete [ ]
- [ ] Todos los criterios de SPEC-60/61/62/63 cumplidos
- [ ] `make build` pasa
- [ ] Coverage targets cumplidos para todas las capas
- [ ] 80+ nuevos tests pasan
- [ ] Sin regresiones en tests F0-F5 existentes (291)
- [ ] `mypy src/ --strict` pasa
- [ ] SLA p95 < 100ms validado
- [ ] Security regression suite pasando
- [ ] Documentación actualizada y precisa
- [ ] Listo para revisión humana → F7

---

## Summary

| Phase | Tasks | Completed | New Tests |
|-------|-------|-----------|-----------|
| Phase 1: Foundation | 1 | 0/1 | 0 |
| Phase 2: SPEC-60 Unit+Hypothesis+mypy | 4 | 0/4 | 17+ |
| Phase 3: SPEC-61 Integration Edges | 5 | 0/5 | 46+ |
| Phase 4: SPEC-62 E2E+Latency | 4 | 0/4 | 10+ |
| Phase 5: SPEC-63 Security | 4 | 0/4 | 61+ |
| Phase 6: Validation+Docs | 2 | 0/2 | 0 |
| **Total** | **20** | **0/20** | **134+** |

---

## Implementation Order Reference

```
Task 1 (deps + config)
↓
Task 2 (strategies) ←── also Task 5 (mypy) can start here
↓
Tasks 3, 4 (parallel: domain PBT + use case edges)
↓
Task 6 (integration helpers)
↓
Tasks 7, 8, 9, 10 (parallel: repo + MV + UoW + API edges)
↓
Task 11 (E2E conftest)
↓
Tasks 12, 13, 14 (parallel: latency + flows + contracts)
↓
Task 15 (security conftest)
↓
Tasks 16, 17, 18 (parallel: SQLi + input + leakage)
↓
Task 19 (full build validation)
↓
Task 20 (documentation)
```
