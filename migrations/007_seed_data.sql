-- Migración 007: Datos de prueba (seed data)
--
-- Inserta datos de ejemplo para desarrollo y pruebas manuales.
-- Ejecución MANUAL únicamente (make seed), nunca automática en Docker.
--
-- Contenido:
--   - 3 categorías: General, Materia Prima, Producto Terminado
--   - 10 productos distribuidos en las categorías
--   - 30 movimientos de diversos tipos (IN, OUT, ADJUSTMENT, TRANSFER)
--
-- Idempotencia:
--   - categories: ON CONFLICT (name) DO NOTHING
--   - products: ON CONFLICT (sku) DO NOTHING
--   - movements: solo inserta si la tabla está vacía

-- Categorías
INSERT INTO categories (name, description) VALUES
    ('General', 'Categoría por defecto para productos sin clasificación específica'),
    ('Materia Prima', 'Insumos y materias primas para producción'),
    ('Producto Terminado', 'Productos listos para venta o distribución')
ON CONFLICT (name) DO NOTHING;

-- Productos
INSERT INTO products (sku, name, description, unit_of_measure, category_id, min_stock_threshold)
SELECT 'SKU-001', 'Tornillo M6x20', 'Tornillo métrico cabeza hexagonal M6x20mm', 'unit', c.id, 100
FROM categories c WHERE c.name = 'Materia Prima'
UNION ALL
SELECT 'SKU-002', 'Arandela M6', 'Arandela plana M6 acero galvanizado', 'unit', c.id, 200
FROM categories c WHERE c.name = 'Materia Prima'
UNION ALL
SELECT 'SKU-003', 'Cable eléctrico 2.5mm', 'Cable de cobre calibre 2.5mm rollo 100m', 'meter', c.id, 50
FROM categories c WHERE c.name = 'Materia Prima'
UNION ALL
SELECT 'SKU-004', 'Pintura blanca 20L', 'Pintura látex interior blanca balde 20 litros', 'unit', c.id, 10
FROM categories c WHERE c.name = 'Materia Prima'
UNION ALL
SELECT 'SKU-005', 'Tabla MDF 18mm', 'Tabla MDF 2440x1220x18mm', 'unit', c.id, 20
FROM categories c WHERE c.name = 'Materia Prima'
UNION ALL
SELECT 'SKU-006', 'Kit tornillería básico', 'Kit de tornillos surtidos M4-M8 (100 unidades)', 'unit', c.id, 15
FROM categories c WHERE c.name = 'Producto Terminado'
UNION ALL
SELECT 'SKU-007', 'Cable por metros', 'Cable eléctrico cortado a medida', 'meter', c.id, 30
FROM categories c WHERE c.name = 'Producto Terminado'
UNION ALL
SELECT 'SKU-008', 'Set herramientas básico', 'Set de herramientas manuales 25 piezas', 'unit', c.id, 5
FROM categories c WHERE c.name = 'Producto Terminado'
UNION ALL
SELECT 'SKU-009', 'Cinta aisladora', 'Cinta aisladora negra rollo 20m', 'unit', c.id, 50
FROM categories c WHERE c.name = 'General'
UNION ALL
SELECT 'SKU-010', 'Guantes de seguridad', 'Guantes de nitrilo caja 100 unidades', 'box', c.id, 10
FROM categories c WHERE c.name = 'General'
ON CONFLICT (sku) DO NOTHING;

-- Movimientos (solo si la tabla está vacía)
INSERT INTO movements (product_id, movement_type, quantity, metadata, reference)
SELECT p.id, 'IN'::movement_type, 500,
    '{"supplier": "Ferretería Central"}'::jsonb, 'OC-2026-001'
FROM products p WHERE p.sku = 'SKU-001'
UNION ALL
SELECT p.id, 'IN'::movement_type, 1000,
    '{"supplier": "Ferretería Central"}'::jsonb, 'OC-2026-001'
FROM products p WHERE p.sku = 'SKU-002'
UNION ALL
SELECT p.id, 'IN'::movement_type, 200,
    '{"supplier": "ElectroSuministros"}'::jsonb, 'OC-2026-002'
FROM products p WHERE p.sku = 'SKU-003'
UNION ALL
SELECT p.id, 'IN'::movement_type, 50,
    '{"supplier": "Pinturas del Sur"}'::jsonb, 'OC-2026-003'
FROM products p WHERE p.sku = 'SKU-004'
UNION ALL
SELECT p.id, 'IN'::movement_type, 100,
    '{"supplier": "Maderas SA"}'::jsonb, 'OC-2026-004'
FROM products p WHERE p.sku = 'SKU-005'
UNION ALL
SELECT p.id, 'OUT'::movement_type, 50,
    '{"destination": "Proyecto Alpha"}'::jsonb, 'SAL-2026-001'
FROM products p WHERE p.sku = 'SKU-001'
UNION ALL
SELECT p.id, 'OUT'::movement_type, 200,
    '{"destination": "Proyecto Alpha"}'::jsonb, 'SAL-2026-001'
FROM products p WHERE p.sku = 'SKU-002'
UNION ALL
SELECT p.id, 'OUT'::movement_type, 30,
    '{"destination": "Proyecto Beta"}'::jsonb, 'SAL-2026-002'
FROM products p WHERE p.sku = 'SKU-003'
UNION ALL
SELECT p.id, 'OUT'::movement_type, 10,
    '{"destination": "Proyecto Beta"}'::jsonb, 'SAL-2026-002'
FROM products p WHERE p.sku = 'SKU-004'
UNION ALL
SELECT p.id, 'OUT'::movement_type, 20,
    '{"destination": "Proyecto Gamma"}'::jsonb, 'SAL-2026-003'
FROM products p WHERE p.sku = 'SKU-005'
UNION ALL
SELECT p.id, 'IN'::movement_type, 100,
    '{"batch": "B001"}'::jsonb, 'PROD-2026-001'
FROM products p WHERE p.sku = 'SKU-006'
UNION ALL
SELECT p.id, 'IN'::movement_type, 50,
    '{"batch": "B002"}'::jsonb, 'PROD-2026-002'
FROM products p WHERE p.sku = 'SKU-007'
UNION ALL
SELECT p.id, 'IN'::movement_type, 30,
    '{"batch": "B003"}'::jsonb, 'PROD-2026-003'
FROM products p WHERE p.sku = 'SKU-008'
UNION ALL
SELECT p.id, 'IN'::movement_type, 200,
    '{"supplier": "Distribuidora Norte"}'::jsonb, 'OC-2026-005'
FROM products p WHERE p.sku = 'SKU-009'
UNION ALL
SELECT p.id, 'IN'::movement_type, 50,
    '{"supplier": "Distribuidora Norte"}'::jsonb, 'OC-2026-005'
FROM products p WHERE p.sku = 'SKU-010'
UNION ALL
SELECT p.id, 'OUT'::movement_type, 20,
    '{"customer": "Cliente A"}'::jsonb, 'VTA-2026-001'
FROM products p WHERE p.sku = 'SKU-006'
UNION ALL
SELECT p.id, 'OUT'::movement_type, 10,
    '{"customer": "Cliente B"}'::jsonb, 'VTA-2026-002'
FROM products p WHERE p.sku = 'SKU-007'
UNION ALL
SELECT p.id, 'OUT'::movement_type, 5,
    '{"customer": "Cliente C"}'::jsonb, 'VTA-2026-003'
FROM products p WHERE p.sku = 'SKU-008'
UNION ALL
SELECT p.id, 'OUT'::movement_type, 50,
    '{"customer": "Cliente D"}'::jsonb, 'VTA-2026-004'
FROM products p WHERE p.sku = 'SKU-009'
UNION ALL
SELECT p.id, 'OUT'::movement_type, 10,
    '{"customer": "Cliente E"}'::jsonb, 'VTA-2026-005'
FROM products p WHERE p.sku = 'SKU-010'
UNION ALL
SELECT p.id, 'ADJUSTMENT'::movement_type, 10,
    '{"reason": "Inventario físico - diferencia encontrada"}'::jsonb, 'ADJ-2026-001'
FROM products p WHERE p.sku = 'SKU-001'
UNION ALL
SELECT p.id, 'ADJUSTMENT'::movement_type, 5,
    '{"reason": "Mercadería dañada - baja de stock"}'::jsonb, 'ADJ-2026-002'
FROM products p WHERE p.sku = 'SKU-002'
UNION ALL
SELECT p.id, 'ADJUSTMENT'::movement_type, 15,
    '{"reason": "Corrección por error de conteo"}'::jsonb, 'ADJ-2026-003'
FROM products p WHERE p.sku = 'SKU-003'
UNION ALL
SELECT p.id, 'TRANSFER'::movement_type, 25,
    '{"from": "Almacén Central", "to": "Sucursal Norte"}'::jsonb, 'TRF-2026-001'
FROM products p WHERE p.sku = 'SKU-004'
UNION ALL
SELECT p.id, 'TRANSFER'::movement_type, 10,
    '{"from": "Almacén Central", "to": "Sucursal Sur"}'::jsonb, 'TRF-2026-002'
FROM products p WHERE p.sku = 'SKU-005'
UNION ALL
SELECT p.id, 'TRANSFER'::movement_type, 5,
    '{"from": "Sucursal Norte", "to": "Almacén Central"}'::jsonb, 'TRF-2026-003'
FROM products p WHERE p.sku = 'SKU-006'
UNION ALL
SELECT p.id, 'IN'::movement_type, 100,
    '{"supplier": "Ferretería Central", "note": "Reposición"}'::jsonb, 'OC-2026-006'
FROM products p WHERE p.sku = 'SKU-001'
UNION ALL
SELECT p.id, 'OUT'::movement_type, 15,
    '{"destination": "Proyecto Delta"}'::jsonb, 'SAL-2026-004'
FROM products p WHERE p.sku = 'SKU-005'
UNION ALL
SELECT p.id, 'ADJUSTMENT'::movement_type, 3,
    '{"reason": "Ajuste por devolución de cliente"}'::jsonb, 'ADJ-2026-004'
FROM products p WHERE p.sku = 'SKU-008'
UNION ALL
SELECT p.id, 'IN'::movement_type, 30,
    '{"supplier": "ElectroSuministros"}'::jsonb, 'OC-2026-007'
FROM products p
WHERE p.sku = 'SKU-003'
  AND NOT EXISTS (SELECT 1 FROM movements LIMIT 1);
