# Implementation Plan: F1 — Infraestructura DB

## Overview

F1 establishes the complete database infrastructure for the stock-historial system:
- PostgreSQL 16 schema with 3NF tables (categories, products, movements)
- Native ENUM for movement types (IN, OUT, ADJUSTMENT, TRANSFER)
- Immutability enforcement via DB trigger
- Optimized indexes (composite + partial)
- Migration runner + seed data scripts
- FastAPI lifespan integration with DB pool
- Health endpoint with SELECT 1 connectivity check
- Integration tests with testcontainers

This phase produces a fully operational database layer that F2+ builds upon.

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Manual numbered SQL migrations | No Alembic — simpler, explicit, easier to review; fits "raw numbered SQL files" from F0 spec |
| Native ENUM for movement_type | Small, stable set (4 values); per postgresql-table-design skill — use ENUM for such cases |
| JSONB for metadata | TRANSFER needs origin/destination; locations table deferred to future phase |
| Quantity always positive | Sign inferred from movement_type; simpler mental model, avoids ambiguous negative values |
| Seed data manual only | Never auto-run in Docker; prevents accidental data in production |
| statement_timeout deferred | No analytical queries exist in F1; add in F3/F5 when materialized views exist |
| TestClient sync in conftest | Per F0 decision — async deferred to F6 |

## Task List

### Phase 1: Database Schema (Migrations)

#### Task 1: Create ENUM and categories table
- **Description:** Create movement_type ENUM and categories table with IF NOT EXISTS for idempotency
- **Acceptance criteria:**
  - [ ] `migrations/001_create_movement_type_enum.sql` exists and is idempotent
  - [ ] `migrations/002_create_categories.sql` exists with PK, UNIQUE name, IF NOT EXISTS
- **Verification:** Run migrations against fresh DB twice — no error on second run
- **Dependencies:** None
- **Files:** `migrations/001_*.sql`, `migrations/002_*.sql`
- **Scope:** Small (2 files)

#### Task 2: Create products and movements tables
- **Description:** Create products table (FK to categories) and movements table (FK to products, ENUM type, CHECK quantity > 0)
- **Acceptance criteria:**
  - [ ] `migrations/003_create_products.sql` creates table with all constraints
  - [ ] `migrations/004_create_movements.sql` creates table with movement_type ENUM, CHECK(quantity>0), JSONB metadata
- **Verification:** `\d products` and `\d movements` in psql show correct schema
- **Dependencies:** Task 1
- **Files:** `migrations/003_*.sql`, `migrations/004_*.sql`
- **Scope:** Medium (2 files)

#### Task 3: Create immutability trigger
- **Description:** Create trigger function and trigger to enforce no UPDATE/DELETE on movements
- **Acceptance criteria:**
  - [ ] `migrations/005_create_immutability_trigger.sql` exists
  - [ ] UPDATE on movements raises exception
  - [ ] DELETE on movements raises exception
- **Verification:** Run `UPDATE movements SET quantity = 1 WHERE id = 1` → raises exception
- **Dependencies:** Task 2
- **Files:** `migrations/005_*.sql`
- **Scope:** Small (1 file)

#### Task 4: Create indexes
- **Description:** Create composite index on (product_id, created_at DESC), partial indexes per movement_type, FK index on products.category_id
- **Acceptance criteria:**
  - [ ] `migrations/006_create_indexes.sql` exists with all indexes
  - [ ] Composite index `ix_movements_product_created` exists
  - [ ] 4 partial indexes (one per movement_type) exist
  - [ ] FK index `ix_products_category_id` exists
- **Verification:** `SELECT * FROM pg_indexes WHERE tablename IN ('movements','products')` shows 7+ indexes
- **Dependencies:** Task 3
- **Files:** `migrations/006_*.sql`
- **Scope:** Small (1 file)

#### Task 5: Create seed data
- **Description:** Insert ~3 categories, ~10 products, ~30 movements with ON CONFLICT DO NOTHING
- **Acceptance criteria:**
  - [ ] `migrations/007_seed_data.sql` exists
  - [ ] Running twice inserts data only once (idempotent)
  - [ ] After seed: SELECT COUNT(*) FROM products ≈ 10
  - [ ] After seed: SELECT COUNT(*) FROM movements ≈ 30
- **Verification:** Run seed twice, check counts remain stable
- **Dependencies:** Task 4
- **Files:** `migrations/007_*.sql`
- **Scope:** Small (1 file)

### Checkpoint: Schema Complete
- [ ] All 7 migration files exist and are idempotent
- [ ] Schema validated: categories, products, movements tables exist with correct constraints
- [ ] Immutability trigger blocks UPDATE/DELETE
- [ ] All indexes created
- [ ] Seed data runs without error

---

### Phase 2: Migration Runner + Seed Script

#### Task 6: Create migrate.py
- **Description:** Python script that discovers and runs migrations in order, tracks in schema_migrations table
- **Acceptance criteria:**
  - [ ] `src/infrastructure/db/migrate.py` exists
  - [ ] `python -m src.infrastructure.db.migrate` runs all 7 migrations
  - [ ] Running twice skips already-applied migrations
  - [ ] schema_migrations table tracks applied versions
- **Verification:** Run migrate twice, second run shows "already applied" for all
- **Dependencies:** Task 5
- **Files:** `src/infrastructure/db/migrate.py`
- **Scope:** Medium (1 file, ~100 lines)

#### Task 7: Create seed.py
- **Description:** Python script to run seed data separately (manual-only execution)
- **Acceptance criteria:**
  - [ ] `src/infrastructure/db/seed.py` exists
  - [ ] `python -m src.infrastructure.db.seed` inserts seed data
- **Verification:** Run seed, verify product/movement counts
- **Dependencies:** Task 6
- **Files:** `src/infrastructure/db/seed.py`
- **Scope:** Small (1 file, ~30 lines)

### Checkpoint: Migration Scripts Complete
- [ ] `make migrate` runs all migrations idempotently
- [ ] `make seed` inserts seed data
- [ ] No new dependencies added to requirements.txt

---

### Phase 3: FastAPI Integration

#### Task 8: Integrate pool into FastAPI lifespan
- **Description:** Modify main.py to call init_pool on startup and close_pool on shutdown
- **Acceptance criteria:**
  - [ ] `src/main.py` lifespan calls `await init_pool(Settings())` before yield
  - [ ] `src/main.py` lifespan calls `await close_pool()` after yield
- **Verification:** App starts without error; pool is active during requests
- **Dependencies:** Task 6 (migrate.py uses connection.py)
- **Files:** `src/main.py`
- **Scope:** Small (1 file, ~10 lines changed)

#### Task 9: Add DB check to health endpoint
- **Description:** Modify health.py to include SELECT 1 check and return {status, db} response
- **Acceptance criteria:**
  - [ ] `src/adapters/api/routers/health.py` imports get_pool
  - [ ] GET /v1/health returns {status: "ok", db: "connected"} when DB is up
  - [ ] GET /v1/health returns {status: "degraded", db: "unavailable"} when DB is down
  - [ ] Both responses return HTTP 200 (degraded is informational, not error)
- **Verification:** Test with DB up and DB down scenarios
- **Dependencies:** Task 8
- **Files:** `src/adapters/api/routers/health.py`
- **Scope:** Small (1 file, ~20 lines changed)

#### Task 10: Update connection.py docstrings
- **Description:** Remove "placeholder" comments, update docstrings to reflect lifespan integration
- **Acceptance criteria:**
  - [ ] connection.py no longer mentions "placeholder" or "until F1"
  - [ ] Docstrings reflect that pool is managed by FastAPI lifespan
- **Verification:** Review docstrings
- **Dependencies:** Task 8
- **Files:** `src/infrastructure/db/connection.py`
- **Scope:** XS (docstring update only)

### Checkpoint: FastAPI Integration Complete
- [ ] App starts with pool initialized
- [ ] App shuts down with pool closed
- [ ] Health endpoint reports DB connectivity
- [ ] `make dev` works without manual pool init

---

### Phase 4: Integration Tests

#### Task 11: Create test_db_schema.py
- **Description:** Integration tests validating schema, constraints, trigger, indexes with testcontainers
- **Acceptance criteria:**
  - [ ] `tests/integration/test_db_schema.py` exists
  - [ ] Uses testcontainers.postgres for real PostgreSQL 16
  - [ ] Tests: table existence, ENUM, FK constraints, CHECK constraints, immutability trigger, indexes, seed data, UNIQUE constraints
  - [ ] All 15 test cases pass
- **Verification:** `pytest tests/integration/test_db_schema.py -v` passes
- **Dependencies:** Task 5 (schema), Task 9 (health endpoint available)
- **Files:** `tests/integration/test_db_schema.py`
- **Scope:** Large (1 file, ~200 lines, 15 test cases)

### Checkpoint: Integration Tests Complete
- [ ] All 15 test cases pass
- [ ] Schema validated against real PostgreSQL
- [ ] Constraints and trigger enforced in tests

---

### Phase 5: Documentation + Build Updates

#### Task 12: Update Makefile
- **Description:** Add migrate and seed targets to Makefile
- **Acceptance criteria:**
  - [ ] `make migrate` runs `python -m src.infrastructure.db.migrate`
  - [ ] `make seed` runs `python -m src.infrastructure.db.seed`
  - [ ] `make help` lists migrate and seed
- **Verification:** Run `make help` and verify targets listed
- **Dependencies:** Tasks 6, 7
- **Files:** `Makefile`
- **Scope:** XS (add 2 targets)

#### Task 13: Update spec-tracking.md
- **Description:** Update Spec-10/11/12 status from Pend/Bloq to En Progreso/Pend
- **Acceptance criteria:**
  - [ ] Spec-10: Estado "Pend." → "En Progreso"
  - [ ] Spec-11: Estado "Bloq." → "Pend."
  - [ ] Spec-12: Estado "Bloq." → "Pend."
- **Verification:** Review file
- **Dependencies:** All tasks
- **Files:** `docs/workflow/spec-tracking.md`
- **Scope:** XS (status update)

#### Task 14: Update SPEC.md
- **Description:** Add F1 section below F0 content
- **Acceptance criteria:**
  - [ ] SPEC.md includes F1 section with summary and reference to SPEC-F1.md
- **Verification:** Review file
- **Dependencies:** All tasks
- **Files:** `SPEC.md`
- **Scope:** XS (add section)

### Checkpoint: Documentation Complete
- [ ] Makefile has migrate and seed targets
- [ ] spec-tracking.md reflects F1 progress
- [ ] SPEC.md includes F1 summary

---

### Phase 6: Final Validation

#### Task 15: Run make build
- **Description:** Execute full build pipeline: lint + format + test + migrate
- **Acceptance criteria:**
  - [ ] `make lint` passes with 0 errors
  - [ ] `make format` passes
  - [ ] `make test` passes
  - [ ] `make migrate` runs successfully
- **Verification:** `make build` exit code 0
- **Dependencies:** All tasks
- **Scope:** XS (validation only)

### Checkpoint: F1 Complete
- [ ] All acceptance criteria met
- [ ] make build passes
- [ ] Ready for human review before proceeding to F2

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Migration idempotency issues | High | Use IF NOT EXISTS / DO NOTHING patterns; test by running twice |
| Immutability trigger blocks legitimate needs | Medium | Document that corrections use ADJUSTMENT movements, not UPDATE |
| testcontainers fails to start | Low | Use docker-compose for manual verification if container fails |
| FUSE filesystem execute permissions | Low | Use global ruff / python -m black as documented in AGENTS.md |

## Open Questions

None — all 4 open questions from F1 spec draft were resolved:
- locations table: DEFERRED (use JSONB metadata for TRANSFER)
- quantity sign: ALWAYS POSITIVE (sign inferred from movement_type)
- seed execution: MANUAL ONLY (make seed, never auto)
- statement_timeout: DEFERRED to F3/F5

## Parallelization Opportunities

**Safe to parallelize after Task 5 (schema complete):**
- Task 6 (migrate.py) and Task 7 (seed.py) can be done together
- Task 8 (main.py lifespan) and Task 9 (health.py) can be done together
- Task 11 (integration tests) can start after Task 5 (schema exists)

**Must be sequential:**
- Migrations must complete before migrate.py can be tested
- Migrations must be applied before seed.py can be tested
- main.py lifespan must integrate before health.py can test DB connectivity
