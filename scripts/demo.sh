#!/usr/bin/env bash
# scripts/demo.sh — Demo completo del sistema Stock Historial
# Ejercita el flujo completo: health → categoria → producto → IN → stock → OUT → stock → historico → movimientos
#
# Uso: make demo  (o  bash scripts/demo.sh)
# Requiere: servidor corriendo en DEMO_BASE_URL (default: http://localhost:8000)

set -euo pipefail

BASE_URL="${DEMO_BASE_URL:-http://localhost:8000}"

echo "═══════════════════════════════════════════════════════════"
echo "  Stock Historial — Demo Script"
echo "  Base URL: ${BASE_URL}"
echo "═══════════════════════════════════════════════════════════"
echo ""

# ── Paso 1: Health Check ─────────────────────────────────────
echo "📡 Paso 1: Health Check"
HEALTH=$(curl -sf "${BASE_URL}/v1/health")
echo "${HEALTH}" | python3 -m json.tool
echo ""

# ── Paso 2: Crear Categoria ──────────────────────────────────
echo "📦 Paso 2: Crear Categoria"
CATEGORY=$(curl -sf -X POST "${BASE_URL}/v1/categories" \
  -H "Content-Type: application/json" \
  -d '{"name": "Electronics", "description": "Productos electronicos"}')
echo "${CATEGORY}" | python3 -m json.tool
CATEGORY_ID=$(echo "${CATEGORY}" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  → Category ID: ${CATEGORY_ID}"
echo ""

# ── Paso 3: Crear Producto ───────────────────────────────────
echo "🏷️  Paso 3: Crear Producto"
PRODUCT=$(curl -sf -X POST "${BASE_URL}/v1/products" \
  -H "Content-Type: application/json" \
  -d "{
    \"sku\": \"DEMO-001\",
    \"name\": \"Widget A\",
    \"unit_of_measure\": \"unit\",
    \"category_id\": ${CATEGORY_ID},
    \"description\": \"Producto de demostracion\",
    \"min_stock_threshold\": 10
  }")
echo "${PRODUCT}" | python3 -m json.tool
PRODUCT_ID=$(echo "${PRODUCT}" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "  → Product ID: ${PRODUCT_ID}"
echo ""

# ── Paso 4: Registrar Movimiento IN (+50) ────────────────────
echo "📥 Paso 4: Registrar Movimiento IN (+50)"
MOV_IN=$(curl -sf -X POST "${BASE_URL}/v1/movements" \
  -H "Content-Type: application/json" \
  -d "{
    \"product_id\": ${PRODUCT_ID},
    \"movement_type\": \"IN\",
    \"quantity\": 50,
    \"metadata\": {\"supplier\": \"Demo Supplier\"},
    \"reference\": \"DEMO-IN-001\"
  }")
echo "${MOV_IN}" | python3 -m json.tool
echo ""

# ── Paso 5: Consultar Stock Actual ───────────────────────────
echo "📊 Paso 5: Consultar Stock Actual"
STOCK1=$(curl -sf "${BASE_URL}/v1/stock/${PRODUCT_ID}/current")
echo "${STOCK1}" | python3 -m json.tool
echo ""

# ── Paso 6: Registrar Movimiento OUT (-10) ───────────────────
echo "📤 Paso 6: Registrar Movimiento OUT (-10)"
MOV_OUT=$(curl -sf -X POST "${BASE_URL}/v1/movements" \
  -H "Content-Type: application/json" \
  -d "{
    \"product_id\": ${PRODUCT_ID},
    \"movement_type\": \"OUT\",
    \"quantity\": 10,
    \"reference\": \"DEMO-OUT-001\"
  }")
echo "${MOV_OUT}" | python3 -m json.tool
echo ""

# ── Paso 7: Consultar Stock Actual (actualizado) ─────────────
echo "📊 Paso 7: Consultar Stock Actual (actualizado)"
STOCK2=$(curl -sf "${BASE_URL}/v1/stock/${PRODUCT_ID}/current")
echo "${STOCK2}" | python3 -m json.tool
echo ""

# ── Paso 8: Consultar Stock Historico ────────────────────────
echo "📅 Paso 8: Consultar Stock Historico (at-date)"
DEMO_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
STOCK_HIST=$(curl -sf -G "${BASE_URL}/v1/stock/${PRODUCT_ID}/at-date" \
  --data-urlencode "date=${DEMO_DATE}")
echo "${STOCK_HIST}" | python3 -m json.tool
echo ""

# ── Paso 9: Listar Movimientos del Producto ──────────────────
echo "📋 Paso 9: Listar Movimientos del Producto"
MOV_LIST=$(curl -sf "${BASE_URL}/v1/movements?product_id=${PRODUCT_ID}&limit=10")
echo "${MOV_LIST}" | python3 -m json.tool
echo ""

echo "═══════════════════════════════════════════════════════════"
echo "  ✅ Demo completado exitosamente"
echo "═══════════════════════════════════════════════════════════"
