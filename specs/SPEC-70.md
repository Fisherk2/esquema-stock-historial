# SPEC-70: Dockerfile & Docker Compose Prod

**Fase:** F7 — Despliegue & Documentación
**Dependencias:** Spec-42 (Rutas FastAPI) ✅ Completado, Spec-50 (APScheduler) ✅ Completado, Spec-62 (Tests E2E) ✅ Completado
**Prioridad:** Alta
**Estado:** Aprobado

---

## Objective

Optimizar el Dockerfile existente para producción (non-root user, OCI labels, `.dockerignore`) y crear `docker-compose.prod.yml` — un stack self-contained con app + PostgreSQL persistente para despliegue local/demo. También actualizar `.env.example` con todas las variables F0-F7 y añadir comandos `docker-prod-up`/`docker-prod-down`/`demo` al Makefile.

**Principios de diseño:**
- **Non-root container** — el contenedor runtime ejecuta como usuario `app`, no como root
- **Self-contained prod stack** — un solo comando levanta app + DB con datos persistidos
- **Variables en `.env`** — cero credenciales hardcodeadas en YAML de producción
- **PostgreSQL no expuesto** — en prod, el puerto 5432 solo es accesible entre contenedores
- **OCI labels** — metadata estándar para descubrimiento y auditoría en registries
- **`.dockerignore` estricto** — solo el código necesario entra en el contexto de build
- **Cero nuevas dependencias** — F7 no añade nada a `requirements.txt`

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| Non-root `USER app` en runtime stage | Best practice de seguridad. Si el contenedor se compromete, el atacante tiene permisos limitados |
| `.dockerignore` explícito | Reduce contexto de build (~50% más rápido), evita leaks de `.git`, `__pycache__`, `.venv`, docs internos al contexto Docker |
| OCI `LABEL` metadata en Dockerfile | org.opencontainers.image.* labels mejoran descubrimiento y auditoría en registries |
| `docker-compose.prod.yml` separado del dev | El compose de dev expone PostgreSQL al host (útil para debugging). El compose de prod no. Diferentes políticas de restart |
| `restart: unless-stopped` en prod | Los servicios se reinician automáticamente tras crash o reboot. Solo se detienen con `docker compose down` |
| Variables en `.env` (no hardcodeadas en YAML) | Consistente con el patrón de configuración del proyecto (pydantic-settings). Facilita rotación de credenciales |
| Puerto PostgreSQL no expuesto en prod | Solo comunicación interna app↔db via red Docker. Exponer el puerto es riesgo de seguridad |
| `--chown=app:app` en COPY | Los archivos copiados al contenedor deben ser propiedad del usuario runtime, no de root |
| `.env.example` completo F0-F7 | Un solo archivo documenta todas las variables del sistema. Nuevo developer tiene referencia completa |

---

## Dockerfile Changes

### Current State (v0.6.0)

El Dockerfile actual tiene 2 stages (builder + runtime) pero:
- Runtime ejecuta como root
- No tiene `.dockerignore`
- No tiene OCI labels
- No tiene usuario no-root

### Target State (v1.0.0)

```dockerfile
# Stage 1: Builder — instala dependencias en un prefix aislado
# para que el stage runtime no incluya pip ni caché de compilación.
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY . .

# Stage 2: Runtime — imagen mínima solo con Python y las dependencias
# instaladas. Sin herramientas de build, sin caché de pip.
# Ejecuta como usuario no-root (app) para seguridad.
FROM python:3.12-slim AS runtime

# OCI Image Spec labels — metadata estándar para registries
LABEL org.opencontainers.image.title="Stock Historial" \
      org.opencontainers.image.description="Sistema de gestión de inventario con Source of Truth Inmutable" \
      org.opencontainers.image.version="1.0.0" \
      org.opencontainers.image.source="https://github.com/Fisherk2/esquema-stock-historial" \
      org.opencontainers.image.licenses="MIT"

# Crear usuario no-root antes de COPY
RUN groupadd --gid 1000 app && \
    useradd --uid 1000 --gid app --shell /bin/bash --create-home app

WORKDIR /app

# Copiar dependencias y código con ownership correcto
COPY --from=builder --chown=app:app /install /usr/local
COPY --from=builder --chown=app:app /app .

# PYTHONUNBUFFERED: logs en tiempo real (sin buffer en stdout/stderr)
# PYTHONDONTWRITEBYTECODE: evita archivos .pyc en contenedor
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Ejecutar como usuario no-root
USER app

# Healthcheck usa el endpoint /v1/health para verificar que la app responde
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/v1/health')" || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Key Changes Summary

| Cambio | Antes | Después |
|--------|-------|---------|
| Usuario runtime | root (default) | `USER app` (uid=1000, gid=1000) |
| OCI Labels | Ninguno | 5 labels org.opencontainers.image.* |
| COPY ownership | default (root) | `--chown=app:app` |
| `.dockerignore` | No existe | Excluye 15+ patrones |

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

Stack self-contained para despliegue local/demo. Diferencias clave vs `docker-compose.yml` (dev):

| Aspecto | Dev (`docker-compose.yml`) | Prod (`docker-compose.prod.yml`) |
|---------|---------------------------|----------------------------------|
| PostgreSQL puerto | Expuesto al host (`5432:5432`) | No expuesto (solo red interna) |
| Credenciales | Hardcodeadas (`postgres:postgres`) | Desde `.env` |
| Restart policy | Default (no restart) | `unless-stopped` |
| Environment | `development` | `production` |
| Scheduler | Default (enabled) | Explicitly enabled |
| Log level | `info` | `info` |
| Log format | `text` | `json` (structured for prod) |

```yaml
# docker-compose.prod.yml — Stack de producción para despliegue local/demo
# Uso: docker compose -f docker-compose.prod.yml up -d
# Variables: configurar .env antes de levantar (ver .env.example)

services:
  # PostgreSQL 16 Alpine — datos persistidos en volumen
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-stock_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
      POSTGRES_DB: ${POSTGRES_DB:-stock_historial}
    # No exponer puerto al host en producción
    # Solo comunicación interna app↔db via red Docker
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

  # App FastAPI — se construye desde el Dockerfile optimizado
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

### Contrato de Variables para `.env` (prod)

```bash
# .env — Configuración de producción para docker-compose.prod.yml

# PostgreSQL (requerido para prod)
POSTGRES_USER=stock_user
POSTGRES_PASSWORD=change_me_in_production  # ⚠️ CAMBIAR en producción real
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

Solo documenta 6 variables: `APP_NAME`, `APP_HOST`, `APP_PORT`, `LOG_LEVEL`, `ENVIRONMENT`, `DATABASE_URL`.

### Target State (v1.0.0)

```bash
# ── Application ──────────────────────────────────────────────────────
APP_NAME=Stock Historial          # Nombre de la app para logs y metadata
APP_HOST=0.0.0.0                  # Interfaz de red (0.0.0.0 para Docker)
APP_PORT=8000                     # Puerto de escucha HTTP

# ── Logging ──────────────────────────────────────────────────────────
LOG_LEVEL=info                    # debug | info | warning | error
LOG_FORMAT=text                   # text | json (json recomendado para producción)
ENVIRONMENT=development           # development | staging | production

# ── Database ─────────────────────────────────────────────────────────
# Formato DSN asyncpg: postgresql+asyncpg://user:pass@host:port/dbname
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/stock_historial

# ── Scheduler (F5) ──────────────────────────────────────────────────
SCHEDULER_ENABLED=true            # true | false (false deshabilita el scheduler)
SCHEDULER_REFRESH_INTERVAL_MINUTES=5  # Minutos entre refreshes de la vista materializada
SCHEDULER_MISFIRE_GRACE_TIME_SECONDS=60  # Tolerancia en segundos para jobs retrasados
SCHEDULER_STATEMENT_TIMEOUT_SECONDS=30   # Timeout en segundos para el refresh job

# ── API Timeouts (F5) ───────────────────────────────────────────────
API_STATEMENT_TIMEOUT_SECONDS=5   # Timeout en segundos para queries de API

# ── Docker Compose Prod ─────────────────────────────────────────────
# Solo necesarias para docker-compose.prod.yml
POSTGRES_USER=stock_user          # Usuario de PostgreSQL para prod
POSTGRES_PASSWORD=change_me_in_production  # ⚠️ CAMBIAR en producción real
POSTGRES_DB=stock_historial       # Base de datos PostgreSQL para prod

# ── Demo Script ──────────────────────────────────────────────────────
DEMO_BASE_URL=http://localhost:8000  # URL base para scripts/demo.sh
```

---

## Makefile Additions

### Commands to Add

```makefile
# Añadir a .PHONY:
# demo docker-prod-up docker-prod-down

demo:
	bash scripts/demo.sh

docker-prod-up:
	docker compose -f docker-compose.prod.yml up -d

docker-prod-down:
	docker compose -f docker-compose.prod.yml down
```

### Updated `help` Target

Añadir las siguientes líneas al target `help`:

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
| `.dockerignore` | Excluir archivos innecesarios del contexto Docker | NEW |
| `docker-compose.prod.yml` | Stack prod self-contained (app + PostgreSQL persistente) | NEW |
| `.env.example` | Documentar todas las variables F0-F7 | MODIFY |
| `Makefile` | +demo, +docker-prod-up, +docker-prod-down | MODIFY |

---

## Acceptance Criteria

- [ ] Dockerfile: `USER app` declarado antes de CMD, `groupadd`/`useradd` con gid=1000/uid=1000
- [ ] Dockerfile: 5 OCI labels `org.opencontainers.image.*` (title, description, version, source, licenses)
- [ ] Dockerfile: `COPY --from=builder --chown=app:app` en ambas instrucciones COPY
- [ ] `.dockerignore`: excluye `.git/`, `__pycache__/`, `.venv/`, `.mypy_cache/`, `.ruff_cache/`, `htmlcov/`, `docs/ai-agent-setup/`, `.opencode/`, `skills/`, `agents/`, `references/`, `specs/`, `scripts/`
- [ ] `docker build -t stock-historial:latest .` completa sin errores
- [ ] Contenedor runtime ejecuta como usuario `app` (verificar con `docker exec <container> id`)
- [ ] `docker-compose.prod.yml` incluye servicios `app` + `db`
- [ ] `docker compose -f docker-compose.prod.yml up -d` levanta ambos servicios
- [ ] Healthcheck de app pasa: `curl -sf http://localhost:8000/v1/health` retorna `{"status": "ok"}`
- [ ] Puerto de PostgreSQL NO expuesto al host en producción (sin `ports: - "5432:5432"`)
- [ ] Ambos servicios tienen `restart: unless-stopped`
- [ ] Variables de entorno de prod vienen de `.env` (POSTGRES_PASSWORD requerida)
- [ ] `.env.example` documenta todas las variables F0-F7 (13 variables + 3 prod-only + 1 demo)
- [ ] `make demo` ejecuta `bash scripts/demo.sh`
- [ ] `make docker-prod-up` ejecuta `docker compose -f docker-compose.prod.yml up -d`
- [ ] `make docker-prod-down` ejecuta `docker compose -f docker-compose.prod.yml down`
- [ ] `make lint` pasa sin errores
- [ ] 0 regresiones en tests existentes (205+ tests)

---

## Testing Strategy

F7 no añade tests unitarios ni de integración nuevos. La validación es de infraestructura:

| Validación | Comando | Criterio de Éxito |
|------------|---------|-------------------|
| Docker build | `docker build -t stock-historial:latest .` | Exit code 0 |
| Non-root user | `docker run --rm stock-historial:latest id` | `uid=1000(app) gid=1000(app)` |
| Prod stack up | `docker compose -f docker-compose.prod.yml up -d` | Ambos servicios running |
| Healthcheck | `curl -sf http://localhost:8000/v1/health` | `{"status": "ok"}` |
| PostgreSQL no expuesto | `ss -tlnp \| grep 5432` | No hay listener en host |
| Prod stack down | `docker compose -f docker-compose.prod.yml down` | Ambos servicios stopped |
| Tests existentes | `make test` | 205+ tests pasando |

### Ejemplo: Verificación de non-root user

```bash
# Build y verificación de usuario
docker build -t stock-historial:latest .
docker run --rm stock-historial:latest python -c "import os; print(f'uid={os.getuid()} gid={os.getgid()}')"
# Expected output: uid=1000 gid=1000
```

### Ejemplo: Verificación de prod stack

```bash
# Levantar stack de producción
docker compose -f docker-compose.prod.yml up -d

# Esperar healthchecks
sleep 10

# Verificar API
curl -sf http://localhost:8000/v1/health | python3 -m json.tool

# Verificar que PostgreSQL NO está expuesto al host
ss -tlnp | grep 5432 || echo "OK: PostgreSQL no expuesto"

# Detener stack
docker compose -f docker-compose.prod.yml down
```

---

## Resolved Questions

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| F7-70-Q1 | ¿Non-root user uid/gid? | **1000/1000** | Estándar convencional para primer usuario no-root en Linux. Evita conflictos con uid=0 (root) |
| F7-70-Q2 | ¿Exponer puerto PostgreSQL en prod? | **No** | Solo comunicación interna app↔db via red Docker. Exponer el puerto es riesgo de seguridad innecesario |
| F7-70-Q3 | ¿`restart: unless-stopped`? | **Sí** | Los servicios se reinician automáticamente tras crash o reboot. Solo `docker compose down` los detiene permanentemente |
| F7-70-Q4 | ¿OCI labels en Dockerfile? | **Sí, 5 labels** | org.opencontainers.image.title, description, version, source, licenses — estándar OCI para metadata de imágenes |
| F7-70-Q5 | ¿`.dockerignore` incluir `scripts/`? | **Sí** | Los scripts de desarrollo (lint.sh, test.sh, etc.) no se necesitan en el contenedor runtime. demo.sh se ejecuta desde el host |
| F7-70-Q6 | ¿Credenciales PostgreSQL en compose? | **Via `.env`** | POSTGRES_PASSWORD requerida (error si no está definida). Consistente con pydantic-settings |
| F7-70-Q7 | ¿LOG_FORMAT default en prod? | **`json`** | Logs estructurados son estándar en producción (agregación, búsqueda, alertas). Dev usa `text` para legibilidad |
