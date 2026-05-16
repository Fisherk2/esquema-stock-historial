# Implementation Plan: F2 — Núcleo de Dominio

## Overview

F2 establishes the domain core of the stock-historial system:
- Domain entities (`Movement`, `Product`, `Category`) as `@dataclass` natives
- Value objects (`MovementType`, `SKU`, `Quantity`) with frozen dataclasses + validation
- Domain exceptions hierarchy (`DomainError` → 4 concrete exceptions)
- Business rules as pure functions (stock validation, delta calculation, immutability, consistency)
- Repository ports as `typing.Protocol` + `@runtime_checkable` (IMovementRepository, IProductRepository, ICategoryRepository, IStockQueryRepository)
- Unit tests with parametrized cases for all domain components

This phase produces zero infrastructure code — pure domain logic that F3+ implements against.

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| `@dataclass` natives (no Pydantic) | Domain must be framework-agnostic; Pydantic reserved for DTOs in application layer |
| `Movement` as `frozen=True` dataclass | Language-level immutability enforcement; no update/delete methods on repository |
| `typing.Protocol` + `@runtime_checkable` | DIP without inheritance coupling; structs can satisfy Protocol implicitly; runtime checking for mock validation in tests |
| MovementType as `Enum` (not StrEnum) | Explicit, closed set of 4 values mapping 1:1 to PostgreSQL ENUM |
| FK references as `int` (not navigation) | Product holds `category_id: int`, not `Category` object; avoids lazy-loading issues and keeps entities serializable |
| TRANSFER as single Movement with metadata | One atomic record with `origin`/`destination` in metadata; simpler than paired OUT+IN |
| ADJUSTMENT always +qty | No negative adjustments; corrections use separate OUT movements (confirmed by user) |
| Rules as pure functions | No class, no state, no I/O; `validate_stock_not_negative(movement_type, quantity, current_stock)` receives current_stock as explicit parameter |
| SKU pattern: `[A-Za-z0-9\-_]{1,50}` | Permissive enough for common SKU formats; can extend to dots in future if needed |
| `product_id=0` placeholder in InsufficientStockError | Rule function doesn't know product_id; use case constructs exception with real product_id |

## Dependency Graph

```
DomainError ─────────────────────────────────────────────┐
  ├── InsufficientStockError                              │
  ├── ImmutabilityViolationError                          │
  ├── InvalidSKUError                                     │
  └── InvalidQuantityError                                │
       │                                                  │
MovementType ─────────────────────────────────────────────┤
  │                                                       │
  ├── Quantity (frozen VO) ──► InvalidQuantityError ──────┤
  │       │                                               │
  │       └──► Movement (frozen entity) ──► ImmutabilityViolationError
  │               │                                       │
  │               ├──► enforce_immutability (rule)        │
  │               ├──► validate_movement_type_consistency (rule)
  │               ├──► IMovementRepository (port)         │
  │               └──► IStockQueryRepository (port)       │
  │                                                       │
  ├── calculate_stock_delta (rule)                        │
  │                                                       │
  └── validate_stock_not_negative (rule) ──► InsufficientStockError
                                                          │
SKU (frozen VO) ──► InvalidSKUError ──────────────────────┤
  │                                                       │
  └──► Product (entity) ──► IProductRepository (port)     │
                                                          │
Category (entity) ──► ICategoryRepository (port) ◄────────┘
```

## Vertical Slicing Strategy

Instead of building all entities → all VOs → all rules → all ports (horizontal),
we build complete vertical paths:

```
Slice 1 (Movement path):  MovementType → Quantity → DomainError → Exceptions → Movement → Rules → Ports
Slice 2 (Product path):   SKU → InvalidSKUError → Product → IProductRepository
Slice 3 (Category path):  Category → ICategoryRepository
```

Each slice delivers a **working, testable** vertical path from VO to port.

## Task List

### Phase 1: Foundation (Value Objects + Base Exceptions)

#### Task 1: Create DomainError base exception
- **Description:** Create the base `DomainError` class that all domain exceptions inherit from. This is the root of the exception hierarchy and the first file needed by all other domain modules.
- **Acceptance criteria:**
  - [ ] `src/domain/exceptions/domain_error.py` exists with `DomainError(Exception)`
  - [ ] `src/domain/exceptions/__init__.py` re-exports `DomainError`
  - [ ] `DomainError` has Google-style docstring
  - [ ] `make lint` passes
- **Verification:** `pytest tests/unit/domain/ -v` (when tests exist); `make lint`
- **Dependencies:** None
- **Files:** `src/domain/exceptions/domain_error.py`, `src/domain/exceptions/__init__.py`
- **Scope:** XS (2 files)

#### Task 2: Create MovementType enum
- **Description:** Create the `MovementType` enum with 4 values (IN, OUT, ADJUSTMENT, TRANSFER) mapping 1:1 to the PostgreSQL ENUM. This is the first value object and is required by Movement, rules, and ports.
- **Acceptance criteria:**
  - [ ] `src/domain/value_objects/movement_type.py` exists
  - [ ] `MovementType.IN.value == "IN"` (and same for OUT, ADJUSTMENT, TRANSFER)
  - [ ] `src/domain/value_objects/__init__.py` re-exports `MovementType`
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.domain.value_objects.movement_type import MovementType; assert MovementType.IN.value == 'IN'"`
- **Dependencies:** None
- **Files:** `src/domain/value_objects/movement_type.py`, `src/domain/value_objects/__init__.py`
- **Scope:** XS (2 files)

#### Task 3: Create Quantity value object + InvalidQuantityError
- **Description:** Create the `Quantity` frozen dataclass with `__post_init__` validation (value > 0) and the `InvalidQuantityError` exception. This completes the first vertical micro-path: VO → Exception.
- **Acceptance criteria:**
  - [ ] `src/domain/value_objects/quantity.py` exists with `@dataclass(frozen=True)`
  - [ ] `Quantity(0)` raises `InvalidQuantityError`
  - [ ] `Quantity(-1)` raises `InvalidQuantityError`
  - [ ] `Quantity(10)` works and `.value == 10`
  - [ ] `src/domain/exceptions/invalid_quantity.py` exists and inherits from `DomainError`
  - [ ] Both `__init__.py` files updated with re-exports
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.domain.value_objects.quantity import Quantity; Quantity(0)"` → raises InvalidQuantityError
- **Dependencies:** Task 1 (DomainError), Task 2 (MovementType not needed but same wave)
- **Files:** `src/domain/value_objects/quantity.py`, `src/domain/exceptions/invalid_quantity.py`, 2× `__init__.py`
- **Scope:** S (4 files)

### Checkpoint: Foundation
- [ ] DomainError + 2 exceptions exist and inherit correctly
- [ ] MovementType enum has 4 values
- [ ] Quantity validates > 0 and raises InvalidQuantityError
- [ ] `make lint` passes with zero errors
- [ ] No Pydantic imports in `domain/`

---

### Phase 2: Movement Vertical Path

#### Task 4: Create InsufficientStockError + ImmutabilityViolationError
- **Description:** Create the two remaining domain exceptions needed by Movement rules. `InsufficientStockError` carries product_id, requested, available. `ImmutabilityViolationError` carries entity_type, entity_id.
- **Acceptance criteria:**
  - [ ] `src/domain/exceptions/insufficient_stock.py` exists with `product_id`, `requested`, `available` attributes
  - [ ] `src/domain/exceptions/immutability_violation.py` exists with `entity_type`, `entity_id` attributes
  - [ ] Both inherit from `DomainError`
  - [ ] `src/domain/exceptions/__init__.py` re-exports all 4 exceptions
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.domain.exceptions import InsufficientStockError; e = InsufficientStockError(1, 10, 5); assert e.product_id == 1"`
- **Dependencies:** Task 1 (DomainError)
- **Files:** `src/domain/exceptions/insufficient_stock.py`, `src/domain/exceptions/immutability_violation.py`, `src/domain/exceptions/__init__.py`
- **Scope:** S (3 files)

#### Task 5: Create Movement entity
- **Description:** Create the `Movement` frozen dataclass — the core immutable entity of the system. Includes `_validate_metadata_consistency()` for TRANSFER (origin+destination) and ADJUSTMENT (reason) validation in `__post_init__`.
- **Acceptance criteria:**
  - [ ] `src/domain/entities/movement.py` exists with `@dataclass(frozen=True)`
  - [ ] Movement has fields: id, product_id, movement_type, quantity, metadata, created_at, reference
  - [ ] `Movement(..., movement_type=MovementType.TRANSFER, metadata={})` raises ValueError
  - [ ] `Movement(..., movement_type=MovementType.ADJUSTMENT, metadata={})` raises ValueError
  - [ ] `__hash__ = None` — disables hashing (Movement identified by id, not value; metadata dict is unhashable)
  - [ ] Frozen: attempting to set `movement.quantity = Quantity(5)` raises `FrozenInstanceError`
  - [ ] `src/domain/entities/__init__.py` re-exports `Movement`
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.domain.entities.movement import Movement; from src.domain.value_objects.movement_type import MovementType; from src.domain.value_objects.quantity import Quantity; from datetime import datetime, timezone; m = Movement(id=None, product_id=1, movement_type=MovementType.IN, quantity=Quantity(10), metadata={}, created_at=datetime.now(tz=timezone.utc)); print(m)"`
- **Dependencies:** Task 2 (MovementType), Task 3 (Quantity), Task 4 (exceptions not directly but same path)
- **Files:** `src/domain/entities/movement.py`, `src/domain/entities/__init__.py`
- **Scope:** S (2 files)

#### Task 6: Create Movement business rules
- **Description:** Create the three rule functions related to Movement: `calculate_stock_delta`, `validate_stock_not_negative`, and `enforce_immutability`. Also create `validate_movement_type_consistency` (extracted from Movement.__post_init__ logic for reuse at the use-case level).
- **Acceptance criteria:**
  - [ ] `src/domain/rules/stock_validation.py` exists with `calculate_stock_delta` and `validate_stock_not_negative`
  - [ ] `calculate_stock_delta(MovementType.IN, 10) == 10`
  - [ ] `calculate_stock_delta(MovementType.OUT, 10) == -10`
  - [ ] `calculate_stock_delta(MovementType.ADJUSTMENT, 10) == 10`
  - [ ] `calculate_stock_delta(MovementType.TRANSFER, 10) == -10`
  - [ ] `validate_stock_not_negative(MovementType.OUT, 10, 5)` raises InsufficientStockError
  - [ ] `validate_stock_not_negative(MovementType.IN, 10, 5)` does not raise
  - [ ] `src/domain/rules/immutability.py` exists with `enforce_immutability`
  - [ ] `src/domain/rules/movement_consistency.py` exists with `validate_movement_type_consistency`
  - [ ] `src/domain/rules/__init__.py` re-exports all 4 functions
  - [ ] `make lint` passes
- **Verification:** `pytest tests/unit/domain/test_rules.py -v` (when tests exist); `make lint`
- **Dependencies:** Task 2 (MovementType), Task 4 (InsufficientStockError, ImmutabilityViolationError), Task 5 (Movement entity)
- **Files:** `src/domain/rules/stock_validation.py`, `src/domain/rules/immutability.py`, `src/domain/rules/movement_consistency.py`, `src/domain/rules/__init__.py`
- **Scope:** M (4 files)

#### Task 7: Create IMovementRepository + IStockQueryRepository ports
- **Description:** Create the two ports related to Movement: `IMovementRepository` (create, get_by_id, list_by_product — no update/delete) and `IStockQueryRepository` (get_current_stock, get_stock_at_date — ISP separation from movement CRUD).
- **Acceptance criteria:**
  - [ ] `src/domain/ports/movement_repository.py` exists with `@runtime_checkable` Protocol
  - [ ] `IMovementRepository` has `async def create`, `async def get_by_id`, `async def list_by_product`
  - [ ] `IMovementRepository` has NO `update` or `delete` methods
  - [ ] `src/domain/ports/stock_query_repository.py` exists with `@runtime_checkable` Protocol
  - [ ] `IStockQueryRepository` has `async def get_current_stock`, `async def get_stock_at_date`
  - [ ] `src/domain/ports/__init__.py` re-exports both protocols
  - [ ] `isinstance(mock_obj, IMovementRepository)` works with a mock implementation (runtime_checkable)
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.domain.ports import IMovementRepository, IStockQueryRepository; print('OK')"`
- **Dependencies:** Task 5 (Movement entity used in IMovementRepository signatures)
- **Files:** `src/domain/ports/movement_repository.py`, `src/domain/ports/stock_query_repository.py`, `src/domain/ports/__init__.py`
- **Scope:** S (3 files)

#### Task 8: Unit tests for Movement path
- **Description:** Create comprehensive unit tests for the entire Movement vertical path: MovementType, Quantity, InvalidQuantityError, Movement entity, all 4 rules, IMovementRepository and IStockQueryRepository mock satisfaction.
- **Acceptance criteria:**
  - [ ] `tests/unit/domain/test_movement_type.py` — MovementType enum values
  - [ ] `tests/unit/domain/test_quantity.py` — Quantity validation (valid, zero, negative, frozen)
  - [ ] `tests/unit/domain/test_movement.py` — Movement construction, frozen enforcement, metadata consistency
  - [ ] `tests/unit/domain/test_rules.py` — Parametrized tests for all 4 rule functions
  - [ ] `tests/unit/domain/test_ports.py` — Mock classes satisfy Protocol at runtime
  - [ ] All tests pass with `pytest tests/unit/domain/ -v`
  - [ ] Coverage for domain/ > 85%
- **Verification:** `pytest tests/unit/domain/ -v --cov=src/domain --cov-report=term-missing`
- **Dependencies:** Tasks 2, 3, 4, 5, 6, 7
- **Files:** `tests/unit/domain/test_movement_type.py`, `tests/unit/domain/test_quantity.py`, `tests/unit/domain/test_movement.py`, `tests/unit/domain/test_rules.py`, `tests/unit/domain/test_ports.py`
- **Scope:** M (5 files)

### Checkpoint: Movement Path Complete
- [ ] Movement entity is frozen and validates metadata consistency
- [ ] All 4 rules are pure functions with correct behavior
- [ ] IMovementRepository has no update/delete
- [ ] IStockQueryRepository is separate from IMovementRepository (ISP)
- [ ] All Movement-path unit tests pass
- [ ] `make lint` passes
- [ ] Coverage domain/ > 85%

---

### Phase 3: Product Vertical Path

#### Task 9: Create SKU value object + InvalidSKUError
- **Description:** Create the `SKU` frozen dataclass with regex validation (non-empty, max 50 chars, `[A-Za-z0-9\-_]+`) and the `InvalidSKUError` exception.
- **Acceptance criteria:**
  - [ ] `src/domain/value_objects/sku.py` exists with `@dataclass(frozen=True)`
  - [ ] `SKU("PROD-001")` works (valid format)
  - [ ] `SKU("")` raises `InvalidSKUError`
  - [ ] `SKU("a"*51)` raises `InvalidSKUError` (exceeds 50 chars)
  - [ ] `SKU("invalid sku!")` raises `InvalidSKUError` (invalid chars)
  - [ ] `src/domain/exceptions/invalid_sku.py` exists and inherits from `DomainError`
  - [ ] Both `__init__.py` files updated with re-exports
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.domain.value_objects.sku import SKU; SKU('PROD-001')"`
- **Dependencies:** Task 1 (DomainError)
- **Files:** `src/domain/value_objects/sku.py`, `src/domain/exceptions/invalid_sku.py`, 2× `__init__.py` updates
- **Scope:** S (4 files)

#### Task 10: Create Product entity
- **Description:** Create the `Product` dataclass with SKU value object, name validation, min_stock_threshold >= 0 validation, and unit_of_measure validation.
- **Acceptance criteria:**
  - [ ] `src/domain/entities/product.py` exists with `@dataclass`
  - [ ] Product has fields: id, sku, name, description, unit_of_measure, category_id, min_stock_threshold, created_at
  - [ ] `Product(name="", ...)` raises ValueError
  - [ ] `Product(min_stock_threshold=-1, ...)` raises ValueError
  - [ ] `Product(unit_of_measure="", ...)` raises ValueError
  - [ ] `src/domain/entities/__init__.py` updated with Product re-export
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.domain.entities.product import Product; from src.domain.value_objects.sku import SKU; from datetime import datetime, timezone; p = Product(id=None, sku=SKU('PROD-001'), name='Test', description=None, unit_of_measure='unit', category_id=1, min_stock_threshold=0, created_at=datetime.now(tz=timezone.utc)); print(p)"`
- **Dependencies:** Task 9 (SKU)
- **Files:** `src/domain/entities/product.py`, `src/domain/entities/__init__.py`
- **Scope:** S (2 files)

#### Task 11: Create IProductRepository port
- **Description:** Create the `IProductRepository` protocol with create, get_by_id, get_by_sku, list_all (paginated), and list_below_threshold methods.
- **Acceptance criteria:**
  - [ ] `src/domain/ports/product_repository.py` exists with `@runtime_checkable` Protocol
  - [ ] `IProductRepository` has 5 async methods: create, get_by_id, get_by_sku, list_all, list_below_threshold
  - [ ] `get_by_sku(self, sku: str)` accepts string (not SKU VO) for infrastructure simplicity
  - [ ] `list_all` has keyword-only `limit` and `offset` params
  - [ ] `src/domain/ports/__init__.py` updated with IProductRepository re-export
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.domain.ports import IProductRepository; print('OK')"`
- **Dependencies:** Task 10 (Product entity)
- **Files:** `src/domain/ports/product_repository.py`, `src/domain/ports/__init__.py`
- **Scope:** S (2 files)

#### Task 12: Unit tests for Product path
- **Description:** Create unit tests for SKU validation, Product construction, and IProductRepository mock satisfaction.
- **Acceptance criteria:**
  - [ ] `tests/unit/domain/test_sku.py` — SKU validation (valid, empty, too long, invalid chars, frozen)
  - [ ] `tests/unit/domain/test_product.py` — Product construction, name/threshold/unit validation
  - [ ] `tests/unit/domain/test_product_port.py` — Mock class satisfies IProductRepository at runtime
  - [ ] All tests pass with `pytest tests/unit/domain/ -v`
- **Verification:** `pytest tests/unit/domain/test_sku.py tests/unit/domain/test_product.py tests/unit/domain/test_product_port.py -v`
- **Dependencies:** Tasks 9, 10, 11
- **Files:** `tests/unit/domain/test_sku.py`, `tests/unit/domain/test_product.py`, `tests/unit/domain/test_product_port.py`
- **Scope:** M (3 files)

### Checkpoint: Product Path Complete
- [ ] SKU validates format and raises InvalidSKUError
- [ ] Product validates name, threshold, unit_of_measure
- [ ] IProductRepository has 5 methods including list_below_threshold
- [ ] Product-path unit tests pass
- [ ] `make lint` passes

---

### Phase 4: Category Vertical Path

#### Task 13: Create Category entity
- **Description:** Create the `Category` dataclass with name validation (non-empty). Category is the simplest entity — no value objects, no complex invariants.
- **Acceptance criteria:**
  - [ ] `src/domain/entities/category.py` exists with `@dataclass`
  - [ ] Category has fields: id, name, description, created_at
  - [ ] `Category(name="", ...)` raises ValueError
  - [ ] `src/domain/entities/__init__.py` updated with Category re-export
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.domain.entities.category import Category; from datetime import datetime, timezone; c = Category(id=None, name='Electronics', description=None, created_at=datetime.now(tz=timezone.utc)); print(c)"`
- **Dependencies:** None (standalone entity)
- **Files:** `src/domain/entities/category.py`, `src/domain/entities/__init__.py`
- **Scope:** XS (2 files)

#### Task 14: Create ICategoryRepository port
- **Description:** Create the `ICategoryRepository` protocol with create, get_by_id, and list_all methods.
- **Acceptance criteria:**
  - [ ] `src/domain/ports/category_repository.py` exists with `@runtime_checkable` Protocol
  - [ ] `ICategoryRepository` has 3 async methods: create, get_by_id, list_all
  - [ ] `list_all` returns `list[Category]` (no pagination — small dataset expected)
  - [ ] `src/domain/ports/__init__.py` updated with ICategoryRepository re-export
  - [ ] `make lint` passes
- **Verification:** `python -c "from src.domain.ports import ICategoryRepository; print('OK')"`
- **Dependencies:** Task 13 (Category entity)
- **Files:** `src/domain/ports/category_repository.py`, `src/domain/ports/__init__.py`
- **Scope:** XS (2 files)

#### Task 15: Unit tests for Category path
- **Description:** Create unit tests for Category construction and ICategoryRepository mock satisfaction.
- **Acceptance criteria:**
  - [ ] `tests/unit/domain/test_category.py` — Category construction, name validation
  - [ ] `tests/unit/domain/test_category_port.py` — Mock class satisfies ICategoryRepository at runtime
  - [ ] All tests pass
- **Verification:** `pytest tests/unit/domain/test_category.py tests/unit/domain/test_category_port.py -v`
- **Dependencies:** Tasks 13, 14
- **Files:** `tests/unit/domain/test_category.py`, `tests/unit/domain/test_category_port.py`
- **Scope:** S (2 files)

### Checkpoint: Category Path Complete
- [ ] Category validates non-empty name
- [ ] ICategoryRepository has 3 methods, no pagination
- [ ] Category-path unit tests pass
- [ ] `make lint` passes

---

### Phase 5: Domain Integration + Documentation

#### Task 16: Update domain/__init__.py with full re-exports
- **Description:** Update the top-level `src/domain/__init__.py` to re-export the public API of the entire domain layer, providing a clean import surface for application and infrastructure layers.
- **Acceptance criteria:**
  - [ ] `src/domain/__init__.py` re-exports all entities, value objects, exceptions, rules, and ports
  - [ ] `python -c "from src.domain import Movement, Product, Category, MovementType, SKU, Quantity"` works
  - [ ] `python -c "from src.domain import DomainError, InsufficientStockError"` works
  - [ ] `make lint` passes
- **Verification:** Import smoke test above
- **Dependencies:** Tasks 5, 10, 13 (all entities), Tasks 6, 7, 11, 14 (all rules/ports)
- **Files:** `src/domain/__init__.py`
- **Scope:** XS (1 file)

#### Task 17: Update spec-tracking.md + SPEC.md
- **Description:** Update the spec tracking table with F2 spec progress and add F2 section to SPEC.md.
- **Acceptance criteria:**
  - [ ] Spec-20: checklist [10/10], status "Completado"
  - [ ] Spec-21: checklist [8/8], status "Completado"
  - [ ] Spec-22: checklist [9/9], status "Completado"
  - [ ] SPEC.md includes F2 section with summary and references to SPEC-20/21/22
  - [ ] WORKFLOW.md "Estado Actual" updated to reflect F2 progress
- **Verification:** Review updated files
- **Dependencies:** All implementation tasks
- **Files:** `docs/workflow/spec-tracking.md`, `SPEC.md`, `WORKFLOW.md`
- **Scope:** XS (3 files, documentation only)

#### Task 18: Run make build (final validation)
- **Description:** Execute full build pipeline to validate that all domain code passes lint, formatting, and tests.
- **Acceptance criteria:**
  - [ ] `make lint` passes with 0 errors
  - [ ] `make format` passes (no changes needed)
  - [ ] `make test` passes (all unit tests green)
  - [ ] Coverage for `src/domain/` > 85%
  - [ ] No Pydantic imports in `domain/`
  - [ ] No imports from `application/`, `infrastructure/`, `adapters/` in `domain/`
- **Verification:** `make build` exit code 0
- **Dependencies:** All tasks
- **Scope:** XS (validation only)

### Checkpoint: F2 Complete
- [ ] All acceptance criteria from SPEC-20, SPEC-21, SPEC-22 met
- [ ] `make build` passes
- [ ] Domain layer is fully self-contained (no external imports)
- [ ] Ready for human review before proceeding to F3

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `frozen=True` on Movement prevents `id` assignment after persistence | Medium | Return new Movement with id via `dataclasses.replace(movement, id=generated_id)` — this is the standard pattern for frozen dataclasses |
| SKU regex too restrictive for real-world SKUs | Low | Pattern `[A-Za-z0-9\-_]{1,50}` covers most cases; dots can be added in a future spec update |
| `product_id=0` placeholder in InsufficientStockError from rule function | Low | Document that use case constructs the real exception; rule validates logic, use case provides context |
| `typing.Protocol` + `@runtime_checkable` only checks method signatures, not return types | Low | Unit tests with mock implementations validate behavioral compliance |
| Movement metadata validation duplicated (entity + rule) | Low | Entity validates on construction; rule validates at use-case level before construction. Both exist for defense-in-depth |
| Frozen dataclass `__hash__` + unhashable `dict` metadata | ~~High~~ **Resolved** | **Decision: `__hash__ = None`** on Movement. Entity identified by `id`, not value. No use case for Movement in sets/dict keys. Keeps `metadata: dict[str, Any]` for natural JSONB mapping. `__eq__` still works (frozen default compares all fields). |

## Open Questions

1. ~~**Movement `__hash__` issue:**~~ **RESOLVED** — Option (a): `__hash__ = None`. Movement identified by `id`, not by value. Zero friction with dict metadata. No domain use case requires Movement to be hashable.

2. **`validate_stock_not_negative` product_id:** Should the function accept `product_id` as parameter instead of using `0` placeholder? Cleaner API but breaks the "pure function, no entity knowledge" principle.

3. **`validate_movement_type_consistency` ValueError vs domain exception:** Spec uses `ValueError` but SPEC-21 says "Domain exceptions only." Resolve inconsistency.

## Parallelization Opportunities

**Safe to parallelize (no shared files):**
- Task 1 (DomainError) + Task 2 (MovementType) — both are leaf nodes
- Task 3 (Quantity) + Task 9 (SKU) — different VOs, different exceptions
- Task 13 (Category entity) + Task 4 (exceptions) — no overlap

**Must be sequential:**
- Task 5 (Movement) requires Tasks 2, 3 (VOs)
- Task 6 (Rules) requires Tasks 2, 4, 5 (VOs + exceptions + entity)
- Task 7 (Ports) requires Task 5 (Movement entity)
- Task 8 (Tests) requires Tasks 2-7 (all Movement path code)
