# Performance Optimization

## Explicit SQL

Analytical queries use direct SQL with CTEs and Window Functions. No ORM. Each complex query must include its `EXPLAIN ANALYZE` in the corresponding spec to validate the execution plan.

**Mandatory parameterized SQL:** All queries use positional parameters (`$1`, `$2`). Never f-strings, not even for numeric values. Example:
```python
# Correcto: SET statement_timeout = $1", timeout_ms
# Incorrecto: f"SET statement_timeout = {timeout_ms}"
```

## Connection Pool

- **Configurable size** via `db_pool_min_size` (default: 2) and `db_pool_max_size` (default: 10) in `Settings`.
- The pool is initialized at FastAPI startup and closed on shutdown.
- In production, the app fails explicitly if the DB is not available (no silent startup).
- `BasePostgresRepository` shares the pool across all repositories, avoiding duplicate connections.

## Materialized Views

- Main view: `mv_stock_historical` with `REFRESH CONCURRENTLY`.
- The internal scheduler (APScheduler) refreshes the view periodically.
- **Fallback:** If the view is not available, direct calculation is performed with pagination limit.
- Target SLA: `<100ms` for historical stock queries.

## Indexes

- Composite indexes on `movements` (`product_id`, `created_at`).
- Partial indexes to filter movement types.
- All indexes must be validated with `EXPLAIN` before merging.

## Concurrency and Retries

- Optimistic Concurrency with transactional versioning.
- `@retry` decorator with exponential backoff.
- `READ COMMITTED` isolation + retry in `asyncpg`.

## Failure Handling

- **`statement_timeout` configured via `server_settings` in pool.** `asyncpg.create_pool(server_settings={"statement_timeout": ...})` ensures the timeout applies to **all** pool connections. The previous approach (`SET statement_timeout` post-creation) was a bug: it only affected the first connection, leaving the rest without timeout.
- Explicit timeouts in `asyncpg.connect()`.
- Fallback to 503 if the view does not respond within SLA.
- **Scheduler timeout:** The refresh job no longer uses `SET LOCAL` (it didn't work without a transaction). It inherits the pool timeout. `retry_with_backoff` tolerates timeouts and conflicts.

## Non-Transactional Migrations

- Support for migrations that cannot run inside a transaction (e.g., `CREATE INDEX CONCURRENTLY`, `VACUUM`).
- They are marked with the `-- non-transactional` comment on the first line of the SQL file.
- The migration executor (`migrate.py`) detects this marker and executes without `BEGIN/COMMIT`.
