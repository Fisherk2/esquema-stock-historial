-- Migración 001: Crear tipo ENUM movement_type
--
-- Define los tipos de movimiento permitidos en el sistema.
-- PostgreSQL no soporta IF NOT EXISTS para CREATE TYPE, por lo que
-- se usa un bloque DO con manejo de excepción para idempotencia.
--
-- Valores:
--   IN: Entrada de stock al inventario
--   OUT: Salida de stock del inventario
--   ADJUSTMENT: Ajuste correctivo (compensación de errores)
--   TRANSFER: Transferencia entre ubicaciones (metadata JSONB)

DO $$
BEGIN
    CREATE TYPE movement_type AS ENUM ('IN', 'OUT', 'ADJUSTMENT', 'TRANSFER');
EXCEPTION
    WHEN duplicate_object THEN
        NULL; -- El tipo ya existe, continuar sin error
END
$$;
