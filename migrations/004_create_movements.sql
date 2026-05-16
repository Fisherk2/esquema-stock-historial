-- Migración 004: Crear tabla movements
--
-- Tabla de movimientos de inventario. Source of Truth inmutable:
-- cada movimiento es un registro append-only que no se modifica ni elimina.
--
-- Decisiones de diseño:
--   - movement_type usa el ENUM nativo de PostgreSQL (conjunto estable de 4 valores)
--   - quantity siempre positivo (CHECK > 0): el signo se infiere del tipo de movimiento
--     (IN suma, OUT resta, ADJUSTMENT ajusta, TRANSFER mueve)
--   - metadata JSONB para datos opcionales: origen/destino en TRANSFER, notas, etc.
--   - reference TEXT para referencias externas: número de orden, factura, etc.
--   - FK a products con ON DELETE RESTRICT: no se pueden eliminar productos con movimientos
--   - Solo created_at: los movimientos son inmutables, no tienen updated_at

CREATE TABLE IF NOT EXISTS movements (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    movement_type movement_type NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    metadata JSONB NOT NULL DEFAULT '{}',
    reference TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
