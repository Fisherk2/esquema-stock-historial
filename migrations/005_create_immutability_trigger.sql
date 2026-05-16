-- Migración 005: Crear trigger de inmutabilidad para movements
--
-- Garantiza que la tabla movements sea append-only (solo INSERT).
-- Cualquier intento de UPDATE o DELETE genera una excepción.
--
-- Corrección de errores: insertar un movimiento ADJUSTMENT compensatorio,
-- nunca modificar registros históricos.
--
-- Idempotencia: DROP TRIGGER IF EXISTS + CREATE TRIGGER permite re-ejecución segura.
-- La función se crea con CREATE OR REPLACE para actualizar si ya existe.

-- Función que lanza la excepción de violación de inmutabilidad
CREATE OR REPLACE FUNCTION raise_immutable_violation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Violación de inmutabilidad: los movimientos no pueden ser modificados ni eliminados. Use un movimiento ADJUSTMENT compensatorio para corregir errores.';
END;
$$ LANGUAGE plpgsql;

-- Trigger que bloquea UPDATE y DELETE en movements
DROP TRIGGER IF EXISTS enforce_movements_immutability ON movements;
CREATE TRIGGER enforce_movements_immutability
    BEFORE UPDATE OR DELETE ON movements
    FOR EACH ROW
    EXECUTE FUNCTION raise_immutable_violation();
