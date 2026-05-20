# Implementation Plan: F7 — Despliegue & Documentación

## Overview

F7 completes the project with production-ready Docker infrastructure, comprehensive documentation, and a 5-gate CI/CD pipeline. It takes the system from v0.6.0 (testing complete) to v1.0.0 (production-ready). Three specs define the work: **SPEC-70** (Dockerfile hardening + docker-compose.prod.yml + .dockerignore + .env.example + Makefile), **SPEC-71** (README v1.0.0 + ARCHITECTURE.md rewrite + API_REFERENCE.md rewrite + SETUP.md rewrite + demo.sh + CONTRIBUTING.md), and **SPEC-72** (CI/CD 5-gate pipeline rewrite). F7 adds zero new dependencies and zero new Python tests — all validation is infrastructure-level.

**What's done (baseline from F0–F6):**
- 205+ tests passing (unit + integration + e2e + security), `make lint` clean, `make typecheck` clean
- Domain: entities, value objects, rules, ports (F2)
- Infrastructure: asyncpg repos, MV with concurrent refresh + fallback, UoW (F3)
- API: 6 use cases, 5 DTOs, 5 routers (11 HTTP endpoints), error mapping (F4)
- Scheduler: APScheduler, retry with backoff, structured logging (F5)
- Testing: Hypothesis PBT, mypy strict, E2E benchmarks p95<100ms, security OWASP (F6)
- Dockerfile: multi-stage builder+runtime (but runs as root, no OCI labels, no .dockerignore)
- docker-compose.yml: dev stack with PostgreSQL exposed on 5432
- CI: 3-gate pipeline (lint → test+coverage combined)
- Docs: all stubs (ARCHITECTURE.md, API_REFERENCE.md, SETUP.md = 2 lines each)
- README: v0.6.0 with basic info, no badges, no quick start
- CONTRIBUTING.md: empty file

**What's missing (this plan):**
- Dockerfile: non-root `USER app`, OCI labels, `--chown=app:app` COPY
- `.dockerignore`: exclude 15+ patterns from build context
- `docker-compose.prod.yml`: self-contained prod stack (app + PostgreSQL, no port exposure, restart policy, .env vars)
- `.env.example`: expand from 6 to 17 variables (F0–F7)
- Makefile: +demo, +docker-prod-up, +docker-prod-down commands
- `README.md`: v1.0.0 with badges, features, quick start, API table
- `docs/ARCHITECTURE.md`: full rewrite with 3 Mermaid diagrams, import rules, patterns, decisions
- `docs/API_REFERENCE.md`: full rewrite with 11 endpoints, error examples, curl examples
- `docs/SETUP.md`: full rewrite with prereqs, dev/prod/Docker/demo, env var table, troubleshooting
- `scripts/demo.sh`: full flow demo script (health → category → product → IN → stock → OUT → stock → historical → movements)
- `CONTRIBUTING.md`: contribution guide (setup, commits, quality, architecture, PR process)
- `.github/workflows/ci.yml`: rewrite to 5 gates (lint → typecheck → test → coverage → docker-build)

## Architecture Decisions (from Spec Approvals)

| # | Decision | Rationale | Source |
|---|----------|-----------|--------|
| F7-D1 | Non-root `USER app` (uid=1000, gid=1000) | Security best practice. Limits attacker permissions if container is compromised | SPEC-70 |
| F7-D2 | `.dockerignore` excludes scripts/, docs/ai-agent-setup/, .opencode/, skills/ | Reduces build context ~50%, prevents leaks of dev-only files | SPEC-70 |
| F7-D3 | OCI `LABEL` metadata in Dockerfile | Standard for image discovery and auditing in registries | SPEC-70 |
| F7-D4 | `docker-compose.prod.yml` separate from dev | Dev exposes PostgreSQL (debugging). Prod does not. Different restart policies | SPEC-70 |
| F7-D5 | `restart: unless-stopped` in prod | Services auto-restart after crash/reboot. Only `docker compose down` stops permanently | SPEC-70 |
| F7-D6 | PostgreSQL port NOT exposed in prod | Only internal app↔db via Docker network. Exposing is security risk | SPEC-70 |
| F7-D7 | `.env.example` documents all 17 variables F0–F7 | Single reference for all env vars. New developer has complete picture | SPEC-70 |
| F7-D8 | Cero nuevas dependencias de producción en F7 | F7 is infra + docs, no logic | SPEC.md |
| F7-D9 | Docker local + demo (no cloud deploy) | Target deployment is Docker Compose local | SPEC.md |
| F7-D10 | Mermaid diagrams in ARCHITECTURE.md (layers, ER, sequence) | Render natively on GitHub. No external tools | SPEC-71 |
| F7-D11 | Demo script with `set -euo pipefail` and `curl -sf` | Fail fast on any error. Silent progress, fail on HTTP ≥400 | SPEC-71 |
| F7-D12 | Error examples in API_REFERENCE (1-2 per endpoint) | More useful for API consumers than success-only docs | SPEC-71 |
| F7-D13 | 11 endpoints documented (not 10) | Actual inventory: health(1) + categories(2) + products(3) + movements(3) + stock(2) | SPEC-71 |
| F7-D14 | 5 CI gates: lint → typecheck → test → coverage → docker-build | Each gate is independent job. Fail fast: if one fails, downstream skipped | SPEC-72 |
| F7-D15 | Docker build with `type=gha` cache | GitHub Actions cache faster than registry for CI. ~30s warm vs ~2min cold | SPEC-72 |
| F7-D16 | `push: false` in Docker build gate | No deploy target in F7. Only validates Dockerfile compiles | SPEC-72 |
| F7-D17 | Coverage sub-gates: global ≥80%, domain ≥90%, application ≥85% | 3 sequential pytest commands in same job | SPEC-72 |
| F7-D18 | API abierta (sin auth) | No authentication in MVP. Infrastructure prepared for future | SPEC.md |

## Dependency Graph

```
SPEC-70: Docker Prod Infrastructure
│
├── Task 1: Dockerfile hardening (USER app, OCI labels, --chown)
│
├── Task 2: .dockerignore (NEW)
│
├── Task 3: docker-compose.prod.yml (NEW)
│   ├── depends on: Task 1 (Dockerfile must build)
│   └── uses: .env vars from Task 4
│
├── Task 4: .env.example expansion (6 → 17 variables)
│
└── Task 5: Makefile additions (demo, docker-prod-up, docker-prod-down)
    └── depends on: Task 3 (docker-compose.prod.yml must exist)

SPEC-71: Documentation & Demo
│
├── Task 6: scripts/demo.sh (NEW)
│   └── depends on: Task 5 (make demo command must exist)
│
├── Task 7: README.md v1.0.0 rewrite
│   └── depends on: Task 5 (commands table needs new make targets)
│
├── Task 8: docs/ARCHITECTURE.md rewrite
│
├── Task 9: docs/API_REFERENCE.md rewrite
│
├── Task 10: docs/SETUP.md rewrite
│   └── depends on: Task 4 (env var table from .env.example)
│   └── depends on: Task 5 (Docker prod commands)
│
└── Task 11: CONTRIBUTING.md rewrite
    └── depends on: Task 10 (links to SETUP.md)

SPEC-72: CI/CD Pipeline
│
└── Task 12: .github/workflows/ci.yml rewrite (5 gates)
    └── depends on: Task 1 (Dockerfile must be hardened for docker-build gate)

Cross-Spec Dependencies:
├── Task 3 → Task 5 (Makefile references docker-compose.prod.yml)
├── Task 5 → Task 6 (make demo invokes demo.sh)
├── Task 5 → Task 7 (README documents make commands)
├── Task 4 → Task 10 (SETUP.md documents env vars)
├── Task 5 → Task 10 (SETUP.md documents Docker prod commands)
├── Task 10 → Task 11 (CONTRIBUTING.md links SETUP.md)
├── Task 1 → Task 12 (CI docker-build gate needs hardened Dockerfile)
└── Task 6 → Task 13 (validation: demo script must work)
```

## Vertical Slicing Strategy

Each slice delivers one complete, testable capability:

```
Slice 1: Production Docker image (Tasks 1+2) — hardened Dockerfile + .dockerignore
Slice 2: Production Docker stack (Tasks 3+4+5) — prod compose + env vars + Makefile
Slice 3: Demo script (Task 6) — full flow exerciser
Slice 4: README v1.0.0 (Task 7) — project front door
Slice 5: Architecture docs (Task 8) — technical depth
Slice 6: API reference docs (Task 9) — endpoint reference
Slice 7: Setup guide (Task 10) — onboarding walkthrough
Slice 8: Contributing guide (Task 11) — contributor workflow
Slice 9: CI/CD pipeline (Task 12) — 5-gate quality pipeline
Slice 10: Full validation (Task 13) — end-to-end smoke test
Slice 11: Documentation update (Task 14) — project docs traceability
```

---

## Phase 1: SPEC-70 — Docker Production Infrastructure

### Task 1: Harden Dockerfile (non-root user, OCI labels, --chown)

**Description:** Modify the existing Dockerfile to add security best practices: create a non-root `app` user (uid=1000, gid=1000), add 5 OCI image labels, and set `--chown=app:app` on both COPY instructions. The container must run as `USER app` before CMD. **Repository URL for OCI label:** `https://github.com/Fisherk2/esquema-stock-historial`

**Acceptance criteria:**
- [ ] Dockerfile has `RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --shell /bin/bash --create-home app`
- [ ] Dockerfile has 5 OCI labels: `org.opencontainers.image.title`, `.description`, `.version`, `.source`, `.licenses`
- [ ] Dockerfile has `COPY --from=builder --chown=app:app /install /usr/local`
- [ ] Dockerfile has `COPY --from=builder --chown=app:app /app .`
- [ ] Dockerfile has `USER app` before CMD
- [ ] `docker build -t stock-historial:latest .` completes without errors
- [ ] Container runs as user `app`: `docker run --rm stock-historial:latest id` → `uid=1000(app) gid=1000(app)`
- [ ] `make lint` passes
- [ ] 0 regressions in existing tests (205+)

**Verification:**
- [ ] `docker build -t stock-historial:latest .` — exit code 0
- [ ] `docker run --rm stock-historial:latest python -c "import os; print(f'uid={os.getuid()} gid={os.getgid()}')"` → `uid=1000 gid=1000`
- [ ] `docker inspect stock-historial:latest | python3 -c "import sys,json; labels=json.load(sys.stdin)[0]['Config']['Labels']; assert 'org.opencontainers.image.title' in labels"` — passes
- [ ] `make test` — 205+ tests pass

**Dependencies:** None

**Files likely touched:**
- `Dockerfile` (modify)

**Estimated scope:** S (1 file)

---

### Task 2: Create .dockerignore

**Description:** Create `.dockerignore` to exclude unnecessary files from Docker build context. This reduces build time (~50% faster), prevents secret leaks, and keeps the image minimal.

**Acceptance criteria:**
- [ ] `.dockerignore` file exists
- [ ] Excludes: `.git/`, `__pycache__/`, `*.pyc`, `*.pyo`, `.Python`, `.venv/`, `venv/`, `env/`
- [ ] Excludes: `.pytest_cache/`, `htmlcov/`, `.coverage`, `.mypy_cache/`, `.ruff_cache/`
- [ ] Excludes: `.vscode/`, `.idea/`, `*.swp`, `*.swo`
- [ ] Excludes: `Dockerfile`, `docker-compose*.yml`, `.dockerignore`
- [ ] Excludes: `docs/ai-agent-setup/`, `.opencode/`, `skills/`, `agents/`, `references/`, `specs/`
- [ ] Excludes: `.env`, `.env.local`, `.env.production`
- [ ] Excludes: `dist/`, `build/`, `*.egg-info/`
- [ ] Excludes: `.DS_Store`, `Thumbs.db`
- [ ] Excludes: `scripts/` (dev-only, not needed in runtime)
- [ ] `docker build -t stock-historial:latest .` still succeeds after .dockerignore

**Verification:**
- [ ] `docker build -t stock-historial:latest .` — exit code 0
- [ ] Verify build context is smaller: `docker build -t stock-historial:latest . 2>&1 | head -5` — shows "Sending build context"

**Dependencies:** None (can parallel with Task 1)

**Files likely touched:**
- `.dockerignore` (new)

**Estimated scope:** XS (1 file, ~40 lines)

---

### Task 3: Create docker-compose.prod.yml

**Description:** Create production Docker Compose stack with app + PostgreSQL. Key differences from dev: PostgreSQL port NOT exposed, credentials from `.env`, `restart: unless-stopped`, `ENVIRONMENT=production`, `LOG_FORMAT=json`. Uses the hardened Dockerfile from Task 1.

**Acceptance criteria:**
- [ ] `docker-compose.prod.yml` exists
- [ ] Has `db` service: `postgres:16-alpine`, env vars from `${POSTGRES_USER:-stock_user}`, `${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}`, `${POSTGRES_DB:-stock_historial}`
- [ ] `db` has `restart: unless-stopped`
- [ ] `db` has healthcheck with `pg_isready`
- [ ] `db` has volume `pgdata_prod:/var/lib/postgresql/data`
- [ ] `db` does NOT expose port 5432 to host (no `ports:` section)
- [ ] Has `app` service: `build: .`, port `${APP_PORT:-8000}:8000`
- [ ] `app` has `DATABASE_URL` pointing to `db` service
- [ ] `app` has `ENVIRONMENT: production`, `LOG_FORMAT: ${LOG_FORMAT:-json}`
- [ ] `app` has scheduler env vars: `SCHEDULER_ENABLED`, `SCHEDULER_REFRESH_INTERVAL_MINUTES`, `SCHEDULER_MISFIRE_GRACE_TIME_SECONDS`, `SCHEDULER_STATEMENT_TIMEOUT_SECONDS`, `API_STATEMENT_TIMEOUT_SECONDS`
- [ ] `app` has `restart: unless-stopped`
- [ ] `app` has `depends_on: db: condition: service_healthy`
- [ ] `app` has healthcheck with `/v1/health`
- [ ] Named volume `pgdata_prod` declared

**Verification:**
- [ ] `docker compose -f docker-compose.prod.yml config` — validates without errors
- [ ] `docker compose -f docker-compose.prod.yml up -d` — both services start
- [ ] `sleep 10 && curl -sf http://localhost:8000/v1/health` — returns `{"status": "ok"}`
- [ ] `ss -tlnp | grep 5432` — no listener (PostgreSQL not exposed)
- [ ] `docker compose -f docker-compose.prod.yml down` — stops cleanly

**Dependencies:** Task 1 (Dockerfile must build successfully)

**Files likely touched:**
- `docker-compose.prod.yml` (new)

**Estimated scope:** S (1 file, ~60 lines)

---

### Task 4: Expand .env.example (6 → 17 variables)

**Description:** Expand `.env.example` to document all environment variables from F0 through F7. This is the single reference for all configuration. Adds: `APP_NAME`, `LOG_FORMAT`, scheduler vars (F5), PostgreSQL prod vars (F7), and `DEMO_BASE_URL` (F7).

**Acceptance criteria:**
- [ ] `.env.example` has `APP_NAME` variable
- [ ] `.env.example` has logging section: `LOG_LEVEL`, `LOG_FORMAT`, `ENVIRONMENT`
- [ ] `.env.example` has database section: `DATABASE_URL` with asyncpg DSN format comment
- [ ] `.env.example` has scheduler section (F5): `SCHEDULER_ENABLED`, `SCHEDULER_REFRESH_INTERVAL_MINUTES`, `SCHEDULER_MISFIRE_GRACE_TIME_SECONDS`, `SCHEDULER_STATEMENT_TIMEOUT_SECONDS`
- [ ] `.env.example` has API timeouts section (F5): `API_STATEMENT_TIMEOUT_SECONDS`
- [ ] `.env.example` has Docker prod section (F7): `POSTGRES_USER`, `POSTGRES_PASSWORD` (with ⚠️ warning), `POSTGRES_DB`
- [ ] `.env.example` has demo section (F7): `DEMO_BASE_URL`
- [ ] Total: 17 variables documented (up from 6)
- [ ] Each variable has inline comment explaining its purpose
- [ ] Sections are separated with clear headers

**Verification:**
- [ ] `grep -c "=" .env.example` — 17+ lines with assignments
- [ ] `grep "POSTGRES_PASSWORD" .env.example` — contains warning comment
- [ ] `make lint` passes

**Dependencies:** None (can parallel with Tasks 1-3)

**Files likely touched:**
- `.env.example` (modify)

**Estimated scope:** S (1 file, ~30 lines)

---

### Task 5: Add Makefile commands (demo, docker-prod-up, docker-prod-down)

**Description:** Add three new Makefile targets: `demo` (runs demo script), `docker-prod-up` (starts prod stack), `docker-prod-down` (stops prod stack). Update `.PHONY` and `help` target.

**Acceptance criteria:**
- [ ] `.PHONY` includes `demo docker-prod-up docker-prod-down`
- [ ] `demo:` target runs `bash scripts/demo.sh`
- [ ] `docker-prod-up:` target runs `docker compose -f docker-compose.prod.yml up -d`
- [ ] `docker-prod-down:` target runs `docker compose -f docker-compose.prod.yml down`
- [ ] `help` target shows all three new commands with descriptions
- [ ] `make help` output includes demo, docker-prod-up, docker-prod-down
- [ ] `make lint` passes

**Verification:**
- [ ] `make help | grep demo` — shows demo command
- [ ] `make help | grep docker-prod-up` — shows docker-prod-up command
- [ ] `make help | grep docker-prod-down` — shows docker-prod-down command

**Dependencies:** Task 3 (docker-compose.prod.yml must exist for commands to work)

**Files likely touched:**
- `Makefile` (modify)

**Estimated scope:** S (1 file, ~10 lines added)

---

### Checkpoint: SPEC-70 Complete
- [ ] Dockerfile: `USER app`, OCI labels, `--chown=app:app` on both COPY
- [ ] `.dockerignore`: 15+ patterns excluded
- [ ] `docker-compose.prod.yml`: app + db, no PostgreSQL port exposed, restart policies, .env vars
- [ ] `.env.example`: 17 variables documented F0-F7
- [ ] Makefile: demo, docker-prod-up, docker-prod-down
- [ ] `docker build -t stock-historial:latest .` succeeds
- [ ] Container runs as uid=1000(app) gid=1000(app)
- [ ] Prod stack starts: `docker compose -f docker-compose.prod.yml up -d`
- [ ] Healthcheck passes: `curl -sf http://localhost:8000/v1/health`
- [ ] PostgreSQL NOT exposed on host port
- [ ] `make lint` passes
- [ ] 0 regressions in 205+ existing tests
- [ ] **Review with human before proceeding to SPEC-71**

---

## Phase 2: SPEC-71 — Documentation & Demo

### Task 6: Create scripts/demo.sh

**Description:** Create the demo script that exercises the full system flow via curl: health check → create category → create product → IN movement → query current stock → OUT movement → query updated stock → query historical stock → list movements. Uses `set -euo pipefail` and `curl -sf` for robust error handling.

**Acceptance criteria:**
- [ ] `scripts/demo.sh` exists and is executable (`chmod +x`)
- [ ] Uses `set -euo pipefail`
- [ ] Uses `DEMO_BASE_URL` env var (default `http://localhost:8000`)
- [ ] Step 1: Health check — `curl -sf "${BASE_URL}/v1/health"`
- [ ] Step 2: Create category — POST `/v1/categories` with name + description
- [ ] Step 3: Create product — POST `/v1/products` with SKU, name, category_id
- [ ] Step 4: Register IN movement — POST `/v1/movements` with quantity=50
- [ ] Step 5: Query current stock — GET `/v1/stock/{id}/current`
- [ ] Step 6: Register OUT movement — POST `/v1/movements` with quantity=10
- [ ] Step 7: Query updated stock — GET `/v1/stock/{id}/current`
- [ ] Step 8: Query historical stock — GET `/v1/stock/{id}/at-date?date=...`
- [ ] Step 9: List movements — GET `/v1/movements?product_id={id}&limit=10`
- [ ] All output formatted with `python3 -m json.tool`
- [ ] Extracts IDs from JSON responses for subsequent requests
- [ ] Prints step-by-step progress with emoji indicators
- [ ] Fails fast if server is unavailable (curl -sf exits non-zero)

**Verification:**
- [ ] `bash -n scripts/demo.sh` — syntax check passes
- [ ] With server running: `make demo` — exit code 0
- [ ] Demo output shows stock=50.0 after IN, stock=40.0 after OUT
- [ ] Without server: `DEMO_BASE_URL=http://invalid:9999 make demo` — exit code ≠ 0
- [ ] `make lint` passes

**Dependencies:** Task 5 (make demo command must exist)

**Files likely touched:**
- `scripts/demo.sh` (new)

**Estimated scope:** S (1 file, ~80 lines)

---

### Task 7: Rewrite README.md to v1.0.0

**Description:** Rewrite README.md following progressive disclosure: header + badges → features → stack → commands → quick start → structure → architecture → docs → API → status. This is the project's front door. **Repository URL for badges:** `https://github.com/Fisherk2/esquema-stock-historial`

**Acceptance criteria:**
- [ ] Header: title + one-line description
- [ ] Badges: CI status, coverage 99%, Python 3.12, MIT License
- [ ] Features table: Source of Truth Inmutable, Stock histórico <100ms, Clean Architecture, Immutable movements, etc.
- [ ] Stack Tecnológico table: all components with versions
- [ ] Commands table: all `make` commands including demo, docker-prod-up, docker-prod-down
- [ ] Quick Start: 3 steps — `make install && make docker-prod-up && make demo`
- [ ] Project structure: directory tree (same as v0.6.0)
- [ ] Architecture: summary paragraph + link to `docs/ARCHITECTURE.md`
- [ ] Documentation table: links to all doc files
- [ ] API Endpoints summary table: 11 endpoints with method + route + description
- [ ] Estado Actual: F7 completada, v1.0.0
- [ ] `make lint` passes

**Verification:**
- [ ] All internal links point to existing files (no 404s)
- [ ] Badge URLs are valid format (even if CI not yet active)
- [ ] API table has 11 rows (health + categories + products + movements + stock)
- [ ] Quick Start section has 3 steps
- [ ] Commands table includes demo, docker-prod-up, docker-prod-down

**Dependencies:** Task 5 (commands table needs new make targets)

**Files likely touched:**
- `README.md` (rewrite)

**Estimated scope:** M (1 file, ~120 lines)

---

### Task 8: Rewrite docs/ARCHITECTURE.md

**Description:** Full rewrite of the 2-line stub. Document Clean Architecture with 3 Mermaid diagrams (layer diagram, ER diagram, request flow sequence), import rules table, key patterns, and technical decisions.

**Acceptance criteria:**
- [ ] Overview section: what the system is, what problem it solves, architectural principles
- [ ] Layer diagram: Mermaid `graph TB` with Adapters → Application → Domain ← Infrastructure
- [ ] Detailed layers: each layer with responsibilities, components, import rules
- [ ] Key patterns: Repository, Unit of Work, CQRS (queries via MV), Source of Truth Inmutable
- [ ] Technical decisions: SQL explícito (no ORM), asyncpg, APScheduler, Pydantic strict
- [ ] Import rules table: what each layer can/cannot import
- [ ] Data diagram: Mermaid `erDiagram` with CATEGORIES → PRODUCTS → MOVEMENTS
- [ ] Request flow diagram: Mermaid `sequenceDiagram` Client → Router → UseCase → Repo → DB
- [ ] `make lint` passes

**Verification:**
- [ ] 3 Mermaid code blocks present (graph, erDiagram, sequenceDiagram)
- [ ] Import rules table has 4 rows (Domain, Application, Infrastructure, Adapters)
- [ ] All referenced components exist in codebase (Product, Movement, Category, etc.)
- [ ] Mermaid syntax valid (can verify on mermaid.live)

**Dependencies:** None (can parallel with Tasks 6, 7, 9, 10, 11)

**Files likely touched:**
- `docs/ARCHITECTURE.md` (rewrite)

**Estimated scope:** M (1 file, ~180 lines)

---

### Task 9: Rewrite docs/API_REFERENCE.md

**Description:** Full rewrite of the 2-line stub. Document all 11 API endpoints with method, route, description, parameters, request/response body, error codes, executable curl examples, and at least 1 error example per endpoint.

**Acceptance criteria:**
- [ ] Overview section: base URL, no authentication, content-type, pagination
- [ ] Error response format: `ErrorResponse` contract with example
- [ ] Error codes table: all error codes by endpoint with HTTP status and description
- [ ] 11 endpoint sections, each with: method, route, description, parameters, request body, response body, error codes, curl example, error example
- [ ] Health check: GET `/v1/health`
- [ ] Categories: POST `/v1/categories`, GET `/v1/categories`
- [ ] Products: POST `/v1/products`, GET `/v1/products`, GET `/v1/products/{id}`
- [ ] Movements: POST `/v1/movements`, GET `/v1/movements`, GET `/v1/movements/{id}`
- [ ] Stock: GET `/v1/stock/{id}/current`, GET `/v1/stock/{id}/at-date`
- [ ] Pagination section: explanation of limit/offset/total
- [ ] Rate limiting note: "Not implemented (future)"
- [ ] All curl examples are executable against a local server
- [ ] `make lint` passes

**Verification:**
- [ ] Count endpoint sections: 11
- [ ] Each endpoint has a `curl` code block
- [ ] Each endpoint has at least 1 error example
- [ ] Error response contract matches actual error handler format

**Dependencies:** None (can parallel with Tasks 6, 7, 8, 10, 11)

**Files likely touched:**
- `docs/API_REFERENCE.md` (rewrite)

**Estimated scope:** L (1 file, ~400 lines) — **acceptable because single file, no logic, pure documentation**

---

### Task 10: Rewrite docs/SETUP.md

**Description:** Full rewrite of the 2-line stub. Complete onboarding guide: prerequisites → installation → local dev → Docker dev → Docker prod → demo → environment variables → troubleshooting → migrations.

**Acceptance criteria:**
- [ ] Prerequisites: Python 3.12+, PostgreSQL 16+, Docker, Git
- [ ] Installation: `make install`, `.env` setup from `.env.example`
- [ ] Local dev: `make dev`, PostgreSQL via Docker or local
- [ ] Docker dev: `make docker-up`, hot reload, debugging
- [ ] Docker prod: `make docker-prod-up`, `.env` production setup, healthchecks
- [ ] Demo: `make demo`, `DEMO_BASE_URL` variable
- [ ] Environment variables table: 17 variables with defaults, descriptions, and "Since" phase
- [ ] Troubleshooting table: 6+ common problems with solutions
- [ ] Migrations: `make migrate`, `make seed`
- [ ] `make lint` passes

**Verification:**
- [ ] Environment variables table has 17 rows
- [ ] Troubleshooting table has 6+ rows
- [ ] All `make` commands referenced actually exist in Makefile
- [ ] All links to other docs point to existing files

**Dependencies:** Task 4 (env var table from .env.example), Task 5 (Docker prod commands)

**Files likely touched:**
- `docs/SETUP.md` (rewrite)

**Estimated scope:** M (1 file, ~150 lines)

---

### Task 11: Rewrite CONTRIBUTING.md

**Description:** Rewrite the empty CONTRIBUTING.md with a functional contributor guide: setup, workflow, commit conventions, quality gates, architecture rules, testing expectations, PR process.

**Acceptance criteria:**
- [ ] Setup section: prerequisites + link to `docs/SETUP.md`
- [ ] Workflow section: Fork → Branch → Commit → PR
- [ ] Commit convention: `type(scope): description` format with types and scopes
- [ ] Quality section: `make build` (lint + format + test) before commit
- [ ] Type checking: `make typecheck` must pass
- [ ] Coverage: must not reduce existing coverage
- [ ] Architecture: respect import rules (link to `docs/ARCHITECTURE.md`)
- [ ] Testing: write tests for all new code
- [ ] PR process: clear description, reference specs
- [ ] `make lint` passes

**Verification:**
- [ ] All referenced `make` commands exist
- [ ] Links to SETUP.md and ARCHITECTURE.md are valid
- [ ] Commit convention table has types: feat, fix, docs, style, refactor, test, chore, ci
- [ ] Scopes match project layers: domain, application, infrastructure, adapters, db, scheduler, docs, ci

**Dependencies:** Task 10 (links to SETUP.md)

**Files likely touched:**
- `CONTRIBUTING.md` (rewrite)

**Estimated scope:** S (1 file, ~80 lines)

---

### Checkpoint: SPEC-71 Complete
- [ ] Demo script: 9-step flow, `set -euo pipefail`, `curl -sf`, `DEMO_BASE_URL`
- [ ] `make demo` works with running server
- [ ] README v1.0.0: badges, features, quick start, API table
- [ ] ARCHITECTURE.md: 3 Mermaid diagrams, import rules, patterns, decisions
- [ ] API_REFERENCE.md: 11 endpoints with curl examples + error examples
- [ ] SETUP.md: prereqs → install → dev/prod Docker → demo → env vars → troubleshooting
- [ ] CONTRIBUTING.md: setup, commits, quality, PR process
- [ ] All internal documentation links are valid (no 404s)
- [ ] `make lint` passes
- [ ] 0 regressions in 205+ existing tests
- [ ] **Review with human before proceeding to SPEC-72**

---

## Phase 3: SPEC-72 — CI/CD Pipeline

### Task 12: Rewrite .github/workflows/ci.yml (5 gates)

**Description:** Rewrite the CI/CD pipeline from 3 gates (lint → test+coverage combined) to 5 independent sequential gates: lint → typecheck → test → coverage → docker-build. Each gate is a separate job with `needs` dependencies for fail-fast behavior.

**Acceptance criteria:**
- [ ] `ci.yml` has 5 jobs: `lint`, `typecheck`, `test`, `coverage`, `docker-build`
- [ ] Gate 1 (lint): `make lint`, `actions/setup-python@v5` with Python 3.12
- [ ] Gate 2 (typecheck): `make typecheck`, `needs: lint`
- [ ] Gate 3 (test): `make test`, `needs: typecheck`
- [ ] Gate 4 (coverage): 3 sub-gates, `needs: test`
  - `pytest --cov=src --cov-report=term-missing --cov-fail-under=80`
  - `pytest --cov=src.domain --cov-report=term-missing --cov-fail-under=90`
  - `pytest --cov=src.application --cov-report=term-missing --cov-fail-under=85`
- [ ] Gate 5 (docker-build): `docker/setup-buildx-action@v3` + `docker/build-push-action@v6`, `needs: coverage`
  - `push: false`
  - `cache-from: type=gha`
  - `cache-to: type=gha,mode=max`
  - `tags: stock-historial:latest`
- [ ] Each Python job uses `actions/setup-python@v5` with Python 3.12
- [ ] Each Python job installs `pip install -r requirements.txt`
- [ ] Pipeline fails if any gate fails (0 tolerance)
- [ ] No deploy step — only continuous validation
- [ ] `make lint` passes

**Verification:**
- [ ] YAML syntax valid: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` — no errors
- [ ] 5 jobs defined with correct `needs` chains
- [ ] Coverage job has 3 sub-steps (global, domain, application)
- [ ] Docker build job uses `type=gha` cache
- [ ] No `push: true` anywhere

**Dependencies:** Task 1 (Dockerfile must be hardened for docker-build gate to work)

**Files likely touched:**
- `.github/workflows/ci.yml` (rewrite)

**Estimated scope:** S (1 file, ~80 lines)

---

### Checkpoint: SPEC-72 Complete
- [ ] CI/CD pipeline: 5 gates (lint → typecheck → test → coverage → docker-build)
- [ ] All gates are independent jobs with `needs` dependencies
- [ ] Coverage sub-gates: global ≥80%, domain ≥90%, application ≥85%
- [ ] Docker build uses `type=gha` cache, `push: false`
- [ ] Pipeline validates without deploy
- [ ] `make lint` passes
- [ ] 0 regressions in 205+ existing tests
- [ ] **Review with human before proceeding to validation**

---

## Phase 4: Validation & Documentation Update

### Task 13: Full build validation + smoke tests

**Description:** Run the complete build pipeline to verify F7 changes don't break anything. Execute infrastructure-level smoke tests (Docker build, prod stack, demo script). Verify all quality gates pass locally.

**Acceptance criteria:**
- [ ] `make lint` passes with 0 errors
- [ ] `make typecheck` passes with 0 errors
- [ ] `make test` passes (205+ tests)
- [ ] Coverage `src/domain/` ≥90%
- [ ] Coverage `src/application/` ≥85%
- [ ] Coverage `src/infrastructure/` ≥70%
- [ ] Coverage global ≥80%
- [ ] `docker build -t stock-historial:latest .` succeeds
- [ ] `docker run --rm stock-historial:latest id` → `uid=1000(app) gid=1000(app)`
- [ ] `docker compose -f docker-compose.prod.yml up -d` starts both services
- [ ] Healthcheck passes: `curl -sf http://localhost:8000/v1/health`
- [ ] PostgreSQL NOT exposed on host: `ss -tlnp | grep 5432` → empty
- [ ] `docker compose -f docker-compose.prod.yml down` stops cleanly
- [ ] `make demo` succeeds (with server running)
- [ ] No import violations (domain never imports infrastructure)

**Verification:**
- [ ] `make build` — exit code 0
- [ ] `make test-cov` — coverage targets met
- [ ] `docker build -t stock-historial:latest .` — exit code 0
- [ ] Docker prod stack smoke test passes
- [ ] Demo script runs end-to-end

**Dependencies:** All previous tasks

**Files likely touched:** None (validation only)

**Estimated scope:** XS (validation only)

---

### Task 14: Update project documentation

**Description:** Update project documentation files to reflect F7 completion. Update WORKFLOW.md, spec-tracking.md (SPEC-70/71/72 checklists), and SPEC.md (F7 status, version).

**Acceptance criteria:**
- [ ] `WORKFLOW.md` — F7 status updated to "Completada" with summary
- [ ] `docs/workflow/spec-tracking.md` — SPEC-70/71/72 checklists fully verified ([17/17], [12/12], [14/14])
- [ ] `SPEC.md` — F7 row status changed to ✅ Completada, version set to 1.0.0
- [ ] `SPEC.md` — Version History table: `1.0.0 | F7 — Despliegue & Documentación | 2026-05-20`
- [ ] `AGENTS.md` — Phase updated to F7 completed

**Verification:**
- [ ] Review updated files for accuracy
- [ ] All spec checklists match actual implementation

**Dependencies:** Task 13 (validation must pass first)

**Files likely touched:**
- `WORKFLOW.md`
- `docs/workflow/spec-tracking.md`
- `SPEC.md`
- `AGENTS.md`

**Estimated scope:** S (4 files, documentation only)

---

### Checkpoint: F7 Complete
- [ ] All SPEC-70/71/72 acceptance criteria met
- [ ] `make build` passes
- [ ] `docker build` succeeds, non-root user verified
- [ ] Prod stack starts and healthcheck passes
- [ ] Demo script runs successfully
- [ ] CI/CD pipeline has 5 gates
- [ ] All documentation rewritten and accurate
- [ ] Version is 1.0.0
- [ ] Ready for human review → Release

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Docker build fails after Dockerfile changes | High | Test `docker build` immediately after Task 1. Keep multi-stage pattern intact |
| Prod stack fails to start (DB connection, healthcheck) | High | Task 3 includes explicit smoke test. Use `docker compose config` to validate YAML first |
| `.dockerignore` excludes too much (e.g., `src/` or `migrations/`) | High | Verify `docker build` still works after Task 2. Compare build context size |
| Demo script fails due to API response format mismatch | Medium | Use actual API responses as reference. Test with running server |
| CI/CD coverage sub-gates fail in CI (testcontainers timing) | Medium | Coverage job already runs in F6 CI successfully. Same pattern |
| Mermaid diagrams don't render on GitHub | Low | Use standard Mermaid syntax. Validate on mermaid.live |
| API_REFERENCE.md curl examples are outdated | Medium | Cross-reference with actual router code and DTOs. Test examples against running server |
| `POSTGRES_PASSWORD` required in prod compose but `.env` missing | Medium | `docker-compose.prod.yml` uses `${POSTGRES_PASSWORD:?...}` which shows clear error. SETUP.md documents the step |

## Open Questions

- ~~GitHub repository URL for OCI labels and CI badge~~ → **Resolved:** `https://github.com/Fisherk2/esquema-stock-historial`
- CI badge in README: Will only show green after first CI run on main branch. Document this in README.

## Parallelization Opportunities

**Safe to parallelize (no shared files):**
- Tasks 1 and 2 (Dockerfile + .dockerignore) — independent
- Tasks 4 and 1/2/3 (.env.example + Docker infra) — independent
- Tasks 8, 9 (ARCHITECTURE.md + API_REFERENCE.md) — independent doc rewrites
- Tasks 7, 8, 9, 11 (README + ARCHITECTURE + API_REF + CONTRIBUTING) — independent docs

**Must be sequential:**
- Task 1 → Task 3 (docker-compose.prod.yml needs working Dockerfile)
- Task 3 → Task 5 (Makefile references docker-compose.prod.yml)
- Task 5 → Task 6 (make demo invokes demo.sh)
- Task 5 → Task 7 (README documents new make commands)
- Task 4 → Task 10 (SETUP.md references .env.example vars)
- Task 5 → Task 10 (SETUP.md documents Docker prod commands)
- Task 10 → Task 11 (CONTRIBUTING.md links SETUP.md)
- Task 1 → Task 12 (CI docker-build gate needs hardened Dockerfile)
- Task 13 → Task 14 (validation before documentation update)

**Needs coordination:**
- Tasks 5, 7, 10 all reference the same Makefile commands — define command names first

## Implementation Order Reference

```
Tasks 1, 2, 4 (parallel: Dockerfile + .dockerignore + .env.example)
↓
Task 3 (docker-compose.prod.yml) ←── needs Task 1
↓
Task 5 (Makefile additions) ←── needs Task 3
↓
Tasks 6, 7, 8, 9 (parallel: demo.sh + README + ARCHITECTURE + API_REFERENCE)
↓                                            ↑
Task 10 (SETUP.md) ←── needs Tasks 4, 5     |
↓                                              |
Task 11 (CONTRIBUTING.md) ←── needs Task 10   |
↓                                              |
Task 12 (CI/CD) ←── needs Task 1              |
↓                                              |
Task 13 (full validation) ←── needs ALL       |
↓                                              |
Task 14 (documentation update) ←── needs Task 13
```
