-- Migración 002: Crear tabla categories
--
-- Tabla de categorías para clasificar productos.
-- Normalización 3NF: las categorías son entidades separadas, no un campo
-- ENUM o string en products. Permite gestión dinámica de categorías.
--
-- Decisiones de diseño:
--   - BIGINT GENERATED ALWAYS AS IDENTITY: PK secuencial, no UUID (sistema no distribuido)
--   - TEXT para name/description: sin límite de longitud arbitrario
--   - UNIQUE en name: evita duplicados de categorías
--   - TIMESTAMPTZ: timestamps con zona horaria (nunca TIMESTAMP sin zona)

CREATE TABLE IF NOT EXISTS categories (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
