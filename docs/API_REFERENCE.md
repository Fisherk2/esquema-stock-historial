# API Reference — Stock Historial v1.0.0

## Overview

| Aspecto | Valor |
|---|---|
| Base URL | `http://localhost:8000/v1` |
| Autenticación | No implementada (API abierta) |
| Content-Type | `application/json` |
| Formato de fecha | ISO 8601 (timezone-aware) |
| Paginación | `limit` + `offset` en endpoints de lista |
| OpenAPI | Disponible en `/docs` y `/redoc` |

## Formato de Error

Todos los errores retornan un cuerpo JSON con el siguiente formato:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Códigos de Error

| Código HTTP | Significado | Cuándo se retorna |
|---|---|---|
| `400` | Bad Request | Payload inválido, validación Pydantic fallida |
| `404` | Not Found | Recurso no encontrado (producto, movimiento, categoria) |
| `405` | Method Not Allowed | Intento de modificar movimiento inmutable |
| `409` | Conflict | Stock negativo, conflicto de concurrencia |
| `422` | Unprocessable Entity | Error de validación de campos Pydantic |
| `500` | Internal Server Error | Error interno del servidor |

## Endpoints

---

### 1. Health Check

```
GET /v1/health
```

Verifica el estado operativo de la aplicación y conectividad con PostgreSQL.

**Parámetros:** Ninguno

**Respuesta exitosa (200):**

```json
{
  "status": "ok",
  "db": "connected"
}
```

**Respuesta degradada (200):**

```json
{
  "status": "degraded",
  "db": "unavailable"
}
```

**Ejemplo:**

```bash
curl http://localhost:8000/v1/health | python3 -m json.tool
```

---

### 2. Crear Categoria

```
POST /v1/categories
```

Crea una nueva categoria de productos.

**Body:**

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `name` | string | Sí | Nombre (1-100 caracteres) |
| `description` | string | No | Descripción opcional (max 500) |

**Ejemplo de request:**

```json
{
  "name": "Electronics",
  "description": "Productos electronicos"
}
```

**Respuesta exitosa (201):**

```json
{
  "id": 1,
  "name": "Electronics",
  "description": "Productos electronicos",
  "created_at": "2025-05-20T14:30:00Z"
}
```

**Ejemplo de error:**

```bash
# name vacío → 422
curl -X POST http://localhost:8000/v1/categories \
  -H "Content-Type: application/json" \
  -d '{"name": "", "description": "test"}'
```

```json
{
  "detail": [{"type": "string_too_short", "loc": ["body", "name"], "msg": "String should have at least 1 character"}]
}
```

**Ejemplo:**

```bash
curl -X POST http://localhost:8000/v1/categories \
  -H "Content-Type: application/json" \
  -d '{"name": "Electronics", "description": "Productos electronicos"}'
```

---

### 3. Listar Categorias

```
GET /v1/categories
```

Lista todas las categorias existentes (sin paginación).

**Respuesta exitosa (200):**

```json
[
  {
    "id": 1,
    "name": "Electronics",
    "description": "Productos electronicos",
    "created_at": "2025-05-20T14:30:00Z"
  }
]
```

**Ejemplo:**

```bash
curl http://localhost:8000/v1/categories | python3 -m json.tool
```

---

### 4. Crear Producto

```
POST /v1/products
```

Crea un nuevo producto en el inventario. La categoria debe existir previamente.

**Body:**

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `sku` | string | Sí | Código SKU único (pattern: `^[A-Za-z0-9\-_]{1,50}$`) |
| `name` | string | Sí | Nombre del producto (1-255 caracteres) |
| `unit_of_measure` | string | Sí | Unidad de medida (e.g., "unit", "kg", "liter") |
| `category_id` | int | Sí | ID de la categoria (debe existir) |
| `description` | string | No | Descripción opcional (max 1000) |
| `min_stock_threshold` | int | No | Umbral de alerta (default: 0, mínimo: 0) |

**Ejemplo de request:**

```json
{
  "sku": "PROD-001",
  "name": "Widget A",
  "unit_of_measure": "unit",
  "category_id": 1,
  "description": "Widget de prueba",
  "min_stock_threshold": 10
}
```

**Respuesta exitosa (201):**

```json
{
  "id": 1,
  "sku": "PROD-001",
  "name": "Widget A",
  "description": "Widget de prueba",
  "unit_of_measure": "unit",
  "category_id": 1,
  "min_stock_threshold": 10,
  "created_at": "2025-05-20T14:30:00Z"
}
```

**Ejemplo de error:**

```bash
# categoria_id no existe → 404 (FK violation)
curl -X POST http://localhost:8000/v1/products \
  -H "Content-Type: application/json" \
  -d '{"sku": "X-999", "name": "Ghost", "unit_of_measure": "unit", "category_id": 9999}'
```

**Ejemplo:**

```bash
curl -X POST http://localhost:8000/v1/products \
  -H "Content-Type: application/json" \
  -d '{"sku": "PROD-001", "name": "Widget A", "unit_of_measure": "unit", "category_id": 1}'
```

---

### 5. Listar Productos

```
GET /v1/products
```

Lista productos con paginación.

**Parámetros de query:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `limit` | int | 100 | Máximo de resultados (1-1000) |
| `offset` | int | 0 | Desplazamiento |

**Respuesta exitosa (200):**

```json
{
  "items": [
    {
      "id": 1,
      "sku": "PROD-001",
      "name": "Widget A",
      "description": null,
      "unit_of_measure": "unit",
      "category_id": 1,
      "min_stock_threshold": 0,
      "created_at": "2025-05-20T14:30:00Z"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Ejemplo:**

```bash
curl "http://localhost:8000/v1/products?limit=10&offset=0"
```

---

### 6. Obtener Producto por ID

```
GET /v1/products/{product_id}
```

Obtiene un producto por su identificador único.

**Parámetros de path:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `product_id` | int | ID del producto |

**Respuesta exitosa (200):**

```json
{
  "id": 1,
  "sku": "PROD-001",
  "name": "Widget A",
  "description": null,
  "unit_of_measure": "unit",
  "category_id": 1,
  "min_stock_threshold": 0,
  "created_at": "2025-05-20T14:30:00Z"
}
```

**Ejemplo de error:**

```bash
# Producto no existe → 404
curl http://localhost:8000/v1/products/9999
```

```json
{
  "detail": "Product not found"
}
```

**Ejemplo:**

```bash
curl http://localhost:8000/v1/products/1
```

---

### 7. Crear Movimiento de Stock

```
POST /v1/movements
```

Registra un nuevo movimiento de inventario. Tipos: `IN`, `OUT`, `ADJUSTMENT`, `TRANSFER`.

**Body:**

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `product_id` | int | Sí | ID del producto (debe existir) |
| `movement_type` | string | Sí | `IN`, `OUT`, `ADJUSTMENT` o `TRANSFER` |
| `quantity` | int | Sí | Cantidad positiva (> 0) |
| `metadata` | object | Condicional | Contexto. Obligatorio para TRANSFER y ADJUSTMENT |
| `reference` | string | No | Referencia externa (max 255) |

**Metadata condicional:**
- `TRANSFER`: requiere `origin` y `destination` en metadata
- `ADJUSTMENT`: requiere `reason` en metadata

**Ejemplo de request (IN):**

```json
{
  "product_id": 1,
  "movement_type": "IN",
  "quantity": 50,
  "metadata": {"supplier": "ACME Corp"},
  "reference": "PO-12345"
}
```

**Respuesta exitosa (201):**

```json
{
  "id": 1,
  "product_id": 1,
  "movement_type": "IN",
  "quantity": 50,
  "metadata": {"supplier": "ACME Corp"},
  "reference": "PO-12345",
  "created_at": "2025-05-20T14:30:00Z"
}
```

**Ejemplo de error:**

```bash
# OUT con stock insuficiente → 409
curl -X POST http://localhost:8000/v1/movements \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "movement_type": "OUT", "quantity": 9999}'
```

```json
{
  "detail": "Insufficient stock: cannot remove 9999 units, only X available"
}
```

**Ejemplo:**

```bash
curl -X POST http://localhost:8000/v1/movements \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "movement_type": "IN", "quantity": 50, "reference": "DEMO-IN-001"}'
```

---

### 8. Obtener Movimiento por ID

```
GET /v1/movements/{movement_id}
```

Recupera un movimiento por su identificador único.

**Parámetros de path:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `movement_id` | int | ID del movimiento |

**Respuesta exitosa (200):**

```json
{
  "id": 1,
  "product_id": 1,
  "movement_type": "IN",
  "quantity": 50,
  "metadata": {"supplier": "ACME Corp"},
  "reference": "PO-12345",
  "created_at": "2025-05-20T14:30:00Z"
}
```

**Ejemplo de error:**

```bash
# Movimiento no existe → 404
curl http://localhost:8000/v1/movements/9999
```

```json
{
  "detail": "Movement not found"
}
```

**Ejemplo:**

```bash
curl http://localhost:8000/v1/movements/1
```

---

### 9. Listar Movimientos de un Producto

```
GET /v1/movements?product_id={id}
```

Lista movimientos de un producto con paginación.

**Parámetros de query:**

| Parámetro | Tipo | Default | Descripción |
|---|---|---|---|
| `product_id` | int | **Requerido** | ID del producto |
| `limit` | int | 100 | Máximo de resultados (1-1000) |
| `offset` | int | 0 | Desplazamiento |

**Respuesta exitosa (200):**

```json
{
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "movement_type": "IN",
      "quantity": 50,
      "metadata": {},
      "reference": "PO-12345",
      "created_at": "2025-05-20T14:30:00Z"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Ejemplo:**

```bash
curl "http://localhost:8000/v1/movements?product_id=1&limit=10"
```

---

### 10. Consultar Stock Actual

```
GET /v1/stock/{product_id}/current
```

Obtiene el stock actual de un producto usando la vista materializada (con fallback a cálculo directo).

**Parámetros de path:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `product_id` | int | ID del producto |

**Respuesta exitosa (200):**

```json
{
  "product_id": 1,
  "current_stock": 40.0
}
```

**Ejemplo:**

```bash
curl http://localhost:8000/v1/stock/1/current
```

---

### 11. Consultar Stock Histórico

```
GET /v1/stock/{product_id}/at-date?date={ISO8601}
```

Calcula el stock de un producto en una fecha específica usando cálculo directo sobre la tabla de movimientos.

**Parámetros de path:**

| Parámetro | Tipo | Descripción |
|---|---|---|
| `product_id` | int | ID del producto |

**Parámetros de query:**

| Parámetro | Tipo | Requerido | Descripción |
|---|---|---|---|
| `date` | datetime | **Requerido** | Fecha de consulta (ISO 8601, timezone-aware) |

**Ejemplo de request:**

```
GET /v1/stock/1/at-date?date=2025-01-01T00:00:00Z
```

**Respuesta exitosa (200):**

```json
{
  "product_id": 1,
  "stock": 15.0,
  "date": "2025-01-01T00:00:00Z"
}
```

**Ejemplo:**

```bash
curl "http://localhost:8000/v1/stock/1/at-date?date=2025-05-20T12:00:00Z"
```

---

## Paginación

Los endpoints que listan recursos (`/products`, `/movements`) soportan paginación con los parámetros `limit` y `offset`:

- **`limit`**: Número máximo de resultados (default: 100, máximo: 1000)
- **`offset`**: Desplazamiento desde el inicio (default: 0)

La respuesta incluye `total` para calcular el número de páginas:

```json
{
  "items": [...],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

## Rate Limiting

No implementado en esta versión. Se agregará en futuras releases.
