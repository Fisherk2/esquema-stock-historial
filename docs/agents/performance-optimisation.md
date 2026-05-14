# Optimización de Rendimiento

## SQL Explícito

Las consultas analíticas usan SQL directo con CTEs y Window Functions. Sin ORM. Cada query compleja debe incluir su `EXPLAIN ANALYZE` en el spec correspondiente para validar el plan de ejecución.

## Vistas Materializadas

- Vista principal: `mv_stock_historical` con `REFRESH CONCURRENTLY`.
- El scheduler interno (APScheduler) refresca la vista periódicamente.
- **Fallback:** Si la vista no está disponible, se hace cálculo directo con límite de paginación.
- SLA objetivo: `<100ms` en consultas de stock histórico.

## Índices

- Índices compuestos en `movements` (`product_id`, `created_at`).
- Índices parciales para filtrar tipos de movimiento.
- Todos los índices deben ser validados con `EXPLAIN` antes de mergear.

## Concurrencia y Reintentos

- Optimistic Concurrency con versión transaccional.
- Decorador `@retry` con backoff exponencial.
- Aislamiento `READ COMMITTED` + retry en `asyncpg`.

## Manejo de Fallos

- `statement_timeout=5s` en queries analíticas.
- Timeouts explícitos en `asyncpg.connect()`.
- Fallback a 503 si la vista no responde dentro del SLA.
