-- Migración 003: Crear tabla products
--
-- Tabla de productos del inventario. Cada producto pertenece a una categoría.
--
-- Decisiones de diseño:
--   - SKU como TEXT UNIQUE: identificador de negocio, no la PK técnica
--   - unit_of_measure con DEFAULT 'unit': valor por defecto para productos simples
--   - min_stock_threshold CHECK >= 0: umbral no puede ser negativo
--   - FK a categories con ON DELETE RESTRICT: no se pueden eliminar categorías con productos
--   - Solo created_at (sin updated_at): los cambios se registran como movimientos ADJUSTMENT

CREATE TABLE IF NOT EXISTS products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    unit_of_measure TEXT NOT NULL DEFAULT 'unit',
    category_id BIGINT NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    min_stock_threshold INTEGER NOT NULL DEFAULT 0 CHECK (min_stock_threshold >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
