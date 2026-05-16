# SPEC-11: Esquema y Migraciones

## Descripción

Definir el esquema de base de datos normalizado (3NF) con tablas `categories`, `products` y `movements`, incluyendo constraints, foreign keys, ENUM nativo y trigger de inmutabilidad.

## Fase

F1 — Infraestructura DB

## Archivos Involucrados

- `migrations/001_create_movement_type_enum.sql` — ENUM `movement_type` (IN, OUT, ADJUSTMENT, TRANSFER)
- `migrations/002_create_categories.sql` — Tabla `categories` con PK identity, UNIQUE name
- `migrations/003_create_products.sql` — Tabla `products` con FK a categories, SKU UNIQUE
- `migrations/004_create_movements.sql` — Tabla `movements` append-only con ENUM, CHECK, JSONB
- `migrations/005_create_immutability_trigger.sql` — Trigger BEFORE UPDATE/DELETE RAISE EXCEPTION
- `src/infrastructure/db/migrate.py` — Migration runner con tracking en `schema_migrations`
- `src/infrastructure/db/seed.py` — Seed data executor (manual)
- `tests/integration/test_db_schema.py` — Tests de esquema con testcontainers

## Criterios de Aceptación

- [x] ENUM `movement_type` con valores: IN, OUT, ADJUSTMENT, TRANSFER
- [x] Tabla `categories`: PK BIGINT IDENTITY, name TEXT UNIQUE, description TEXT, created_at TIMESTAMPTZ
- [x] Tabla `products`: PK BIGINT IDENTITY, sku TEXT UNIQUE, name TEXT, category_id FK RESTRICT, min_stock_threshold CHECK >= 0
- [x] Tabla `movements`: PK BIGINT IDENTITY, product_id FK RESTRICT, movement_type ENUM, quantity CHECK > 0, metadata JSONB DEFAULT '{}', reference TEXT
- [x] Trigger `enforce_movements_immutability` bloquea UPDATE y DELETE en movements
- [x] Migration runner ejecuta archivos `.sql` en orden numérico con tracking
- [x] Migraciones idempotentes: re-ejecutar no duplica datos ni errores
- [x] `schema_migrations` table rastrea versiones aplicadas con timestamp
- [x] FK en products(category_id) con ON DELETE RESTRICT
- [x] FK en movements(product_id) con ON DELETE RESTRICT
- [x] Tests de integración validan: existencia tablas, ENUM, FK, CHECK, UNIQUE, trigger
- [x] 16 tests de integración pasan con testcontainers PostgreSQL 16

## Decisiones de Diseño

| Decisión | Racional |
|----------|----------|
| BIGINT IDENTITY (no UUID) | Sistema no distribuido, no necesita IDs opacos |
| TEXT (no VARCHAR) | PostgreSQL maneja longitud internamente, sin overhead |
| TIMESTAMPTZ (no TIMESTAMP) | Zona horaria explícita para auditoría histórica |
| quantity siempre positivo | Signo inferido de movement_type, evita ambigüedad |
| JSONB para metadata | TRANSFER necesita origen/destino; locations table diferida |
| ON DELETE RESTRICT | No se pueden eliminar productos/categorías con movimientos |
| Trigger + código para inmutabilidad | Defensa en profundidad: DB bloquea, repo solo expone INSERT |
| Migraciones SQL manuales | No Alembic — más simple, explícito, fácil de revisar |

## Dependencias

Spec-10 (Configuración DB)

## Estado

**Completado** — 2026-05-15
