# SPEC-12: Indexes and Base Optimization

## Description

Create composite and partial indexes to optimize historical stock queries (<100ms), FK index on products(category_id), and seed data for development.

## Phase

F1 — DB Infrastructure

## Involved Files

- `migrations/006_create_indexes.sql` — Composite, partial, and FK indexes
- `migrations/007_seed_data.sql` — Idempotent test data
- `tests/integration/test_db_schema.py` — Tests for index existence and seed data

## Acceptance Criteria

- [x] Composite index `ix_movements_product_created` on `(product_id, created_at DESC)`
- [x] Partial index `ix_movements_type_in` WHERE movement_type = 'IN'
- [x] Partial index `ix_movements_type_out` WHERE movement_type = 'OUT'
- [x] Partial index `ix_movements_type_adjustment` WHERE movement_type = 'ADJUSTMENT'
- [x] Partial index `ix_movements_type_transfer` WHERE movement_type = 'TRANSFER'
- [x] FK index `ix_products_category_id` on `products(category_id)`
- [x] Seed data: 3 categories, 10 products, 30 movements
- [x] Idempotent seed data: ON CONFLICT DO NOTHING / only inserts if table is empty
- [x] Tests validate existence of all indexes
- [x] Tests validate that seed data inserts >= 10 products and >= 30 movements

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Composite index (product_id, created_at DESC) | Most frequent query: product history ordered |
| Partial indexes by movement_type | Filtered queries by type only scan relevant rows |
| Manual FK index on products(category_id) | PostgreSQL does NOT index FKs automatically; needed for JOINs and lock avoidance |
| No CONCURRENTLY in F1 | Cannot run in transaction; for zero-downtime production in later phases |
| Manual seed data (make seed) | Never automatic in Docker; prevents accidental production data |

## Dependencies

Spec-11 (Schema and Migrations)

## Status

**Completed** — 2026-05-15
