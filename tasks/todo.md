# TODO — F4: Capa API (Casos de Uso + Endpoints)

## Progress: [0/10] ░░░░░░░░░░ PENDIENTE

> **Nota:** La implementación preliminar de F4 ya existe (use cases, DTOs, routers, error mapping, DI factories, 147 unit tests). Este TODO cubre los gaps restantes para completar la fase.

## Phase 1: Foundation [0/2]

- [ ] **Task 1:** Crear fixture de cliente HTTP para integración
  - `tests/integration/api/conftest.py`
  - Fixture `api_client`: `httpx.AsyncClient` con `ASGITransport`, pool override
  - Usa fixture existente `db_pool` de `tests/integration/conftest.py`
  - Verify: `python -c "from tests.integration.api.conftest import *; print('OK')"`

- [ ] **Task 2:** Agregar test de integración `count_by_product()`
  - `tests/integration/repositories/test_movement_repository.py` (append)
  - `test_count_by_product_returns_correct_count` — 3 movimientos → count = 3
  - `test_count_by_product_returns_zero_for_no_movements` — sin movimientos → 0
  - Verify: `pytest tests/integration/repositories/test_movement_repository.py -v -k count`

### Checkpoint: Foundation Ready [ ]
- [ ] API client fixture funciona con DB real
- [ ] Tests de `count_by_product()` pasan
- [ ] `make lint` pasa
- [ ] Listo para escribir endpoint tests

---

## Phase 2: Endpoint Integration Tests [0/4]

- [ ] **Task 3:** Tests de categorías
  - `tests/integration/api/test_categories_api.py`
  - `test_create_category_returns_201` — POST crea con id y created_at
  - `test_create_category_empty_name_returns_422` — POST con nombre vacío
  - `test_list_categories_returns_200` — GET retorna seed data
  - `test_list_categories_after_create` — POST + GET muestra nueva
  - Verify: `pytest tests/integration/api/test_categories_api.py -v`

- [ ] **Task 4:** Tests de productos
  - `tests/integration/api/test_products_api.py`
  - `test_create_product_returns_201` — POST con datos válidos
  - `test_create_product_invalid_sku_returns_422` — POST con SKU inválido
  - `test_create_product_nonexistent_category_returns_400` — POST con category_id inexistente
  - `test_list_products_returns_200_with_pagination` — GET con total paginado
  - `test_get_product_by_id_returns_200` — GET/{id} retorna producto
  - `test_get_product_by_id_not_found_returns_404` — GET/99999 → 404
  - `test_list_products_pagination_works` — limit/offset funciona
  - Verify: `pytest tests/integration/api/test_products_api.py -v`

- [ ] **Task 5:** Tests de movimientos
  - `tests/integration/api/test_movements_api.py`
  - `test_create_in_movement_returns_201` — POST IN
  - `test_create_out_movement_with_stock_returns_201` — POST OUT con stock
  - `test_create_out_movement_insufficient_stock_returns_409` — POST OUT sin stock → 409
  - `test_create_transfer_requires_metadata_returns_400` — POST TRANSFER sin metadata
  - `test_create_adjustment_requires_reason_returns_400` — POST ADJUSTMENT sin reason
  - `test_create_movement_invalid_product_returns_400` — POST con producto inexistente
  - `test_get_movement_by_id_returns_200` — GET/{id} después de POST
  - `test_get_movement_not_found_returns_404` — GET/99999 → 404
  - `test_list_movements_by_product_returns_200` — GET?product_id= con paginación
  - `test_list_movements_pagination` — limit/offset correcto
  - Verify: `pytest tests/integration/api/test_movements_api.py -v`

- [ ] **Task 6:** Tests de stock
  - `tests/integration/api/test_stock_api.py`
  - `test_get_current_stock_returns_200` — GET current después de IN
  - `test_get_current_stock_reflects_out_movements` — GET current después de OUT
  - `test_get_current_stock_no_movements_returns_zero` — sin movimientos → 0.0
  - `test_get_stock_at_date_returns_200` — GET at-date con fecha válida
  - `test_get_stock_at_date_with_iso8601_format` — formato ISO 8601 funciona
  - Verify: `pytest tests/integration/api/test_stock_api.py -v`

### Checkpoint: Endpoint Tests Complete [ ]
- [ ] 4 archivos de tests de endpoints pasan
- [ ] Categories: 4+ tests
- [ ] Products: 7+ tests
- [ ] Movements: 10+ tests
- [ ] Stock: 5+ tests
- [ ] `make lint` pasa
- [ ] Listo para error mapping tests

---

## Phase 3: Error Mapping Tests [0/1]

- [ ] **Task 7:** Tests de mapeo de errores
  - `tests/integration/api/test_error_mapping_api.py`
  - `test_insufficient_stock_returns_409` — OUT sin stock → 409 con código `INSUFFICIENT_STOCK`
  - `test_insufficient_stock_includes_details` — 409 incluye product_id, requested, available
  - `test_invalid_sku_returns_422` — SKU inválido → 422 con código `INVALID_SKU`
  - `test_immutability_violation_returns_403` — handler registrado para 403
  - `test_validation_error_returns_400` — TRANSFER sin metadata → 400
  - `test_error_response_format` — formato `{"error": {"code": "...", "message": "..."}}` consistente
  - Verify: `pytest tests/integration/api/test_error_mapping_api.py -v`

### Checkpoint: Error Mapping Complete [ ]
- [ ] 6 exception handlers producen respuestas HTTP correctas
- [ ] Formato `ErrorResponse` consistente
- [ ] `make lint` pasa

---

## Phase 4: Validación Final [0/3]

- [ ] **Task 8:** Build completo con cobertura
  - `make lint` → 0 errores
  - `make test` → todos verdes (unit + integration)
  - Coverage `src/application/` > 85%
  - Coverage `src/adapters/` > 70%
  - OpenAPI `/docs` muestra 10 endpoints
  - Version 0.4.0 en `main.py`
  - Verify: `make build` exit code 0; `make test-cov` > 85% application

- [ ] **Task 9:** Actualizar documentación del proyecto
  - `WORKFLOW.md` — F4 status con conteo de tests de integración
  - `docs/workflow/spec-tracking.md` — Spec-40/41/42 verificados
  - `docs/workflow/roadmap-phases.md` — F4 "En Progreso" → "Completado"
  - `SPEC.md` — F4 success criteria verificados
  - Verify: revisión de archivos actualizados

- [ ] **Task 10:** Eliminar directorio vacío `application/interfaces/`
  - `src/application/interfaces/` (eliminar directorio completo)
  - Verificar: `grep -r "application.interfaces" src/ tests/` retorna nada
  - Verify: `make lint` pasa; `make test` pasa

### Checkpoint: F4 Complete [ ]
- [ ] Todos los criterios de Spec-40/41/42 cumplidos
- [ ] `make build` pasa
- [ ] Coverage `src/application/` > 85%
- [ ] Tests de integración para los 10 endpoints pasan
- [ ] Error mapping validado end-to-end
- [ ] Documentación actualizada y precisa
- [ ] Sin código muerto (`application/interfaces/` eliminado)
- [ ] Listo para revisión humana → F5

---

## Summary

| Phase | Tasks | Completed |
|-------|-------|-----------|
| Phase 1: Foundation | 2 | 0/2 |
| Phase 2: Endpoint Tests | 4 | 0/4 |
| Phase 3: Error Mapping | 1 | 0/1 |
| Phase 4: Final Validation | 3 | 0/3 |
| **Total** | **10** | **0/10** |

---

## Implementation Order Reference

```
Task 1 (API client fixture)
    ↓
Task 2 (count_by_product test — independent, can parallelize)
    ↓
Tasks 3, 4, 5, 6 (endpoint tests — can be parallelized)
    ↓
Task 7 (error mapping tests — after Task 5 for reference)
    ↓
Task 10 (cleanup — independent, can parallelize)
    ↓
Task 8 (build validation)
    ↓
Task 9 (docs update)
```

## Resolved Decisions (F4-Q1 through F4-Q10)

All 10 decisions from preliminary implementation are confirmed:
- `count_by_product()` implemented now (F4-Q1)
- `validate_stock_not_negative()` fixed with `product_id` (F4-Q2)
- F4 spec appended to SPEC.md (F4-Q3)
- Unit + Integration testing scope (F4-Q4)
- `ListProductsUseCase` returns total via `count_all()` (F4-Q5)
- GET by ID direct to repo (CQRS) (F4-Q6)
- Use cases as classes with DI (F4-Q7)
- UoW only for OUT/TRANSFER (F4-Q8)
- API snake_case (F4-Q9)
- Exception handlers (not middleware) (F4-Q10)
