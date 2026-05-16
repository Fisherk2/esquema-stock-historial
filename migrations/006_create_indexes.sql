-- Migración 006: Crear índices optimizados
--
-- Índices compuestos y parciales para consultas de stock histórico <100ms.
--
-- Diseño:
--   - Índice compuesto (product_id, created_at DESC): consultas de historial por producto,
--     ordenadas del más reciente al más antiguo. DESC optimiza ORDER BY created_at DESC.
--   - Índices parciales por movement_type: aceleran consultas filtradas por tipo
--     (ej: "solo entradas", "solo salidas"). Solo indexan filas relevantes.
--   - Índice FK en products(category_id): PostgreSQL NO indexa FK automáticamente.
--     Necesario para JOINs y para evitar locks en DELETE de categorías.
--
-- Nota: CREATE INDEX CONCURRENTLY no se usa aquí porque no puede ejecutarse
-- dentro de una transacción. Para despliegue en producción con zero-downtime,
-- ejecutar esta migración fuera del runner transaccional.

-- Índice compuesto: historial de stock por producto (más reciente primero)
CREATE INDEX IF NOT EXISTS ix_movements_product_created
    ON movements (product_id, created_at DESC);

-- Índices parciales: consultas filtradas por tipo de movimiento
CREATE INDEX IF NOT EXISTS ix_movements_type_in
    ON movements (product_id, created_at DESC)
    WHERE movement_type = 'IN';

CREATE INDEX IF NOT EXISTS ix_movements_type_out
    ON movements (product_id, created_at DESC)
    WHERE movement_type = 'OUT';

CREATE INDEX IF NOT EXISTS ix_movements_type_adjustment
    ON movements (product_id, created_at DESC)
    WHERE movement_type = 'ADJUSTMENT';

CREATE INDEX IF NOT EXISTS ix_movements_type_transfer
    ON movements (product_id, created_at DESC)
    WHERE movement_type = 'TRANSFER';

-- Índice FK: PostgreSQL no indexa FK automáticamente
CREATE INDEX IF NOT EXISTS ix_products_category_id
    ON products (category_id);
