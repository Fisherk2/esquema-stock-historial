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
