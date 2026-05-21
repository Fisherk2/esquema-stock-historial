# Optimización de Rendimiento

## SQL Explícito

Las consultas analíticas usan SQL directo con CTEs y Window Functions. Sin ORM. Cada query compleja debe incluir su `EXPLAIN ANALYZE` en el spec correspondiente para validar el plan de ejecución.

**SQL parametrizado obligatorio:** Todos los queries usan parámetros posicionales (`$1`, `$2`). Nunca f-strings, ni siquiera para valores numéricos. Ejemplo:
```python
# Correcto: SET statement_timeout = $1", timeout_ms
# Incorrecto: f"SET statement_timeout = {timeout_ms}"
```

## Pool de Conexiones

- **Tamaño configurable** via `db_pool_min_size` (default: 2) y `db_pool_max_size` (default: 10) en `Settings`.
- El pool se inicializa al startup de FastAPI y se cierra en shutdown.
- En producción, la app falla explícitamente si la DB no está disponible (no startup silencioso).
- `BasePostgresRepository` comparte el pool entre todos los repositorios, evitando conexiones duplicadas.

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

- **`statement_timeout` configurado via `server_settings` en pool (v1.0.2).** `asyncpg.create_pool(server_settings={"statement_timeout": ...})` asegura que el timeout se aplique a **todas** las conexiones del pool. El enfoque anterior (`SET statement_timeout` post-creacion) era un bug: solo afectaba la primera conexion, dejando las demas sin timeout.
- Timeouts explícitos en `asyncpg.connect()`.
- Fallback a 503 si la vista no responde dentro del SLA.
- **Scheduler timeout:** El refresh job ya no usa `SET LOCAL` (no funcionaba sin transaccion). Hereda el timeout del pool. `retry_with_backoff` tolera timeouts y conflictos.

## Migraciones Non-Transactionales

- Soporte para migraciones que no pueden ejecutarse dentro de una transacción (ej: `CREATE INDEX CONCURRENTLY`, `VACUUM`).
- Se marcan con el comentario `-- non-transactional` en la primera línea del archivo SQL.
- El ejecutor de migraciones (`migrate.py`) detecta esta marca y ejecuta sin `BEGIN/COMMIT`.
