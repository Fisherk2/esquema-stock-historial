# SPEC-12: Índices y Optimización Base

## Descripción

Crear índices compuestos y parciales para optimizar consultas de stock histórico (<100ms), índice FK en products(category_id), y seed data para desarrollo.

## Fase

F1 — Infraestructura DB

## Archivos Involucrados

- `migrations/006_create_indexes.sql` — Índices compuestos, parciales y FK
- `migrations/007_seed_data.sql` — Datos de prueba idempotentes
- `tests/integration/test_db_schema.py` — Tests de existencia de índices y seed data

## Criterios de Aceptación

- [x] Índice compuesto `ix_movements_product_created` en `(product_id, created_at DESC)`
- [x] Índice parcial `ix_movements_type_in` WHERE movement_type = 'IN'
- [x] Índice parcial `ix_movements_type_out` WHERE movement_type = 'OUT'
- [x] Índice parcial `ix_movements_type_adjustment` WHERE movement_type = 'ADJUSTMENT'
- [x] Índice parcial `ix_movements_type_transfer` WHERE movement_type = 'TRANSFER'
- [x] Índice FK `ix_products_category_id` en `products(category_id)`
- [x] Seed data: 3 categorías, 10 productos, 30 movimientos
- [x] Seed data idempotente: ON CONFLICT DO NOTHING / solo inserta si tabla vacía
- [x] Tests validan existencia de todos los índices
- [x] Tests validan que seed data inserta >= 10 productos y >= 30 movimientos

## Decisiones de Diseño

| Decisión | Racional |
|----------|----------|
| Índice compuesto (product_id, created_at DESC) | Consulta más frecuente: historial de un producto ordenado |
| Índices parciales por movement_type | Consultas filtradas por tipo solo escanean filas relevantes |
| Índice FK manual en products(category_id) | PostgreSQL NO indexa FK automáticamente; necesario para JOINs y evitar locks |
| Sin CONCURRENTLY en F1 | No puede ejecutarse en transacción; para producción zero-downtime en fases posteriores |
| Seed data manual (make seed) | Nunca automático en Docker; previene datos accidentales en producción |

## Dependencias

Spec-11 (Esquema y Migraciones)

## Estado

**Completado** — 2026-05-15
