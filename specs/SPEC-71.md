# SPEC-71: README Técnico & Demo Script & Documentación Completa

**Fase:** F7 — Despliegue & Documentación
**Dependencias:** Spec-62 (Tests E2E) ✅ Completado, Spec-70 (Dockerfile & Docker Compose Prod) ✅ Completado
**Prioridad:** Media
**Estado:** Aprobado

---

## Objective

Reescribir todos los stubs de documentación (`ARCHITECTURE.md`, `API_REFERENCE.md`, `SETUP.md`), actualizar `README.md` a v1.0.0, crear `CONTRIBUTING.md` funcional, y desarrollar `scripts/demo.sh` — un script Bash que ejercita el flujo completo del sistema contra la API local.

**Principios de diseño:**
- **Documentación como código** — los ejemplos `curl` son ejecutables contra un servidor local
- **Diagramas Mermaid embebidos** — sin herramientas externas, renderizan en GitHub/GitLab
- **Demo script robusto** — `set -euo pipefail`, `curl -sf`, falla rápido si el servidor no está disponible
- **Progressive disclosure** — README da overview; docs/ dan profundidad
- **Cero nuevas dependencias** — F7 no añade nada a `requirements.txt`
- **Error examples por endpoint** — cada endpoint muestra 1-2 errores más comunes

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| Reescribir stubs (no parchear) | Los stubs tienen 1-2 líneas. Reescribir desde cero da coherencia y calidad |
| Mermaid embebido en ARCHITECTURE.md | Renderiza nativamente en GitHub. Sin herramientas externas ni CI steps adicionales |
| Demo script en `scripts/demo.sh` | Separado del Makefile. El Makefile solo lo invoca con `make demo` |
| `DEMO_BASE_URL` env var | Consistente con el patrón `.env` del proyecto. Permite demo contra staging u otro host |
| `set -euo pipefail` en demo script | Falla rápido ante cualquier error (comando fallido, pipe roto, variable undefined) |
| `curl -sf` en demo script | `-s` silencia progreso, `-f` falla con código de error si HTTP ≥400 |
| Error examples en API_REFERENCE | Cada endpoint muestra 1-2 errores comunes (400, 404, 409, 422, 405). Más útil para consumidores |
| 9 endpoints documentados (no 10) | El sistema tiene 9 endpoints HTTP: health(1), categories(2), products(3), movements(3), stock(2) |
| CONTRIBUTING.md nuevo | Guía para contribuidores: setup, convenciones, PR process, commits |

---

## README.md Update

### Target Structure (v1.0.0)

El README sigue el patrón de **progressive disclosure**: overview → stack → commands → arquitectura → docs → estado.

**Secciones:**

1. **Header** — Título + descripción + badges (CI, coverage, Python version, license)
2. **Badges** — GitHub Actions CI status, coverage percentage, Python 3.12, MIT License
3. **Features** — Tabla de funcionalidades clave (Source of Truth Inmutable, Stock histórico <100ms, etc.)
4. **Stack Tecnológico** — Tabla de componentes (igual que v0.6.0, actualizada a v1.0.0)
5. **Comandos Principales** — Tabla con todos los `make` commands incluyendo `demo`, `docker-prod-up`, `docker-prod-down`
6. **Quick Start** — 3 pasos: `make install && make docker-prod-up && make demo`
7. **Estructura del Proyecto** — Árbol de directorios (igual que v0.6.0)
8. **Arquitectura** — Párrafo resumido + link a `docs/ARCHITECTURE.md`
9. **Documentación** — Tabla de archivos de documentación con links
10. **API Endpoints** — Tabla resumida de los 9 endpoints con método + ruta
11. **Estado Actual** — F7 completada, v1.0.0

### Badge URLs

```
[![CI](https://github.com/{user}/stock-historial/actions/workflows/ci.yml/badge.svg)](https://github.com/{user}/stock-historial/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
```

### Quick Start Section

```bash
# 1. Instalar dependencias
make install

# 2. Levantar stack de producción (app + PostgreSQL)
make docker-prod-up

# 3. Ejecutar demo completa
make demo
```

### API Endpoints Summary Table

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/v1/health` | Health check del sistema |
| POST | `/v1/categories` | Crear categoría |
| GET | `/v1/categories` | Listar categorías |
| POST | `/v1/products` | Crear producto |
| GET | `/v1/products` | Listar productos (paginado) |
| GET | `/v1/products/{id}` | Obtener producto por ID |
| POST | `/v1/movements` | Registrar movimiento |
| GET | `/v1/movements` | Listar movimientos por producto (paginado) |
| GET | `/v1/movements/{id}` | Obtener movimiento por ID |
| GET | `/v1/stock/{id}/current` | Stock actual de un producto |
| GET | `/v1/stock/{id}/at-date` | Stock histórico a una fecha |

---

## docs/ARCHITECTURE.md — Rewrite

### Target Structure

1. **Overview** — Qué es el sistema, qué problema resuelve, principios arquitectónicos
2. **Diagrama de Capas** — Mermaid: Domain → Application → Infrastructure → Adapters
3. **Capas Detalladas** — Cada capa con responsabilidades, componentes, y reglas de importación
4. **Patrones Clave** — Repository, Unit of Work, CQRS (queries via MV), Source of Truth
5. **Decisions Técnicas** — SQL explícito (no ORM), asyncpg, APScheduler, Pydantic strict
6. **Reglas de Importación** — Tabla de qué capa puede importar qué
7. **Diagrama de Datos** — Mermaid: Products → Movements → MV
8. **Diagrama de Request Flow** — Mermaid: HTTP → Router → UseCase → Repo → DB

### Diagrama de Capas (Mermaid target)

```mermaid
graph TB
    subgraph Adapters
        Routers[API Routers<br/>FastAPI /v1/*]
        Middleware[Middleware<br/>Error Handler, Request Logging]
    end

    subgraph Application
        UseCases[Use Cases<br/>CreateMovement, QueryStock]
        DTOs[DTOs<br/>Pydantic Input/Output]
    end

    subgraph Domain
        Entities[Entities<br/>Product, Movement, Category]
        VOs[Value Objects<br/>MovementType, SKU, Quantity]
        Ports[Ports<br/>IMovementRepository, IStockQueryRepo]
        Rules[Rules<br/>validate_stock_not_negative, calculate_stock_delta]
    end

    subgraph Infrastructure
        Repos[Repositories<br/>PostgresMovementRepository, PostgresStockQueryRepo]
        DB[DB Layer<br/>asyncpg Pool, Migrations, UoW]
        Scheduler[Scheduler<br/>APScheduler AsyncIOScheduler]
        Logging[Logging<br/>Structured JSON/Text]
    end

    Routers --> UseCases
    Routers --> DTOs
    Middleware --> Routers
    UseCases --> Ports
    UseCases --> Rules
    Repos -.->|implements| Ports
    Repos --> DB
    Scheduler --> DB
```

### Reglas de Importación (tabla target)

| Capa | Puede importar de | No puede importar de |
|------|-------------------|---------------------|
| Domain | Nada (solo stdlib) | Application, Infrastructure, Adapters |
| Application | Domain (ports, entities, rules, VOs) | Infrastructure, Adapters |
| Infrastructure | Domain (ports), Application (DTOs interfaces) | Adapters |
| Adapters | Application (use cases, DTOs), Domain (exceptions) | Infrastructure internals |

### Diagrama de Datos (Mermaid target)

```mermaid
erDiagram
    CATEGORIES ||--o{ PRODUCTS : has
    PRODUCTS ||--o{ MOVEMENTS : receives

    CATEGORIES {
        int id PK
        varchar name UK
        text description
        timestamptz created_at
    }

    PRODUCTS {
        int id PK
        varchar sku UK
        varchar name
        text description
        varchar unit_of_measure
        int category_id FK
        int min_stock_threshold
        timestamptz created_at
    }

    MOVEMENTS {
        int id PK
        int product_id FK
        varchar movement_type
        int quantity
        jsonb metadata
        varchar reference
        timestamptz created_at
    }
```

### Diagrama de Request Flow (Mermaid target)

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Router
    participant UC as Use Case
    participant Repo as Repository
    participant DB as PostgreSQL

    C->>R: POST /v1/movements
    R->>R: Validate with Pydantic DTO
    R->>UC: RecordMovementUseCase.execute()
    UC->>UC: validate_stock_not_negative()
    UC->>Repo: movement_repo.create()
    Repo->>DB: INSERT INTO movements
    DB-->>Repo: movement row
    Repo-->>UC: Movement entity
    UC-->>R: MovementOutput DTO
    R-->>C: 201 Created + JSON
```

---

## docs/API_REFERENCE.md — Rewrite

### Target Structure

1. **Overview** — Base URL, autenticación (ninguna), content-type, paginación
2. **Error Response Format** — Contrato `ErrorResponse` con ejemplo
3. **Endpoints** — Cada endpoint con: método, ruta, descripción, parámetros, request body, response body, códigos de error, ejemplo curl, ejemplo de error
4. **Paginación** — Explicación de `limit`/`offset`/`total`
5. **Rate Limiting** — No implementado (nota para futuro)

### Error Response Contract

Todas las respuestas de error siguen el mismo envelope:

```json
{
  "error": {
    "code": "UPPER_SNAKE_CASE",
    "message": "Human-readable description",
    "details": null
  }
}
```

### Error Codes por Endpoint

| Endpoint | Error Code | HTTP Status | Descripción |
|----------|------------|-------------|-------------|
| POST /v1/categories | `VALIDATION_ERROR` | 422 | Campo inválido o faltante |
| POST /v1/categories | `DUPLICATE_CATEGORY` | 409 | Nombre de categoría duplicado |
| POST /v1/products | `VALIDATION_ERROR` | 422 | Campo inválido o faltante |
| POST /v1/products | `DUPLICATE_SKU` | 409 | SKU duplicado |
| POST /v1/products | `CATEGORY_NOT_FOUND` | 400 | category_id no existe |
| GET /v1/products/{id} | `PRODUCT_NOT_FOUND` | 404 | Producto no encontrado |
| POST /v1/movements | `VALIDATION_ERROR` | 422 | Campo inválido o faltante |
| POST /v1/movements | `PRODUCT_NOT_FOUND` | 400 | product_id no existe |
| POST /v1/movements | `INSUFFICIENT_STOCK` | 409 | Stock insuficiente para OUT/TRANSFER |
| GET /v1/movements/{id} | `MOVEMENT_NOT_FOUND` | 404 | Movimiento no encontrado |
| GET /v1/stock/{id}/current | `PRODUCT_NOT_FOUND` | 404 | Producto no encontrado |
| GET /v1/stock/{id}/at-date | `PRODUCT_NOT_FOUND` | 404 | Producto no encontrado |
| GET /v1/stock/{id}/at-date | `VALIDATION_ERROR` | 422 | Fecha inválida |
| PUT/PATCH/DELETE /v1/movements/* | `METHOD_NOT_ALLOWED` | 405 | Movimientos son inmutables |

### Endpoint Documentation Template

Cada endpoint sigue esta estructura:

```markdown
### POST /v1/movements

Registra un nuevo movimiento de inventario. Los movimientos son **inmutables** —
una vez creados, no pueden modificarse ni eliminarse.

**Request Body:**

| Campo | Tipo | Requerido | Constraints | Descripción |
|-------|------|-----------|-------------|-------------|
| product_id | int | Sí | gt=0 | ID del producto |
| movement_type | string | Sí | IN, OUT, ADJUSTMENT, TRANSFER | Tipo de movimiento |
| quantity | int | Sí | gt=0 | Cantidad positiva |
| metadata | dict[str,str] | No | default={} | TRANSFER requiere origin/destination; ADJUSTMENT requiere reason |
| reference | string | No | max_length=255 | Referencia externa |

**Response 201:**

\`\`\`json
{
  "id": 1,
  "product_id": 1,
  "movement_type": "IN",
  "quantity": 50,
  "metadata": {},
  "reference": "PO-2026-001",
  "created_at": "2026-01-15T10:30:00Z"
}
\`\`\`

**Ejemplo curl:**

\`\`\`bash
curl -X POST http://localhost:8000/v1/movements \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "movement_type": "IN", "quantity": 50, "reference": "PO-2026-001"}'
\`\`\`

**Error 409 — Stock insuficiente:**

\`\`\`json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Insufficient stock for product 1: current=5, requested=50",
    "details": {"current_stock": 5, "requested": 50}
  }
}
\`\`\`

**Error 422 — Campo faltante:**

\`\`\`json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field required",
    "details": {"field": "product_id"}
  }
}
\`\`\`
```

### All 9 Endpoints to Document

| # | Method | Route | Section Title |
|---|--------|-------|---------------|
| 1 | GET | `/v1/health` | Health Check |
| 2 | POST | `/v1/categories` | Crear Categoría |
| 3 | GET | `/v1/categories` | Listar Categorías |
| 4 | POST | `/v1/products` | Crear Producto |
| 5 | GET | `/v1/products` | Listar Productos |
| 6 | GET | `/v1/products/{product_id}` | Obtener Producto |
| 7 | POST | `/v1/movements` | Registrar Movimiento |
| 8 | GET | `/v1/movements` | Listar Movimientos |
| 9 | GET | `/v1/movements/{movement_id}` | Obtener Movimiento |
| 10 | GET | `/v1/stock/{product_id}/current` | Stock Actual |
| 11 | GET | `/v1/stock/{product_id}/at-date` | Stock Histórico |

> **Nota:** Son 11 rutas (el SPEC.md original mencionaba 10, pero el inventario real es 11 contando `/v1/health`). Se documentan todas.

---

## docs/SETUP.md — Rewrite

### Target Structure

1. **Prerequisitos** — Python 3.12+, PostgreSQL 16+, Docker, Git
2. **Instalación** — `make install`, `.env` setup
3. **Desarrollo Local** — `make dev`, PostgreSQL via Docker o local
4. **Docker Dev** — `make docker-up`, hot reload, debug
5. **Docker Prod** — `make docker-prod-up`, `.env` de producción, healthchecks
6. **Demo** — `make demo`, `DEMO_BASE_URL`
7. **Variables de Entorno** — Tabla completa de todas las variables (F0-F7)
8. **Troubleshooting** — Problemas comunes y soluciones
9. **Migraciones** — `make migrate`, `make seed`

### Variables de Entorno Table

| Variable | Default | Descripción | Desde |
|----------|---------|-------------|-------|
| `APP_NAME` | `Stock Historial` | Nombre de la app para logs | F0 |
| `APP_HOST` | `0.0.0.0` | Interfaz de red (0.0.0.0 para Docker) | F0 |
| `APP_PORT` | `8000` | Puerto de escucha HTTP | F0 |
| `LOG_LEVEL` | `info` | Nivel de logging (debug/info/warning/error) | F0 |
| `ENVIRONMENT` | `development` | Entorno de ejecución | F0 |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/stock_historial` | DSN asyncpg | F1 |
| `LOG_FORMAT` | `text` | Formato de logs (text/json) | F5 |
| `SCHEDULER_ENABLED` | `true` | Habilitar/deshabilitar scheduler | F5 |
| `SCHEDULER_REFRESH_INTERVAL_MINUTES` | `5` | Intervalo entre refreshes de MV | F5 |
| `SCHEDULER_MISFIRE_GRACE_TIME_SECONDS` | `60` | Tolerancia para jobs retrasados | F5 |
| `SCHEDULER_STATEMENT_TIMEOUT_SECONDS` | `30` | Timeout para refresh job | F5 |
| `API_STATEMENT_TIMEOUT_SECONDS` | `5` | Timeout para queries de API | F5 |
| `POSTGRES_USER` | `stock_user` | Usuario PostgreSQL (prod) | F7 |
| `POSTGRES_PASSWORD` | (requerido) | Contraseña PostgreSQL (prod) | F7 |
| `POSTGRES_DB` | `stock_historial` | Base de datos PostgreSQL (prod) | F7 |
| `DEMO_BASE_URL` | `http://localhost:8000` | URL base para demo script | F7 |

### Troubleshooting Section

| Problema | Solución |
|----------|----------|
| `psycopg` o connection refused | Verificar que PostgreSQL está corriendo: `docker compose ps` |
| `make demo` falla con connection refused | Verificar que el servidor está levantado: `curl http://localhost:8000/v1/health` |
| `docker compose up` falla con port in use | Detener servicios previos: `make docker-down` o `make docker-prod-down` |
| Migraciones pendientes | Ejecutar: `make migrate` |
| Coverage baja | Ejecutar: `make test-cov` y revisar líneas sin cubrir |
| `mypy` falla | Ejecutar: `make typecheck` y revisar errores |

---

## scripts/demo.sh

### NEW FILE: `scripts/demo.sh`

Script de demostración que ejercita el flujo completo del sistema:

1. **Health check** — verificar que el servidor está vivo
2. **Crear categoría** — POST `/v1/categories`
3. **Crear producto** — POST `/v1/products`
4. **Registrar entrada (IN)** — POST `/v1/movements` con `movement_type=IN`
5. **Consultar stock actual** — GET `/v1/stock/{id}/current`
6. **Registrar salida (OUT)** — POST `/v1/movements` con `movement_type=OUT`
7. **Consultar stock actualizado** — GET `/v1/stock/{id}/current` (verificar stock reducido)
8. **Consultar stock histórico** — GET `/v1/stock/{id}/at-date`
9. **Listar movimientos** — GET `/v1/movements?product_id={id}`
10. **Mensaje de éxito**

### Contract

```bash
#!/usr/bin/env bash
# scripts/demo.sh — Demo script del sistema Stock Historial
# Ejecuta el flujo completo: health → categoría → producto → IN → stock → OUT → stock → histórico → movimientos
#
# Uso: make demo
# Con URL custom: DEMO_BASE_URL=http://staging:8000 make demo
# Prerequisitos: servidor corriendo en localhost:8000

set -euo pipefail

BASE_URL="${DEMO_BASE_URL:-http://localhost:8000}"
HEALTH_URL="${BASE_URL}/v1/health"

# 1. Verificar que el servidor está vivo
echo "🔍 Verificando salud del servidor..."
curl -sf "${HEALTH_URL}" | python3 -m json.tool

# 2. Crear categoría
echo "\n📦 Creando categoría 'Electrónica'..."
CATEGORY=$(curl -sf -X POST "${BASE_URL}/v1/categories" \
  -H "Content-Type: application/json" \
  -d '{"name": "Electrónica", "description": "Dispositivos electrónicos"}')
echo "$CATEGORY" | python3 -m json.tool
CATEGORY_ID=$(echo "$CATEGORY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. Crear producto
echo "\n📱 Creando producto 'Monitor 27 4K'..."
PRODUCT=$(curl -sf -X POST "${BASE_URL}/v1/products" \
  -H "Content-Type: application/json" \
  -d "{
    \"sku\": \"MON-27-4K\",
    \"name\": \"Monitor 27 4K\",
    \"description\": \"Monitor IPS 4K 27 pulgadas\",
    \"unit_of_measure\": \"unit\",
    \"category_id\": ${CATEGORY_ID},
    \"min_stock_threshold\": 5
  }")
echo "$PRODUCT" | python3 -m json.tool
PRODUCT_ID=$(echo "$PRODUCT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 4. Registrar entrada de stock
echo "\n📥 Registrando IN de 50 unidades..."
MOVEMENT=$(curl -sf -X POST "${BASE_URL}/v1/movements" \
  -H "Content-Type: application/json" \
  -d "{
    \"product_id\": ${PRODUCT_ID},
    \"movement_type\": \"IN\",
    \"quantity\": 50,
    \"reference\": \"PO-2026-001\"
  }")
echo "$MOVEMENT" | python3 -m json.tool

# 5. Consultar stock actual
echo "\n📊 Consultando stock actual..."
STOCK=$(curl -sf "${BASE_URL}/v1/stock/${PRODUCT_ID}/current")
echo "$STOCK" | python3 -m json.tool

# 6. Registrar salida
echo "\n📤 Registrando OUT de 10 unidades..."
OUT=$(curl -sf -X POST "${BASE_URL}/v1/movements" \
  -H "Content-Type: application/json" \
  -d "{
    \"product_id\": ${PRODUCT_ID},
    \"movement_type\": \"OUT\",
    \"quantity\": 10,
    \"reference\": \"SO-2026-001\"
  }")
echo "$OUT" | python3 -m json.tool

# 7. Consultar stock actualizado
echo "\n📊 Stock después de la salida..."
STOCK2=$(curl -sf "${BASE_URL}/v1/stock/${PRODUCT_ID}/current")
echo "$STOCK2" | python3 -m json.tool

# 8. Consultar stock histórico
echo "\n📅 Consultando stock histórico..."
STOCK_DATE=$(curl -sf "${BASE_URL}/v1/stock/${PRODUCT_ID}/at-date?date=2026-01-01T00:00:00Z")
echo "$STOCK_DATE" | python3 -m json.tool

# 9. Listar movimientos del producto
echo "\n📋 Listando movimientos del producto..."
MOVEMENTS=$(curl -sf "${BASE_URL}/v1/movements?product_id=${PRODUCT_ID}&limit=10")
echo "$MOVEMENTS" | python3 -m json.tool

echo "\n✅ Demo completada exitosamente!"
```

### Demo Script Validation

| Validación | Comando | Criterio |
|------------|---------|----------|
| Script ejecuta sin errores | `make demo` (con servidor levantado) | Exit code 0 |
| Stock after IN = 50 | Verificar output del step 5 | `current_stock: 50.0` |
| Stock after OUT = 40 | Verificar output del step 7 | `current_stock: 40.0` |
| Servidor no disponible | `DEMO_BASE_URL=http://invalid make demo` | Exit code ≠ 0 (curl -sf falla) |

---

## CONTRIBUTING.md

### NEW FILE: `CONTRIBUTING.md`

Guía para contribuidores del proyecto:

1. **Setup** — Prerequisitos y primer setup (link a `docs/SETUP.md`)
2. **Flujo de Trabajo** — Fork → Branch → Commit → PR
3. **Convenciones de Commits** — Formato: `type(scope): description`
4. **Calidad** — `make build` (lint + format + test) antes de commit
5. **Type Checking** — `make typecheck` (mypy strict) debe pasar
6. **Cobertura** — No reducir cobertura existente
7. **Arquitectura** — Respetar reglas de importación (ver `docs/ARCHITECTURE.md`)
8. **Testing** — Escribir tests para todo código nuevo
9. **Commits** — Commits atómicos, mensajes descriptivos
10. **PR** — Descripción clara, referencia a specs

### Commit Convention

```
type(scope): description

Types: feat, fix, docs, style, refactor, test, chore, ci
Scopes: domain, application, infrastructure, adapters, db, scheduler, docs, ci
```

---

## Files

| File | Description | Action |
|------|-------------|--------|
| `README.md` | Actualizar a v1.0.0: badges, features, quick start, API table | MODIFY |
| `docs/ARCHITECTURE.md` | Reescribir: Clean Architecture, diagramas Mermaid, reglas de importación, decisiones técnicas | REWRITE |
| `docs/API_REFERENCE.md` | Reescribir: 11 endpoints con parámetros, ejemplos curl, errores | REWRITE |
| `docs/SETUP.md` | Reescribir: prereqs → install → dev → prod → demo → variables → troubleshooting | REWRITE |
| `scripts/demo.sh` | Demo script: flujo completo curl contra API | NEW |
| `CONTRIBUTING.md` | Guía de contribución: setup, convenciones, PR process | NEW |
| `Makefile` | +demo command (ya cubierto en Spec-70) | MODIFY (coordinated) |

---

## Acceptance Criteria

- [ ] `README.md` actualizado a v1.0.0 con badges, tabla de features, quick start, API endpoints summary
- [ ] `docs/ARCHITECTURE.md` documenta: Clean Architecture con diagrama Mermaid de capas, reglas de importación (tabla), diagrama de datos (ER), diagrama de request flow (sequence), patrones (Repository, UoW, CQRS, MV), decisiones técnicas (SQL explícito, asyncpg, APScheduler, Pydantic strict)
- [ ] `docs/API_REFERENCE.md` documenta: 11 endpoints con método, ruta, descripción, parámetros, request/response body, códigos de error, ejemplos `curl` ejecutables, y al menos 1 ejemplo de error por endpoint
- [ ] `docs/SETUP.md` documenta: prerequisitos, instalación, desarrollo local, Docker dev, Docker prod, demo, tabla de variables de entorno (16 variables F0-F7), troubleshooting
- [ ] `scripts/demo.sh` ejecuta flujo completo: health → categoría → producto → IN → stock → OUT → stock → histórico → movimientos
- [ ] Demo script soporta `DEMO_BASE_URL` env var (default `http://localhost:8000`)
- [ ] `make demo` ejecuta `bash scripts/demo.sh`
- [ ] Demo script usa `set -euo pipefail` y falla si el servidor no está disponible
- [ ] Demo script muestra output formateado con `python3 -m json.tool`
- [ ] `CONTRIBUTING.md` documenta: setup, convenciones de commits, calidad, arquitectura, testing
- [ ] Todos los ejemplos `curl` en `API_REFERENCE.md` son ejecutables contra un servidor local
- [ ] `make lint` pasa sin errores
- [ ] 0 regresiones en tests existentes (205+ tests)

---

## Testing Strategy

F7 no añade tests unitarios ni de integración. La validación es manual:

| Validación | Comando | Criterio |
|------------|---------|----------|
| Demo script | `make demo` (con servidor levantado) | Exit code 0, output formateado |
| Demo con URL custom | `DEMO_BASE_URL=http://localhost:8000 make demo` | Exit code 0 |
| Demo falla sin servidor | `DEMO_BASE_URL=http://invalid:9999 make demo` | Exit code ≠ 0 |
| Links internos | Verificar que todos los links en README/docs apuntan a archivos existentes | Sin 404s |
| Mermaid rendering | Abrir ARCHITECTURE.md en GitHub | Diagramas renderizan correctamente |
| curl examples | Ejecutar cada ejemplo curl de API_REFERENCE | Respuestas esperadas |

---

## Resolved Questions

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| F7-71-Q1 | ¿Número de endpoints? | **11** (no 10) | El inventario real es 11 rutas: health(1), categories(2), products(3), movements(3), stock(2) |
| F7-71-Q2 | ¿Ejemplos de error en API_REFERENCE? | **Sí, 1-2 por endpoint** | Cada endpoint muestra los errores más comunes (400, 404, 409, 422, 405). Más útil para consumidores de la API |
| F7-71-Q3 | ¿Demo script con validación de stock? | **Sí** | El script verifica que el stock después de IN=50 y OUT=10 es 40. Validación implícita en el output |
| F7-71-Q4 | ¿CONTRIBUTING.md? | **Sí, nuevo** | Guía para contribuidores. Incluye setup, convenciones, PR process, commits |
| F7-71-Q5 | ¿Badges en README? | **Sí: CI, coverage, Python, license** | Badges dan visibilidad inmediata del estado del proyecto |
| F7-71-Q6 | ¿Quick Start en README? | **Sí, 3 pasos** | `make install && make docker-prod-up && make demo` — mínimo friction para empezar |
| F7-71-Q7 | ¿Diagramas Mermaid en ARCHITECTURE? | **Sí: capas, ER, sequence** | 3 diagramas cubren las vistas principales: estructura, datos, flujo |
