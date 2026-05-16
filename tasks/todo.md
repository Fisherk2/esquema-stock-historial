# TODO — F1: Infraestructura DB

## Progress: [15/15] ████████████████████ ✅ COMPLETADO

F1 completada el 2026-05-15. Commits: `57e5ed7` (implementación), `1993eec` (bug fix + docstrings).

## Phase 1: Database Schema (Migrations) [5/5] ✅

- [x] **Task 1:** Create ENUM and categories table
  - `migrations/001_create_movement_type_enum.sql`
  - `migrations/002_create_categories.sql`
  - Verify: Run twice, no error

- [x] **Task 2:** Create products and movements tables
  - `migrations/003_create_products.sql`
  - `migrations/004_create_movements.sql`
  - Verify: `\d products`, `\d movements`

- [x] **Task 3:** Create immutability trigger
  - `migrations/005_create_immutability_trigger.sql`
  - Verify: UPDATE raises exception

- [x] **Task 4:** Create indexes
  - `migrations/006_create_indexes.sql`
  - Verify: pg_indexes shows 7+ indexes

- [x] **Task 5:** Create seed data
  - `migrations/007_seed_data.sql`
  - Verify: Counts ≈ 10 products, ≈ 30 movements

### Checkpoint: Schema Complete [x]

---

## Phase 2: Migration Runner + Seed Script [2/2] ✅

- [x] **Task 6:** Create migrate.py
  - `src/infrastructure/db/migrate.py`
  - Verify: Run twice, second run skips

- [x] **Task 7:** Create seed.py
  - `src/infrastructure/db/seed.py`
  - Verify: Seed inserts data

### Checkpoint: Migration Scripts Complete [x]

---

## Phase 3: FastAPI Integration [3/3] ✅

- [x] **Task 8:** Integrate pool into FastAPI lifespan
  - `src/main.py`
  - Verify: App starts with pool

- [x] **Task 9:** Add DB check to health endpoint
  - `src/adapters/api/routers/health.py`
  - Verify: Returns {status, db}

- [x] **Task 10:** Update connection.py docstrings
  - `src/infrastructure/db/connection.py`
  - Verify: No "placeholder" comments

### Checkpoint: FastAPI Integration Complete [x]

---

## Phase 4: Integration Tests [1/1] ✅

- [x] **Task 11:** Create test_db_schema.py
  - `tests/integration/test_db_schema.py`
  - Verify: All 17 tests pass (16 schema + 1 seed module)

### Checkpoint: Integration Tests Complete [x]

---

## Phase 5: Documentation + Build Updates [3/3] ✅

- [x] **Task 12:** Update Makefile
  - Add `migrate` and `seed` targets
  - Verify: `make help` lists them

- [x] **Task 13:** Update spec-tracking.md
  - Spec-10/11/12 status changes
  - Verify: Review file

- [x] **Task 14:** Update SPEC.md
  - Add F1 section
  - Verify: Review file

### Checkpoint: Documentation Complete [x]

---

## Phase 6: Final Validation [1/1] ✅

- [x] **Task 15:** Run make build
  - Verify: Exit code 0

### Checkpoint: F1 Complete [x]

---

## Summary

| Phase | Tasks | Completed |
|-------|-------|-----------|
| Phase 1: Database Schema | 5 | 5/5 |
| Phase 2: Migration Runner | 2 | 2/2 |
| Phase 3: FastAPI Integration | 3 | 3/3 |
| Phase 4: Integration Tests | 1 | 1/1 |
| Phase 5: Documentation | 3 | 3/3 |
| Phase 6: Final Validation | 1 | 1/1 |
| **Total** | **15** | **15/15** ✅ |

---

# TODO — F2: Núcleo de Dominio

## Progress: [0/0] ░░░░░░░░░░░░░░░░░

## Phase 1: Entidades (Domain) [0/5]

- [ ] **Task F2-1:** Crear entidad `Product` con value objects
- [ ] **Task F2-2:** Crear entidad `Movement` con reglas de inmutabilidad
- [ ] **Task F2-3:** Crear value objects (`Quantity`, `SKU`, `MovementType`)
- [ ] **Task F2-4:** Crear excepciones de dominio (`StockError`, `NegativeQuantityError`, etc.)
- [ ] **Task F2-5:** Tests unitarios de entidades

### Checkpoint: Entidades Complete [ ]

---

## Phase 2: Reglas de Negocio [0/4]

- [ ] **Task F2-6:** Regla de stock no negativo
- [ ] **Task F2-7:** Regla de inmutabilidad de movimientos
- [ ] **Task F2-8:** Regla de transaccionalidad (IN/OUT pares)
- [ ] **Task F2-9:** Tests unitarios de reglas

### Checkpoint: Reglas Complete [ ]

---

## Phase 3: Protocolos/Interfaces [0/3]

- [ ] **Task F2-10:** `IMovementRepository` port
- [ ] **Task F2-11:** `IStockQueryRepository` port
- [ ] **Task F2-12:** `IUseCase` protocol genérico

### Checkpoint: Protocolos Complete [ ]

---

## Summary

| Phase | Tasks | Completed |
|-------|-------|-----------|
| Phase 1: Entidades | 5 | 0/5 |
| Phase 2: Reglas de Negocio | 4 | 0/4 |
| Phase 3: Protocolos | 3 | 0/3 |
| **Total** | **12** | **0/12** |

## Next Step

**SPECIFY:** Crear SPEC-F2.md con contratos y criterios de aceptación antes de implementar.
