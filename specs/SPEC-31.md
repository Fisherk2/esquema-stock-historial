# SPEC-31: Vistas Materializadas

**Fase:** F3 — Adaptadores de Datos  
**Dependencias:** Spec-12 (Índices) ✅ Completado, Spec-30 (Repositorio) ✅ Completado  
**Prioridad:** Alta  
**Estado:** Pendiente  

---

## Objective

Crear la vista materializada `mv_stock_historical` para optimizar consultas de stock histórico a <100ms. La vista precalcula el stock por producto, evitando recalcular SUM/CASE en cada consulta. Incluye migración SQL, índice único para `REFRESH CONCURRENTLY`, y función de refresh standalone.

**Principios de diseño:**
- **REFRESH CONCURRENTLY** — no bloquea lecturas mientras se refresca
- **Índice único obligatorio** — PostgreSQL lo requiere para refresh concurrente
- **Sin refresh automático en F3** — el refresh se ejecuta manualmente; APScheduler se añade en F5
- **Fallback ya existe** — Spec-30 ya implementa cálculo directo como fallback

---

## Migration SQL

### `migrations/008_create_mv_stock_historical.sql`

```sql
-- Migración 008: Crear vista materializada mv_stock_historical
--
-- Vista que precalcula el stock actual de cada producto a partir de
-- todos sus movimientos. Permite consultas de stock en <100ms sin
-- recalcular SUM/CASE en cada request.
--
-- Decisiones de diseño:
--   - Índice único en product_id: requerido por REFRESH CONCURRENTLY
--   - last_movement_at: marca de tiempo del último movimiento, útil para
--     detectar vistas stale y decidir cuándo refrescar
--   - Sin refresh automático en F3: se añade APScheduler en F5
--   - Fallback: si la vista está vacía o stale, get_current_stock() usa
--     cálculo directo (ya implementado en Spec-30)

-- Vista materializada con cálculo de stock por producto
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

-- Índice único requerido para REFRESH CONCURRENTLY
CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_stock_historical_product
    ON mv_stock_historical (product_id);

-- Índice adicional para consultas por stock bajo
CREATE INDEX IF NOT EXISTS ix_mv_stock_historical_stock
    ON mv_stock_historical (current_stock);

-- Índice para detectar vistas stale
CREATE INDEX IF NOT EXISTS ix_mv_stock_historical_last_movement
    ON mv_stock_historical (last_movement_at DESC);
```

---

## Function: `refresh_stock_view()`

Función standalone en `src/infrastructure/db/refresh.py` para refrescar la vista manualmente.

```python
from __future__ import annotations

import logging

import asyncpg

logger = logging.getLogger(__name__)

_REFRESH_SQL = "REFRESH MATERIALIZED VIEW CONCURRENTLY mv_stock_historical"


async def refresh_stock_view(pool: asyncpg.Pool) -> None:
    """Refresca la vista materializada mv_stock_historical.

    Usa REFRESH CONCURRENTLY para no bloquear lecturas durante el
    refresh. Requiere que la vista tenga un índice único (creado en
    migración 008).

    Args:
        pool: Pool de conexiones asyncpg.

    Raises:
        asyncpg.UndefinedTableError: Si la vista no existe aún.

    Ejemplo::

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

En Spec-31, `PostgresStockQueryRepository` se actualiza para usar la vista materializada como fuente primaria, manteniendo el cálculo directo como fallback:

### `get_current_stock()` optimizado

```sql
-- Query optimizada con vista materializada
SELECT current_stock
FROM mv_stock_historical
WHERE product_id = $1
```

### `get_stock_at_date()` — sigue usando cálculo directo

La vista materializada solo contiene el stock **actual**. Para consultas históricas (stock en una fecha pasada), se sigue usando el cálculo directo con `movements`:

```sql
-- Cálculo directo para stock histórico
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
| `migrations/008_create_mv_stock_historical.sql` | DDL de vista materializada + 3 índices |
| `src/infrastructure/db/refresh.py` | `refresh_stock_view()` — función standalone para refresh manual |
| `src/infrastructure/repositories/stock_query_repository.py` | Actualización: `get_current_stock()` usa vista, `get_stock_at_date()` usa cálculo directo |

---

## Acceptance Criteria

- [ ] View `mv_stock_historical` existe tras ejecutar migración 008
- [ ] Índice único `ix_mv_stock_historical_product` existe (requerido para REFRESH CONCURRENTLY)
- [ ] `refresh_stock_view()` ejecuta sin error y refresca la vista correctamente
- [ ] `get_current_stock()` retorna el mismo valor que el cálculo directo (validación con test de integración)
- [ ] `get_stock_at_date()` sigue funcionando con cálculo directo (no usa vista)
- [ ] Tests de integración validan: creación de vista, refresh, consistencia de datos, fallback

---

## Testing Strategy

- **Test de integración**: verificar que la migración 008 crea la vista y los índices
- **Test de consistencia**: insertar movimientos, refrescar vista, comparar resultado con cálculo directo
- **Test de refresh**: ejecutar `refresh_stock_view()` antes y después de insertar movimientos, verificar que el stock se actualiza
- **Test de fallback**: eliminar la vista temporalmente, verificar que `get_current_stock()` cae gracefully al cálculo directo

---

## Performance Notes

### Expected Query Plan (vista materializada)

```
Index Scan using ix_mv_stock_historical_product on mv_stock_historical
  Index Cond: (product_id = $1)
  Execution Time: <1ms
```

### Expected Query Plan (cálculo directo, sin vista)

```
Aggregate
  ->  Index Scan using ix_movements_product_created on movements
        Index Cond: (product_id = $1)
  Execution Time: 5-50ms (depende del número de movimientos)
```

---

## Resolved Questions

1. **¿Incluir `category_id` en la vista materializada?** → **No.** Mínimo viable: `product_id`, `sku`, `product_name`, `current_stock`, `last_movement_at`, `calculated_at`. Si en F5/F6 se necesitan consultas de stock por categoría sin JOIN, se añade en una migración adicional. No rompería los usos existentes ya que solo añade columnas.

2. **¿Añadir `timeout` en `refresh_stock_view()`?** → **No.** `REFRESH CONCURRENTLY` es una operación controlada por PostgreSQL. Si se necesita limitar el tiempo del refresh, se usa `statement_timeout` a nivel de sesión (`SET statement_timeout = '30s'` antes del refresh). Esto se puede configurar en la función si la necesidad surge en F5.

3. **¿Añadir endpoint `POST /v1/admin/refresh-stock-view` para refresh manual?** → **No en F3.** El refresh manual se ejecuta vía la función Python `refresh_stock_view()` o, en F5, mediante APScheduler con política de refresh periódica. Un endpoint admin añade complejidad (auth, access control) que no justifica el beneficio actual.
