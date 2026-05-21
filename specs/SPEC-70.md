# SPEC-70: Dockerfile & Docker Compose Prod

**Phase:** F7 — Deployment & Documentation
**Dependencies:** Spec-42 (FastAPI Routes) ✅ Completed, Spec-50 (APScheduler) ✅ Completed, Spec-62 (E2E Tests) ✅ Completed
**Priority:** High
**Status:** Approved

---

## Objective

Optimize the existing Dockerfile for production (non-root user, OCI labels, `.dockerignore`) and create `docker-compose.prod.yml` — a self-contained stack with app + persistent PostgreSQL for local/demo deployment. Also update `.env.example` with all F0-F7 variables and add `docker-prod-up`/`docker-prod-down`/`demo` commands to the Makefile.

**Design principles:**
- **Non-root container** — the runtime container executes as user `app`, not as root
- **Self-contained prod stack** — a single command starts app + DB with persisted data
- **Variables in `.env`** — zero hardcoded credentials in production YAML
- **PostgreSQL not exposed** — in prod, port 5432 is only accessible between containers
- **OCI labels** — standard metadata for discovery and auditing in registries
- **Strict `.dockerignore`** — only necessary code enters the build context
- **Zero new dependencies** — F7 adds nothing to `requirements.txt`

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| Non-root `USER app` in runtime stage | Security best practice. If the container is compromised, the attacker has limited permissions |
| Explicit `.dockerignore` | Reduces build context (~50% faster), prevents leaks of `.git`, `__pycache__`, `.venv`, internal docs to Docker context |
| OCI `LABEL` metadata in Dockerfile | org.opencontainers.image.* labels improve discovery and auditing in registries |
| `docker-compose.prod.yml` separate from dev | Dev compose exposes PostgreSQL to host (useful for debugging). Prod compose doesn't. Different restart policies |
| `restart: unless-stopped` in prod | Services restart automatically after crash or reboot. Only stopped with `docker compose down` |
| Variables in `.env` (not hardcoded in YAML) | Consistent with project configuration pattern (pydantic-settings). Facilitates credential rotation |
| PostgreSQL port not exposed in prod | Only internal app↔db communication via Docker network. Exposing the port is a security risk |
| `--chown=app:app` in COPY | Files copied to the container must be owned by the runtime user, not root |
| Complete `.env.example` F0-F7 | A single file documents all system variables. New developer has complete reference |

---

## Dockerfile Changes

### Current State (v0.6.0)

The current Dockerfile has 2 stages (builder + runtime) but:
- Runtime runs as root
- No `.dockerignore`
- No OCI labels
- No non-root user

### Target State (v1.0.0)

```dockerfile
# Stage 1: Builder — installs dependencies in an isolated prefix
# so the runtime stage doesn't include pip or compilation cache.
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY . .

# Stage 2: Runtime — minimal image with only Python and dependencies
# installed. No build tools, no pip cache.
# Runs as non-root user (app) for security.
FROM python:3.12-slim AS runtime

# OCI Image Spec labels — standard metadata for registries
LABEL org.opencontainers.image.title="Stock Historial" \
      org.opencontainers.image.description="Inventory management system with Immutable Source of Truth" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/Fisherk2/esquema-stock-historial" \
      org.opencontainers.image.licenses="MIT"

# Create non-root user before COPY
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --shell /bin/bash --create-home app

WORKDIR /app

# Copy dependencies and code with correct ownership
COPY --from=builder --chown=app:app /install /usr/local
COPY --from=builder --chown=app:app /app .

# PYTHONUNBUFFERED: real-time logs (no buffer on stdout/stderr)
# PYTHONDONTWRITEBYTECODE: prevents .pyc files in container
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Run as non-root user
USER app

# Healthcheck uses /v1/health endpoint to verify app responds
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Key Changes Summary

| Change | Before | After |
|--------|-------|---------|
| Runtime user | root (default) | `USER app` (uid=1000, gid=1000) |
| OCI Labels | None | 5 labels org.opencontainers.image.* |
| COPY ownership | default (root) | `--chown=app:app` |
| `.dockerignore` | Does not exist | Excludes 15+ patterns |

---

## .dockerignore

### NEW FILE: `.dockerignore`

```
# Version control
.git/
.gitignore

# Python cache and bytecode
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Virtual environments
.venv/
venv/
env/

# Testing and coverage
.pytest_cache/
htmlcov/
.coverage
.coverage.*
coverage.xml

# Type checking cache
.mypy_cache/

# Linter cache
.ruff_cache/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
Dockerfile
docker-compose*.yml
.dockerignore

# Project meta (not needed in container)
docs/ai-agent-setup/
.opencode/
skills/
agents/
references/
specs/

# Environment files (secrets)
.env
.env.local
.env.production

# Build artifacts
dist/
build/
*.egg-info/

# OS files
.DS_Store
Thumbs.db

# Scripts (dev-only, not needed in runtime)
scripts/
```

---

## docker-compose.prod.yml

### NEW FILE: `docker-compose.prod.yml`

Self-contained stack for local/demo deployment. Key differences vs `docker-compose.yml` (dev):

| Aspect | Dev (`docker-compose.yml`) | Prod (`docker-compose.prod.yml`) |
|---------|---------------------------|----------------------------------|
| PostgreSQL port | Exposed to host (`5432:5432`) | Not exposed (internal network only) |
| Credentials | Hardcoded (`postgres:postgres`) | From `.env` |
| Restart policy | Default (no restart) | `unless-stopped` |
| Environment | `development` | `production` |
| Scheduler | Default (enabled) | Explicitly enabled |
| Log level | `info` | `info` |
| Log format | `text` | `json` (structured for prod) |

```yaml
# docker-compose.prod.yml — Production stack for local/demo deployment
# Usage: docker compose -f docker-compose.prod.yml up -d
# Variables: configure .env before starting (see .env.example)

services:
  # PostgreSQL 16 Alpine — data persisted in volume
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-stock_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
      POSTGRES_DB: ${POSTGRES_DB:-stock_historial}
    # Do not expose port to host in production
    # Only internal app↔db communication via Docker network
    # expose:
    #   - "5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-stock_user}"]
      interval: 5s
      timeout: 3s
      retries: 5
    volumes:
      - pgdata_prod:/var/lib/postgresql/data

  # FastAPI App — built from the optimized Dockerfile
  app:
    build: .
    ports:
      - "${APP_PORT:-8000}:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-stock_user}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-stock_historial}
      APP_HOST: 0.0.0.0
      APP_PORT: 8000
      LOG_LEVEL: ${LOG_LEVEL:-info}
      ENVIRONMENT: production
      LOG_FORMAT: ${LOG_FORMAT:-json}
      SCHEDULER_ENABLED: ${SCHEDULER_ENABLED:-true}
      SCHEDULER_REFRESH_INTERVAL_MINUTES: ${SCHEDULER_REFRESH_INTERVAL_MINUTES:-5}
      SCHEDULER_MISFIRE_GRACE_TIME_SECONDS: ${SCHEDULER_MISFIRE_GRACE_TIME_SECONDS:-60}
      SCHEDULER_STATEMENT_TIMEOUT_SECONDS: ${SCHEDULER_STATEMENT_TIMEOUT_SECONDS:-30}
      API_STATEMENT_TIMEOUT_SECONDS: ${API_STATEMENT_TIMEOUT_SECONDS:-5}
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health')"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 5s

volumes:
  pgdata_prod:
```

### Variable Contract for `.env` (prod)

```bash
# .env — Production configuration for docker-compose.prod.yml

# PostgreSQL (required for prod)
POSTGRES_USER=stock_user
POSTGRES_PASSWORD=change_me_in_production  # ⚠️ CHANGE in real production
POSTGRES_DB=stock_historial

# App
APP_PORT=8000
LOG_LEVEL=info
LOG_FORMAT=json
SCHEDULER_ENABLED=true
SCHEDULER_REFRESH_INTERVAL_MINUTES=5
SCHEDULER_MISFIRE_GRACE_TIME_SECONDS=60
SCHEDULER_STATEMENT_TIMEOUT_SECONDS=30
API_STATEMENT_TIMEOUT_SECONDS=5
```

---

## .env.example Update

### Current State (v0.6.0)

Only documents 6 variables: `APP_NAME`, `APP_HOST`, `APP_PORT`, `LOG_LEVEL`, `ENVIRONMENT`, `DATABASE_URL`.

### Target State (v1.0.0)

```bash
# ── Application ──────────────────────────────────────────────────────
APP_NAME=Stock Historial          # App name for logs and metadata
APP_HOST=0.0.0.0                  # Network interface (0.0.0.0 for Docker)
APP_PORT=8000                     # HTTP listen port

# ── Logging ──────────────────────────────────────────────────────────
LOG_LEVEL=info                    # debug | info | warning | error
LOG_FORMAT=text                   # text | json (json recommended for production)
ENVIRONMENT=development           # development | staging | production

# ── Database ─────────────────────────────────────────────────────────
# asyncpg DSN format: postgresql+asyncpg://user:pass@host:port/dbname
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/stock_historial

# ── Scheduler (F5) ──────────────────────────────────────────────────
SCHEDULER_ENABLED=true            # true | false (false disables the scheduler)
SCHEDULER_REFRESH_INTERVAL_MINUTES=5  # Minutes between materialized view refreshes
SCHEDULER_MISFIRE_GRACE_TIME_SECONDS=60  # Tolerance in seconds for delayed jobs
SCHEDULER_STATEMENT_TIMEOUT_SECONDS=30   # Timeout in seconds for the refresh job

# ── API Timeouts (F5) ───────────────────────────────────────────────
API_STATEMENT_TIMEOUT_SECONDS=5   # Timeout in seconds for API queries

# ── Docker Compose Prod ─────────────────────────────────────────────
# Only needed for docker-compose.prod.yml
POSTGRES_USER=stock_user          # PostgreSQL user for prod
POSTGRES_PASSWORD=change_me_in_production  # ⚠️ CHANGE in real production
POSTGRES_DB=stock_historial       # PostgreSQL database for prod

# ── Demo Script ──────────────────────────────────────────────────────
DEMO_BASE_URL=http://localhost:8000  # Base URL for scripts/demo.sh
```

---

## Makefile Additions

### Commands to Add

```makefile
# Add to .PHONY:
# demo docker-prod-up docker-prod-down

demo:
	bash scripts/demo.sh

docker-prod-up:
	docker compose -f docker-compose.prod.yml up -d

docker-prod-down:
	docker compose -f docker-compose.prod.yml down
```

### Updated `help` Target

Add the following lines to the `help` target:

```
@echo " demo Run demo script (scripts/demo.sh)"
@echo " docker-prod-up Start Docker Compose production stack"
@echo " docker-prod-down Stop Docker Compose production stack"
```

---

## Files

| File | Description | Action |
|------|-------------|--------|
| `Dockerfile` | Non-root user, OCI labels, `--chown=app:app` | MODIFY |
| `.dockerignore` | Exclude unnecessary files from Docker context | NEW |
| `docker-compose.prod.yml` | Self-contained prod stack (app + persistent PostgreSQL) | NEW |
| `.env.example` | Document all F0-F7 variables | MODIFY |
| `Makefile` | +demo, +docker-prod-up, +docker-prod-down | MODIFY |

---

## Acceptance Criteria

- [ ] Dockerfile: `USER app` declared before CMD, `groupadd`/`useradd` with gid=1000/uid=1000
- [ ] Dockerfile: 5 OCI labels `org.opencontainers.image.*` (title, description, version, source, licenses)
- [ ] Dockerfile: `COPY --from=builder --chown=app:app` in both COPY instructions
- [ ] `.dockerignore`: excludes `.git/`, `__pycache__/`, `.venv/`, `.mypy_cache/`, `.ruff_cache/`, `htmlcov/`, `docs/ai-agent-setup/`, `.opencode/`, `skills/`, `agents/`, `references/`, `specs/`, `scripts/`
- [ ] `docker build -t stock-historial:latest .` completes without errors
- [ ] Runtime container executes as user `app` (verify with `docker exec <container> id`)
- [ ] `docker-compose.prod.yml` includes `app` + `db` services
- [ ] `docker compose -f docker-compose.prod.yml up -d` starts both services
- [ ] App healthcheck passes: `curl -sf http://localhost:8000/v1/health` returns `{"status": "ok"}`
- [ ] PostgreSQL port NOT exposed to host in production (no `ports: - "5432:5432"`)
- [ ] Both services have `restart: unless-stopped`
- [ ] Prod environment variables come from `.env` (POSTGRES_PASSWORD required)
- [ ] `.env.example` documents all F0-F7 variables (13 variables + 3 prod-only + 1 demo)
- [ ] `make demo` executes `bash scripts/demo.sh`
- [ ] `make docker-prod-up` executes `docker compose -f docker-compose.prod.yml up -d`
- [ ] `make docker-prod-down` executes `docker compose -f docker-compose.prod.yml down`
- [ ] `make lint` passes without errors
- [ ] 0 regressions in existing tests (205+ tests)

---

## Testing Strategy

F7 does not add new unit or integration tests. Validation is infrastructure-based:

| Validation | Command | Success Criteria |
|------------|---------|-------------------|
| Docker build | `docker build -t stock-historial:latest .` | Exit code 0 |
| Non-root user | `docker run --rm stock-historial:latest id` | `uid=1000(app) gid=1000(app)` |
| Prod stack up | `docker compose -f docker-compose.prod.yml up -d` | Both services running |
| Healthcheck | `curl -sf http://localhost:8000/v1/health` | `{"status": "ok"}` |
| PostgreSQL not exposed | `ss -tlnp \| grep 5432` | No listener on host |
| Prod stack down | `docker compose -f docker-compose.prod.yml down` | Both services stopped |
| Existing tests | `make test` | 205+ tests passing |

### Example: Non-root user verification

```bash
# Build and user verification
docker build -t stock-historial:latest .
docker run --rm stock-historial:latest python -c "import os; print(f'uid={os.getuid()} gid={os.getgid()}')"
# Expected output: uid=1000 gid=1000
```

### Example: Prod stack verification

```bash
# Start production stack
docker compose -f docker-compose.prod.yml up -d

# Wait for healthchecks
sleep 10

# Verify API
curl -sf http://localhost:8000/v1/health | python3 -m json.tool

# Verify PostgreSQL is NOT exposed to host
ss -tlnp | grep 5432 || echo "OK: PostgreSQL not exposed"

# Stop stack
docker compose -f docker-compose.prod.yml down
```

---

## Resolved Questions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| F7-70-Q1 | Non-root user uid/gid? | **1000/1000** | Conventional standard for first non-root user on Linux. Avoids conflicts with uid=0 (root) |
| F7-70-Q2 | Expose PostgreSQL port in prod? | **No** | Only internal app↔db communication via Docker network. Exposing the port is an unnecessary security risk |
| F7-70-Q3 | `restart: unless-stopped`? | **Yes** | Services restart automatically after crash or reboot. Only `docker compose down` stops them permanently |
| F7-70-Q4 | OCI labels in Dockerfile? | **Yes, 5 labels** | org.opencontainers.image.title, description, version, source, licenses — OCI standard for image metadata |
| F7-70-Q5 | `.dockerignore` include `scripts/`? | **Yes** | Development scripts (lint.sh, test.sh, etc.) are not needed in the runtime container. demo.sh runs from the host |
| F7-70-Q6 | PostgreSQL credentials in compose? | **Via `.env`** | POSTGRES_PASSWORD required (error if not defined). Consistent with pydantic-settings |
| F7-70-Q7 | LOG_FORMAT default in prod? | **`json`** | Structured logs are standard in production (aggregation, search, alerts). Dev uses text for readability |
