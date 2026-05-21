# SPEC-11: Schema and Migrations

## Description

Define the normalized database schema (3NF) with tables `categories`, `products`, and `movements`, including constraints, foreign keys, native ENUM, and immutability trigger.

## Phase

F1 — DB Infrastructure

## Involved Files

- `migrations/001_create_movement_type_enum.sql` — ENUM `movement_type` (IN, OUT, ADJUSTMENT, TRANSFER)
- `migrations/002_create_categories.sql` — Table `categories` with PK identity, UNIQUE name
- `migrations/003_create_products.sql` — Table `products` with FK to categories, UNIQUE SKU
- `migrations/004_create_movements.sql` — Append-only `movements` table with ENUM, CHECK, JSONB
- `migrations/005_create_immutability_trigger.sql` — BEFORE UPDATE/DELETE trigger RAISE EXCEPTION
- `src/infrastructure/db/migrate.py` — Migration runner with `schema_migrations` tracking
- `src/infrastructure/db/seed.py` — Seed data executor (manual)
- `tests/integration/test_db_schema.py` — Schema tests with testcontainers

## Acceptance Criteria

- [x] ENUM `movement_type` with values: IN, OUT, ADJUSTMENT, TRANSFER
- [x] Table `categories`: PK BIGINT IDENTITY, name TEXT UNIQUE, description TEXT, created_at TIMESTAMPTZ
- [x] Table `products`: PK BIGINT IDENTITY, sku TEXT UNIQUE, name TEXT, category_id FK RESTRICT, min_stock_threshold CHECK >= 0
- [x] Table `movements`: PK BIGINT IDENTITY, product_id FK RESTRICT, movement_type ENUM, quantity CHECK > 0, metadata JSONB DEFAULT '{}', reference TEXT
- [x] Trigger `enforce_movements_immutability` blocks UPDATE and DELETE on movements
- [x] Migration runner executes `.sql` files in numerical order with tracking
- [x] Idempotent migrations: re-running does not duplicate data or cause errors
- [x] `schema_migrations` table tracks applied versions with timestamp
- [x] **Non-transactional migration support**: files with `-- non-transactional` on first line execute without transaction (e.g., `CREATE INDEX CONCURRENTLY`, `VACUUM`)
- [x] FK on products(category_id) with ON DELETE RESTRICT
- [x] FK on movements(product_id) with ON DELETE RESTRICT
- [x] Integration tests validate: table existence, ENUM, FK, CHECK, UNIQUE, trigger
- [x] 16 integration tests pass with testcontainers PostgreSQL 16

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| BIGINT IDENTITY (not UUID) | Non-distributed system, no need for opaque IDs |
| TEXT (not VARCHAR) | PostgreSQL handles length internally, no overhead |
| TIMESTAMPTZ (not TIMESTAMP) | Explicit timezone for historical auditing |
| quantity always positive | Sign inferred from movement_type, avoids ambiguity |
| JSONB for metadata | TRANSFER needs origin/destination; locations table deferred |
| ON DELETE RESTRICT | Cannot delete products/categories with movements |
| Trigger + code for immutability | Defense in depth: DB blocks, repo only exposes INSERT |
| Manual SQL migrations | No Alembic — simpler, explicit, easy to review |
| `-- non-transactional` support | Allows `CREATE INDEX CONCURRENTLY` and other operations that cannot run inside a transaction |

## Dependencies

Spec-10 (DB Configuration)

## Status

**Completed** — 2026-05-15
