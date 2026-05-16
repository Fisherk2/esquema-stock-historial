# TODO — F2: Núcleo de Dominio

## Progress: [0/18] ░░░░░░░░░░░░░░░░░░ EN PROGRESO

## Phase 1: Foundation (Value Objects + Base Exceptions) [0/3]

- [ ] **Task 1:** Create DomainError base exception
  - `src/domain/exceptions/domain_error.py`
  - `src/domain/exceptions/__init__.py`
  - Verify: `python -c "from src.domain.exceptions import DomainError"`

- [ ] **Task 2:** Create MovementType enum
  - `src/domain/value_objects/movement_type.py`
  - `src/domain/value_objects/__init__.py`
  - Verify: `python -c "from src.domain.value_objects import MovementType; assert MovementType.IN.value == 'IN'"`

- [ ] **Task 3:** Create Quantity VO + InvalidQuantityError
  - `src/domain/value_objects/quantity.py`
  - `src/domain/exceptions/invalid_quantity.py`
  - Verify: `Quantity(0)` → raises InvalidQuantityError

### Checkpoint: Foundation [ ]
- [ ] DomainError + 2 exceptions exist
- [ ] MovementType has 4 values
- [ ] Quantity validates > 0
- [ ] `make lint` passes

---

## Phase 2: Movement Vertical Path [0/5]

- [ ] **Task 4:** Create InsufficientStockError + ImmutabilityViolationError
  - `src/domain/exceptions/insufficient_stock.py`
  - `src/domain/exceptions/immutability_violation.py`
  - Verify: `InsufficientStockError(1, 10, 5).product_id == 1`

- [ ] **Task 5:** Create Movement entity (frozen dataclass)
  - `src/domain/entities/movement.py`
  - Verify: Movement with TRANSFER+empty metadata → ValueError

- [ ] **Task 6:** Create Movement business rules
  - `src/domain/rules/stock_validation.py` (calculate_stock_delta, validate_stock_not_negative)
  - `src/domain/rules/immutability.py` (enforce_immutability)
  - `src/domain/rules/movement_consistency.py` (validate_movement_type_consistency)
  - Verify: `calculate_stock_delta(MovementType.IN, 10) == 10`

- [ ] **Task 7:** Create IMovementRepository + IStockQueryRepository ports
  - `src/domain/ports/movement_repository.py`
  - `src/domain/ports/stock_query_repository.py`
  - Verify: No update/delete on IMovementRepository; ISP separation

- [ ] **Task 8:** Unit tests for Movement path
  - `tests/unit/domain/test_movement_type.py`
  - `tests/unit/domain/test_quantity.py`
  - `tests/unit/domain/test_movement.py`
  - `tests/unit/domain/test_rules.py`
  - `tests/unit/domain/test_ports.py`
  - Verify: `pytest tests/unit/domain/ -v --cov=src/domain`

### Checkpoint: Movement Path Complete [ ]
- [ ] Movement is frozen and validates metadata
- [ ] All 4 rules are pure functions
- [ ] IMovementRepository has no update/delete
- [ ] IStockQueryRepository is separate (ISP)
- [ ] Movement-path tests pass, coverage > 85%

---

## Phase 3: Product Vertical Path [0/4]

- [ ] **Task 9:** Create SKU VO + InvalidSKUError
  - `src/domain/value_objects/sku.py`
  - `src/domain/exceptions/invalid_sku.py`
  - Verify: `SKU("PROD-001")` works; `SKU("")` raises InvalidSKUError

- [ ] **Task 10:** Create Product entity
  - `src/domain/entities/product.py`
  - Verify: Product with empty name → ValueError

- [ ] **Task 11:** Create IProductRepository port
  - `src/domain/ports/product_repository.py`
  - Verify: 5 methods including list_below_threshold

- [ ] **Task 12:** Unit tests for Product path
  - `tests/unit/domain/test_sku.py`
  - `tests/unit/domain/test_product.py`
  - `tests/unit/domain/test_product_port.py`
  - Verify: `pytest tests/unit/domain/test_sku.py tests/unit/domain/test_product.py -v`

### Checkpoint: Product Path Complete [ ]
- [ ] SKU validates format
- [ ] Product validates name, threshold, unit
- [ ] IProductRepository has list_below_threshold
- [ ] Product-path tests pass

---

## Phase 4: Category Vertical Path [0/3]

- [ ] **Task 13:** Create Category entity
  - `src/domain/entities/category.py`
  - Verify: Category with empty name → ValueError

- [ ] **Task 14:** Create ICategoryRepository port
  - `src/domain/ports/category_repository.py`
  - Verify: 3 methods, no pagination

- [ ] **Task 15:** Unit tests for Category path
  - `tests/unit/domain/test_category.py`
  - `tests/unit/domain/test_category_port.py`
  - Verify: `pytest tests/unit/domain/test_category.py -v`

### Checkpoint: Category Path Complete [ ]
- [ ] Category validates non-empty name
- [ ] ICategoryRepository has 3 methods
- [ ] Category-path tests pass

---

## Phase 5: Domain Integration + Documentation [0/3]

- [ ] **Task 16:** Update domain/__init__.py with full re-exports
  - `src/domain/__init__.py`
  - Verify: `python -c "from src.domain import Movement, Product, Category"`

- [ ] **Task 17:** Update spec-tracking.md + SPEC.md + WORKFLOW.md
  - `docs/workflow/spec-tracking.md`
  - `SPEC.md`
  - `WORKFLOW.md`
  - Verify: Review updated files

- [ ] **Task 18:** Run make build (final validation)
  - Verify: `make build` exit code 0

### Checkpoint: F2 Complete [ ]
- [ ] All SPEC-20/21/22 acceptance criteria met
- [ ] `make build` passes
- [ ] Domain is self-contained (no external imports)
- [ ] Ready for human review → F3

---

## Summary

| Phase | Tasks | Completed |
|-------|-------|-----------|
| Phase 1: Foundation | 3 | 0/3 |
| Phase 2: Movement Path | 5 | 0/5 |
| Phase 3: Product Path | 4 | 0/4 |
| Phase 4: Category Path | 3 | 0/3 |
| Phase 5: Integration + Docs | 3 | 0/3 |
| **Total** | **18** | **0/18** |

---

## Resolved Design Decision

**Movement `__hash__` + `dict` metadata:** ~~frozen dataclass auto-generates `__hash__`, but `dict` is unhashable~~ **RESOLVED:** `__hash__ = None` on Movement. Entity identified by `id`, not value. No use case for hashing. Keeps `metadata: dict[str, Any]` for natural JSONB mapping.

---
