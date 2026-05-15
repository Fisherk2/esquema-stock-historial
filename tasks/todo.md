# TODO — F1: Infraestructura DB

## Progress: [0/15] ░░░░░░░░░░░░░░░░░

## Phase 1: Database Schema (Migrations) [0/5]

- [ ] **Task 1:** Create ENUM and categories table
  - `migrations/001_create_movement_type_enum.sql`
  - `migrations/002_create_categories.sql`
  - Verify: Run twice, no error

- [ ] **Task 2:** Create products and movements tables
  - `migrations/003_create_products.sql`
  - `migrations/004_create_movements.sql`
  - Verify: `\d products`, `\d movements`

- [ ] **Task 3:** Create immutability trigger
  - `migrations/005_create_immutability_trigger.sql`
  - Verify: UPDATE raises exception

- [ ] **Task 4:** Create indexes
  - `migrations/006_create_indexes.sql`
  - Verify: pg_indexes shows 7+ indexes

- [ ] **Task 5:** Create seed data
  - `migrations/007_seed_data.sql`
  - Verify: Counts ≈ 10 products, ≈ 30 movements

### Checkpoint: Schema Complete [ ]

---

## Phase 2: Migration Runner + Seed Script [0/2]

- [ ] **Task 6:** Create migrate.py
  - `src/infrastructure/db/migrate.py`
  - Verify: Run twice, second run skips

- [ ] **Task 7:** Create seed.py
  - `src/infrastructure/db/seed.py`
  - Verify: Seed inserts data

### Checkpoint: Migration Scripts Complete [ ]

---

## Phase 3: FastAPI Integration [0/3]

- [ ] **Task 8:** Integrate pool into FastAPI lifespan
  - `src/main.py`
  - Verify: App starts with pool

- [ ] **Task 9:** Add DB check to health endpoint
  - `src/adapters/api/routers/health.py`
  - Verify: Returns {status, db}

- [ ] **Task 10:** Update connection.py docstrings
  - `src/infrastructure/db/connection.py`
  - Verify: No "placeholder" comments

### Checkpoint: FastAPI Integration Complete [ ]

---

## Phase 4: Integration Tests [0/1]

- [ ] **Task 11:** Create test_db_schema.py
  - `tests/integration/test_db_schema.py`
  - Verify: All 15 tests pass

### Checkpoint: Integration Tests Complete [ ]

---

## Phase 5: Documentation + Build Updates [0/3]

- [ ] **Task 12:** Update Makefile
  - Add `migrate` and `seed` targets
  - Verify: `make help` lists them

- [ ] **Task 13:** Update spec-tracking.md
  - Spec-10/11/12 status changes
  - Verify: Review file

- [ ] **Task 14:** Update SPEC.md
  - Add F1 section
  - Verify: Review file

### Checkpoint: Documentation Complete [ ]

---

## Phase 6: Final Validation [0/1]

- [ ] **Task 15:** Run make build
  - Verify: Exit code 0

### Checkpoint: F1 Complete [ ]

---

## Summary

| Phase | Tasks | Completed |
|-------|-------|-----------|
| Phase 1: Database Schema | 5 | 0/5 |
| Phase 2: Migration Runner | 2 | 0/2 |
| Phase 3: FastAPI Integration | 3 | 0/3 |
| Phase 4: Integration Tests | 1 | 0/1 |
| Phase 5: Documentation | 3 | 0/3 |
| Phase 6: Final Validation | 1 | 0/1 |
| **Total** | **15** | **0/15** |

## Next Step

**Human Review:** Please review `tasks/plan.md` before proceeding to implementation.
