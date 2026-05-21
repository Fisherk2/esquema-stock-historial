# SPEC-31: Materialized Views

**Phase:** F3 — Data Adapters  
**Dependencies:** Spec-12 (Indexes) ✅ Completed, Spec-30 (Repository) ✅ Completed  
**Priority:** High  
**Status:** Pending  

---

## Objective

Create the materialized view `mv_stock_historical` to optimize historical stock queries to <100ms. The view precalculates stock per product, avoiding recalculating SUM/CASE on every query. Includes SQL migration, unique index for `REFRESH CONCURRENTLY`, and standalone refresh function.

**Design principles:**
- **REFRESH CONCURRENTLY** — does not block reads while refreshing
- **Mandatory unique index** — PostgreSQL requires it for concurrent refresh
- **No automatic refresh in F3** — refresh is executed manually; APScheduler is added in F5
- **Fallback already exists** — Spec-30 already implements direct calculation as fallback

---

## Migration SQL

### `migrations/008_create_mv_stock_historical.sql`

```sql
-- Migration 008: Create materialized view mv_stock_historical
--
-- View that precalculates the current stock of each product from
-- all its movements. Allows stock queries in <100ms without
-- recalculating SUM/CASE on each request.
--
-- Design decisions:
--   - Unique index on product_id: required by REFRESH CONCURRENTLY
--   - last_movement_at: timestamp of the last movement, useful for
--     detecting stale views and deciding when to refresh
--   - No automatic refresh in F3: APScheduler is added in F5
--   - Fallback: if the view is empty or stale, get_current_stock() uses
--     direct calculation (already implemented in Spec-30)

-- Materialized view with stock calculation per product
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_stock_historical AS
SELECT
    p.id AS product_id,
    p.sku,
    p.name AS product_name,
    COALESCE(
        SUM(
            CASE m.movement_type
                WHEN 'IN' THEN m.quantity
                WHEN 'OUT' THEN -m.quantity
                WHEN 'ADJUSTMENT' THEN m.quantity
                WHEN 'TRANSFER' THEN -m.quantity
                ELSE 0
            END
        ), 0
    ) AS current_stock,
    MAX(m.created_at) AS last_movement_at,
    NOW() AS calculated_at
FROM products p
LEFT JOIN movements m ON m.product_id = p.id
GROUP BY p.id, p.sku, p.name;

-- Unique index required for REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_stock_historical_product
    ON mv_stock_historical (product_id);

-- Additional index for low stock queries
CREATE INDEX IF NOT EXISTS ix_mv_stock_historical_stock
    ON mv_stock_historical (current_stock);

-- Index to detect stale views
CREATE INDEX IF NOT EXISTS ix_mv_stock_historical_last_movement
    ON mv_stock_historical (last_movement_at DESC);
```

---

## Function: `refresh_stock_view()`

Standalone function in `src/infrastructure/db/refresh.py` to refresh the view manually.

```python
from __future__ import annotations

import logging

import asyncpg

logger = logging.getLogger(__name__)

_REFRESH_SQL = "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_stock_historical"


async def refresh_stock_view(pool: asyncpg.Pool) -> None:
    """Refreshes the materialized view mv_stock_historical.

    Uses REFRESH CONCURRENTLY to not block reads during the
    refresh. Requires the view to have a unique index (created in
    migration 008).

    Args:
        pool: asyncpg connection pool.

    Raises:
        asyncpg.UndefinedTableError: If the view does not exist yet.

    Example::

        from src.infrastructure.db.refresh import refresh_stock_view

        await refresh_stock_view(pool)
    """
    try:
        await pool.execute(_REFRESH_SQL)
        logger.info("mv_stock_historical refreshed successfully")
    except asyncpg.UndefinedTableError:
        logger.warning("mv_stock_historical does not exist yet, skipping refresh")
    except Exception:
        logger.exception("Failed to refresh mv_stock_historical")
        raise
```

---

## Integration with `PostgresStockQueryRepository`

In Spec-31, `PostgresStockQueryRepository` is updated to use the materialized view as the primary source, keeping direct calculation as fallback:

### Optimized `get_current_stock()`

```sql
-- Optimized query with materialized view
SELECT current_stock
FROM mv_stock_historical
WHERE product_id = $1
```

### `get_stock_at_date()` — continues using direct calculation

The materialized view only contains the **current** stock. For historical queries (stock at a past date), direct calculation with `movements` is still used:

```sql
-- Direct calculation for historical stock
SELECT COALESCE(
    SUM(
        CASE movement_type
            WHEN 'IN' THEN quantity
            WHEN 'OUT' THEN -quantity
            WHEN 'ADJUSTMENT' THEN quantity
            WHEN 'TRANSFER' THEN -quantity
            ELSE 0
        END
    ), 0
) AS stock
FROM movements
WHERE product_id = $1 AND created_at <= $2
```

---

## Files

| File | Description |
|------|-------------|
| `migrations/008_create_mv_stock_historical.sql` | Materialized view DDL + 3 indexes |
| `src/infrastructure/db/refresh.py` | `refresh_stock_view()` — standalone function for manual refresh |
| `src/infrastructure/repositories/stock_query_repository.py` | Update: `get_current_stock()` uses view, `get_stock_at_date()` uses direct calculation |

---

## Acceptance Criteria

- [ ] View `mv_stock_historical` exists after executing migration 008
- [ ] Unique index `ix_mv_stock_historical_product` exists (required for REFRESH CONCURRENTLY)
- [ ] `refresh_stock_view()` executes without error and refreshes the view correctly
- [ ] `get_current_stock()` returns the same value as direct calculation (validated with integration test)
- [ ] `get_stock_at_date()` continues working with direct calculation (does not use view)
- [ ] Integration tests validate: view creation, refresh, data consistency, fallback

---

## Testing Strategy

- **Integration test**: verify that migration 008 creates the view and indexes
- **Consistency test**: insert movements, refresh view, compare result with direct calculation
- **Refresh test**: execute `refresh_stock_view()` before and after inserting movements, verify that stock updates
- **Fallback test**: temporarily drop the view, verify that `get_current_stock()` falls gracefully to direct calculation

---

## Performance Notes

### Expected Query Plan (materialized view)

```
Index Scan using ix_mv_stock_historical_product on mv_stock_historical
  Index Cond: (product_id = $1)
  Execution Time: <1ms
```

### Expected Query Plan (direct calculation, without view)

```
Aggregate
  ->  Index Scan using ix_movements_product_created on movements
        Index Cond: (product_id = $1)
  Execution Time: 5-50ms (depends on the number of movements)
```

---

## Resolved Questions

1. **Include `category_id` in the materialized view?** → **No.** Minimum viable: `product_id`, `sku`, `product_name`, `current_stock`, `last_movement_at`, `calculated_at`. If in F5/F6 stock queries by category without JOIN are needed, it will be added in an additional migration. It would not break existing uses since it only adds columns.

2. **Add `timeout` in `refresh_stock_view()`?** → **No.** `REFRESH CONCURRENTLY` is an operation controlled by PostgreSQL. If refresh time needs to be limited, `statement_timeout` is used at session level (`SET statement_timeout = '30s'` before the refresh). This can be configured in the function if the need arises in F5.

3. **Add endpoint `POST /v1/admin/refresh-stock-view` for manual refresh?** → **Not in F3.** Manual refresh is executed via the Python function `refresh_stock_view()` or, in F5, through APScheduler with a periodic refresh policy. An admin endpoint adds complexity (auth, access control) that does not justify the current benefit.
