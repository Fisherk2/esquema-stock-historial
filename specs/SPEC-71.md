# SPEC-71: Technical README & Demo Script & Complete Documentation

**Phase:** F7 — Deployment & Documentation
**Dependencies:** Spec-62 (E2E Tests) ✅ Completed, Spec-70 (Dockerfile & Docker Compose Prod) ✅ Completed
**Priority:** Medium
**Status:** Approved

---

## Objective

Rewrite all documentation stubs (`ARCHITECTURE.md`, `API_REFERENCE.md`, `SETUP.md`), update `README.md` to v1.0.0, create a functional `CONTRIBUTING.md`, and develop `scripts/demo.sh` — a Bash script that exercises the complete system flow against the local API.

**Design principles:**
- **Documentation as code** — `curl` examples are executable against a local server
- **Embedded Mermaid diagrams** — no external tools, render in GitHub/GitLab
- **Robust demo script** — `set -euo pipefail`, `curl -sf`, fails fast if server is unavailable
- **Progressive disclosure** — README gives overview; docs/ provide depth
- **Zero new dependencies** — F7 adds nothing to `requirements.txt`
- **Error examples per endpoint** — each endpoint shows 1-2 most common errors

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| Rewrite stubs (not patch) | Stubs are 1-2 lines. Rewriting from scratch gives coherence and quality |
| Mermaid embedded in ARCHITECTURE.md | Renders natively in GitHub. No external tools or additional CI steps |
| Demo script in `scripts/demo.sh` | Separated from Makefile. Makefile only invokes it with `make demo` |
| `DEMO_BASE_URL` env var | Consistent with project's `.env` pattern. Allows demo against staging or another host |
| `set -euo pipefail` in demo script | Fails fast on any error (failed command, broken pipe, undefined variable) |
| `curl -sf` in demo script | `-s` silences progress, `-f` fails with error code if HTTP ≥400 |
| Error examples in API_REFERENCE | Each endpoint shows 1-2 common errors (400, 404, 409, 422, 405). More useful for consumers |
| 9 documented endpoints (not 10) | The system has 9 HTTP endpoints: health(1), categories(2), products(3), movements(3), stock(2) |
| New CONTRIBUTING.md | Guide for contributors: setup, conventions, PR process, commits |

---

## README.md Update

### Target Structure (v1.0.0)

The README follows the **progressive disclosure** pattern: overview → stack → commands → architecture → docs → status.

**Sections:**

1. **Header** — Title + description + badges (CI, coverage, Python version, license)
2. **Badges** — GitHub Actions CI status, coverage percentage, Python 3.12, MIT License
3. **Features** — Table of key features (Immutable Source of Truth, Historical stock <100ms, etc.)
4. **Technology Stack** — Component table (same as v0.6.0, updated to v1.0.0)
5. **Main Commands** — Table with all `make` commands including `demo`, `docker-prod-up`, `docker-prod-down`
6. **Quick Start** — 3 steps: `make install && make docker-prod-up && make demo`
7. **Project Structure** — Directory tree (same as v0.6.0)
8. **Architecture** — Summary paragraph + link to `docs/ARCHITECTURE.md`
9. **Documentation** — Table of documentation files with links
10. **API Endpoints** — Summary table of the 9 endpoints with method + route
11. **Current Status** — F7 completed, v1.0.0

### Badge URLs

```
[![CI](https://github.com/Fisherk2/esquema-stock-historial/actions/workflows/ci.yml/badge.svg)](https://github.com/Fisherk2/esquema-stock-historial/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
```

### Quick Start Section

```bash
# 1. Install dependencies
make install

# 2. Start production stack (app + PostgreSQL)
make docker-prod-up

# 3. Run complete demo
make demo
```

### API Endpoints Summary Table

| Method | Route | Description |
|--------|------|-------------|
| GET | `/v1/health` | System health check |
| POST | `/v1/categories` | Create category |
| GET | `/v1/categories` | List categories |
| POST | `/v1/products` | Create product |
| GET | `/v1/products` | List products (paginated) |
| GET | `/v1/products/{id}` | Get product by ID |
| POST | `/v1/movements` | Register movement |
| GET | `/v1/movements` | List movements by product (paginated) |
| GET | `/v1/movements/{id}` | Get movement by ID |
| GET | `/v1/stock/{id}/current` | Current stock for a product |
| GET | `/v1/stock/{id}/at-date` | Historical stock at a date |

---

## docs/ARCHITECTURE.md — Rewrite

### Target Structure

1. **Overview** — What the system is, what problem it solves, architectural principles
2. **Layer Diagram** — Mermaid: Domain → Application → Infrastructure → Adapters
3. **Detailed Layers** — Each layer with responsibilities, components, and import rules
4. **Key Patterns** — Repository, Unit of Work, CQRS (queries via MV), Source of Truth
5. **Technical Decisions** — Explicit SQL (no ORM), asyncpg, APScheduler, Pydantic strict
6. **Import Rules** — Table of which layer can import from which
7. **Data Diagram** — Mermaid: Products → Movements → MV
8. **Request Flow Diagram** — Mermaid: HTTP → Router → UseCase → Repo → DB

### Layer Diagram (Mermaid target)

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

### Import Rules (target table)

| Layer | Can import from | Cannot import from |
|------|-------------------|---------------------|
| Domain | Nothing (only stdlib) | Application, Infrastructure, Adapters |
| Application | Domain (ports, entities, rules, VOs) | Infrastructure, Adapters |
| Infrastructure | Domain (ports), Application (DTOs interfaces) | Adapters |
| Adapters | Application (use cases, DTOs), Domain (exceptions) | Infrastructure internals |

### Data Diagram (Mermaid target)

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

### Request Flow Diagram (Mermaid target)

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

1. **Overview** — Base URL, authentication (none), content-type, pagination
2. **Error Response Format** — `ErrorResponse` contract with example
3. **Endpoints** — Each endpoint with: method, route, description, parameters, request body, response body, error codes, curl example, error example
4. **Pagination** — Explanation of `limit`/`offset`/`total`
5. **Rate Limiting** — Not implemented (note for future)

### Error Response Contract

All error responses follow the same envelope:

```json
{
  "error": {
    "code": "UPPER_SNAKE_CASE",
    "message": "Human-readable description",
    "details": null
  }
}
```

### Error Codes per Endpoint

| Endpoint | Error Code | HTTP Status | Description |
|----------|------------|-------------|-------------|
| POST /v1/categories | `VALIDATION_ERROR` | 422 | Invalid or missing field |
| POST /v1/categories | `DUPLICATE_CATEGORY` | 409 | Duplicate category name |
| POST /v1/products | `VALIDATION_ERROR` | 422 | Invalid or missing field |
| POST /v1/products | `DUPLICATE_SKU` | 409 | Duplicate SKU |
| POST /v1/products | `CATEGORY_NOT_FOUND` | 400 | category_id does not exist |
| GET /v1/products/{id} | `PRODUCT_NOT_FOUND` | 404 | Product not found |
| POST /v1/movements | `VALIDATION_ERROR` | 422 | Invalid or missing field |
| POST /v1/movements | `PRODUCT_NOT_FOUND` | 400 | product_id does not exist |
| POST /v1/movements | `INSUFFICIENT_STOCK` | 409 | Insufficient stock for OUT/TRANSFER |
| GET /v1/movements/{id} | `MOVEMENT_NOT_FOUND` | 404 | Movement not found |
| GET /v1/stock/{id}/current | `PRODUCT_NOT_FOUND` | 404 | Product not found |
| GET /v1/stock/{id}/at-date | `PRODUCT_NOT_FOUND` | 404 | Product not found |
| GET /v1/stock/{id}/at-date | `VALIDATION_ERROR` | 422 | Invalid date |
| PUT/PATCH/DELETE /v1/movements/* | `METHOD_NOT_ALLOWED` | 405 | Movements are immutable |

### Endpoint Documentation Template

Each endpoint follows this structure:

```markdown
### POST /v1/movements

Registers a new inventory movement. Movements are **immutable** —
once created, they cannot be modified or deleted.

**Request Body:**

| Field | Type | Required | Constraints | Description |
|-------|------|-----------|-------------|-------------|
| product_id | int | Yes | gt=0 | Product ID |
| movement_type | string | Yes | IN, OUT, ADJUSTMENT, TRANSFER | Movement type |
| quantity | int | Yes | gt=0 | Positive quantity |
| metadata | dict[str,str] | No | default={} | TRANSFER requires origin/destination; ADJUSTMENT requires reason |
| reference | string | No | max_length=255 | External reference |

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

**curl Example:**

\`\`\`bash
curl -X POST http://localhost:8000/v1/movements \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "movement_type": "IN", "quantity": 50, "reference": "PO-2026-001"}'
\`\`\`

**Error 409 — Insufficient stock:**

\`\`\`json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Insufficient stock for product 1: current=5, requested=50",
    "details": {"current_stock": 5, "requested": 50}
  }
}
\`\`\`

**Error 422 — Missing field:**

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
| 2 | POST | `/v1/categories` | Create Category |
| 3 | GET | `/v1/categories` | List Categories |
| 4 | POST | `/v1/products` | Create Product |
| 5 | GET | `/v1/products` | List Products |
| 6 | GET | `/v1/products/{product_id}` | Get Product |
| 7 | POST | `/v1/movements` | Register Movement |
| 8 | GET | `/v1/movements` | List Movements |
| 9 | GET | `/v1/movements/{movement_id}` | Get Movement |
| 10 | GET | `/v1/stock/{product_id}/current` | Current Stock |
| 11 | GET | `/v1/stock/{product_id}/at-date` | Historical Stock |

> **Note:** There are 11 routes (the original SPEC.md mentioned 10, but the actual inventory is 11 counting `/v1/health`). All are documented.

---

## docs/SETUP.md — Rewrite

### Target Structure

1. **Prerequisites** — Python 3.12+, PostgreSQL 16+, Docker, Git
2. **Installation** — `make install`, `.env` setup
3. **Local Development** — `make dev`, PostgreSQL via Docker or local
4. **Docker Dev** — `make docker-up`, hot reload, debug
5. **Docker Prod** — `make docker-prod-up`, production `.env`, healthchecks
6. **Demo** — `make demo`, `DEMO_BASE_URL`
7. **Environment Variables** — Complete table of all variables (F0-F7)
8. **Troubleshooting** — Common problems and solutions
9. **Migrations** — `make migrate`, `make seed`

### Environment Variables Table

| Variable | Default | Description | Since |
|----------|---------|-------------|-------|
| `APP_NAME` | `Stock Historial` | App name for logs | F0 |
| `APP_HOST` | `0.0.0.0` | Network interface (0.0.0.0 for Docker) | F0 |
| `APP_PORT` | `8000` | HTTP listening port | F0 |
| `LOG_LEVEL` | `info` | Logging level (debug/info/warning/error) | F0 |
| `ENVIRONMENT` | `development` | Runtime environment | F0 |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/stock_historial` | asyncpg DSN | F1 |
| `LOG_FORMAT` | `text` | Log format (text/json) | F5 |
| `SCHEDULER_ENABLED` | `true` | Enable/disable scheduler | F5 |
| `SCHEDULER_REFRESH_INTERVAL_MINUTES` | `5` | Interval between MV refreshes | F5 |
| `SCHEDULER_MISFIRE_GRACE_TIME_SECONDS` | `60` | Tolerance for delayed jobs | F5 |
| `SCHEDULER_STATEMENT_TIMEOUT_SECONDS` | `30` | Timeout for refresh job | F5 |
| `API_STATEMENT_TIMEOUT_SECONDS` | `5` | Timeout for API queries | F5 |
| `POSTGRES_USER` | `stock_user` | PostgreSQL user (prod) | F7 |
| `POSTGRES_PASSWORD` | (required) | PostgreSQL password (prod) | F7 |
| `POSTGRES_DB` | `stock_historial` | PostgreSQL database (prod) | F7 |
| `DEMO_BASE_URL` | `http://localhost:8000` | Base URL for demo script | F7 |

### Troubleshooting Section

| Problem | Solution |
|----------|----------|
| `psycopg` or connection refused | Verify PostgreSQL is running: `docker compose ps` |
| `make demo` fails with connection refused | Verify server is up: `curl http://localhost:8000/v1/health` |
| `docker compose up` fails with port in use | Stop previous services: `make docker-down` or `make docker-prod-down` |
| Pending migrations | Run: `make migrate` |
| Low coverage | Run: `make test-cov` and review uncovered lines |
| `mypy` fails | Run: `make typecheck` and review errors |

---

## scripts/demo.sh

### NEW FILE: `scripts/demo.sh`

Demonstration script that exercises the complete system flow:

1. **Health check** — verify server is alive
2. **Create category** — POST `/v1/categories`
3. **Create product** — POST `/v1/products`
4. **Register entry (IN)** — POST `/v1/movements` with `movement_type=IN`
5. **Query current stock** — GET `/v1/stock/{id}/current`
6. **Register exit (OUT)** — POST `/v1/movements` with `movement_type=OUT`
7. **Query updated stock** — GET `/v1/stock/{id}/current` (verify reduced stock)
8. **Query historical stock** — GET `/v1/stock/{id}/at-date`
9. **List movements** — GET `/v1/movements?product_id={id}`
10. **Success message**

### Contract

```bash
#!/usr/bin/env bash
# scripts/demo.sh — Stock Historial system demo script
# Runs the complete flow: health → category → product → IN → stock → OUT → stock → historical → movements
#
# Usage: make demo
# With custom URL: DEMO_BASE_URL=http://staging:8000 make demo
# Prerequisites: server running on localhost:8000

set -euo pipefail

BASE_URL="${DEMO_BASE_URL:-http://localhost:8000}"
HEALTH_URL="${BASE_URL}/v1/health"

# 1. Verify server is alive
echo "🔍 Checking server health..."
curl -sf "${HEALTH_URL}" | python3 -m json.tool

# 2. Create category
echo "\n📦 Creating category 'Electronics'..."
CATEGORY=$(curl -sf -X POST "${BASE_URL}/v1/categories" \
  -H "Content-Type: application/json" \
  -d '{"name": "Electronics", "description": "Electronic devices"}')
echo "$CATEGORY" | python3 -m json.tool
CATEGORY_ID=$(echo "$CATEGORY" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. Create product
echo "\n📱 Creating product '27 4K Monitor'..."
PRODUCT=$(curl -sf -X POST "${BASE_URL}/v1/products" \
  -H "Content-Type: application/json" \
  -d "{
    \"sku\": \"MON-27-4K\",
    \"name\": \"27 4K Monitor\",
    \"description\": \"27 inch IPS 4K Monitor\",
    \"unit_of_measure\": \"unit\",
    \"category_id\": ${CATEGORY_ID},
    \"min_stock_threshold\": 5
  }")
echo "$PRODUCT" | python3 -m json.tool
PRODUCT_ID=$(echo "$PRODUCT" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 4. Register stock entry
echo "\n📥 Registering IN of 50 units..."
MOVEMENT=$(curl -sf -X POST "${BASE_URL}/v1/movements" \
  -H "Content-Type: application/json" \
  -d "{
    \"product_id\": ${PRODUCT_ID},
    \"movement_type\": \"IN\",
    \"quantity\": 50,
    \"reference\": \"PO-2026-001\"
  }")
echo "$MOVEMENT" | python3 -m json.tool

# 5. Query current stock
echo "\n📊 Querying current stock..."
STOCK=$(curl -sf "${BASE_URL}/v1/stock/${PRODUCT_ID}/current")
echo "$STOCK" | python3 -m json.tool

# 6. Register exit
echo "\n📤 Registering OUT of 10 units..."
OUT=$(curl -sf -X POST "${BASE_URL}/v1/movements" \
  -H "Content-Type: application/json" \
  -d "{
    \"product_id\": ${PRODUCT_ID},
    \"movement_type\": \"OUT\",
    \"quantity\": 10,
    \"reference\": \"SO-2026-001\"
  }")
echo "$OUT" | python3 -m json.tool

# 7. Query updated stock
echo "\n📊 Stock after exit..."
STOCK2=$(curl -sf "${BASE_URL}/v1/stock/${PRODUCT_ID}/current")
echo "$STOCK2" | python3 -m json.tool

# 8. Query historical stock
echo "\n📅 Querying historical stock..."
STOCK_DATE=$(curl -sf "${BASE_URL}/v1/stock/${PRODUCT_ID}/at-date?date=2026-01-01T00:00:00Z")
echo "$STOCK_DATE" | python3 -m json.tool

# 9. List product movements
echo "\n📋 Listing product movements..."
MOVEMENTS=$(curl -sf "${BASE_URL}/v1/movements?product_id=${PRODUCT_ID}&limit=10")
echo "$MOVEMENTS" | python3 -m json.tool

echo "\n✅ Demo completed successfully!"
```

### Demo Script Validation

| Validation | Command | Criteria |
|------------|---------|----------|
| Script runs without errors | `make demo` (with server up) | Exit code 0 |
| Stock after IN = 50 | Verify step 5 output | `current_stock: 50.0` |
| Stock after OUT = 40 | Verify step 7 output | `current_stock: 40.0` |
| Server unavailable | `DEMO_BASE_URL=http://invalid make demo` | Exit code ≠ 0 (curl -sf fails) |

---

## CONTRIBUTING.md

### NEW FILE: `CONTRIBUTING.md`

Guide for project contributors:

1. **Setup** — Prerequisites and initial setup (link to `docs/SETUP.md`)
2. **Workflow** — Fork → Branch → Commit → PR
3. **Commit Conventions** — Format: `type(scope): description`
4. **Quality** — `make build` (lint + format + test) before commit
5. **Type Checking** — `make typecheck` (mypy strict) must pass
6. **Coverage** — Do not reduce existing coverage
7. **Architecture** — Respect import rules (see `docs/ARCHITECTURE.md`)
8. **Testing** — Write tests for all new code
9. **Commits** — Atomic commits, descriptive messages
10. **PR** — Clear description, reference to specs

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
| `README.md` | Update to v1.0.0: badges, features, quick start, API table | MODIFY |
| `docs/ARCHITECTURE.md` | Rewrite: Clean Architecture, Mermaid diagrams, import rules, technical decisions | REWRITE |
| `docs/API_REFERENCE.md` | Rewrite: 11 endpoints with parameters, curl examples, errors | REWRITE |
| `docs/SETUP.md` | Rewrite: prereqs → install → dev → prod → demo → variables → troubleshooting | REWRITE |
| `scripts/demo.sh` | Demo script: complete curl flow against API | NEW |
| `CONTRIBUTING.md` | Contribution guide: setup, conventions, PR process | NEW |
| `Makefile` | +demo command (already covered in Spec-70) | MODIFY (coordinated) |

---

## Acceptance Criteria

- [ ] `README.md` updated to v1.0.0 with badges, features table, quick start, API endpoints summary
- [ ] `docs/ARCHITECTURE.md` documents: Clean Architecture with Mermaid layer diagram, import rules (table), data diagram (ER), request flow diagram (sequence), patterns (Repository, UoW, CQRS, MV), technical decisions (explicit SQL, asyncpg, APScheduler, Pydantic strict)
- [ ] `docs/API_REFERENCE.md` documents: 11 endpoints with method, route, description, parameters, request/response body, error codes, executable `curl` examples, and at least 1 error example per endpoint
- [ ] `docs/SETUP.md` documents: prerequisites, installation, local development, Docker dev, Docker prod, demo, environment variables table (16 variables F0-F7), troubleshooting
- [ ] `scripts/demo.sh` executes complete flow: health → category → product → IN → stock → OUT → stock → historical → movements
- [ ] Demo script supports `DEMO_BASE_URL` env var (default `http://localhost:8000`)
- [ ] `make demo` runs `bash scripts/demo.sh`
- [ ] Demo script uses `set -euo pipefail` and fails if server is unavailable
- [ ] Demo script shows formatted output with `python3 -m json.tool`
- [ ] `CONTRIBUTING.md` documents: setup, commit conventions, quality, architecture, testing
- [ ] All `curl` examples in `API_REFERENCE.md` are executable against a local server
- [ ] `make lint` passes without errors
- [ ] 0 regressions in existing tests (205+ tests)

---

## Testing Strategy

F7 does not add unit or integration tests. Validation is manual:

| Validation | Command | Criteria |
|------------|---------|----------|
| Demo script | `make demo` (with server up) | Exit code 0, formatted output |
| Demo with custom URL | `DEMO_BASE_URL=http://localhost:8000 make demo` | Exit code 0 |
| Demo fails without server | `DEMO_BASE_URL=http://invalid:9999 make demo` | Exit code ≠ 0 |
| Internal links | Verify all links in README/docs point to existing files | No 404s |
| Mermaid rendering | Open ARCHITECTURE.md in GitHub | Diagrams render correctly |
| curl examples | Execute each curl example from API_REFERENCE | Expected responses |

---

## Resolved Questions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| F7-71-Q1 | Number of endpoints? | **11** (not 10) | The actual inventory is 11 routes: health(1), categories(2), products(3), movements(3), stock(2) |
| F7-71-Q2 | Error examples in API_REFERENCE? | **Yes, 1-2 per endpoint** | Each endpoint shows the most common errors (400, 404, 409, 422, 405). More useful for API consumers |
| F7-71-Q3 | Demo script with stock validation? | **Yes** | The script verifies that stock after IN=50 and OUT=10 is 40. Implicit validation in the output |
| F7-71-Q4 | CONTRIBUTING.md? | **Yes, new** | Guide for contributors. Includes setup, conventions, PR process, commits |
| F7-71-Q5 | Badges in README? | **Yes: CI, coverage, Python, license** | Badges give immediate visibility of project status |
| F7-71-Q6 | Quick Start in README? | **Yes, 3 steps** | `make install && make docker-prod-up && make demo` — minimum friction to get started |
| F7-71-Q7 | Mermaid diagrams in ARCHITECTURE? | **Yes: layers, ER, sequence** | 3 diagrams cover the main views: structure, data, flow |
