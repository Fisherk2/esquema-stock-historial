# SPEC-72: CI/CD Pipeline

**Fase:** F7 — Despliegue & Documentación
**Dependencias:** Spec-03 (Calidad y automatización) ✅ Completado, Spec-60 (Hypothesis + mypy strict) ✅ Completado, Spec-70 (Dockerfile & Docker Compose Prod) ✅ Completado
**Prioridad:** Alta
**Estado:** Aprobado

---

## Objective

Extender el pipeline CI/CD existente (3 gates: lint → test → coverage) a 5 gates secuenciales: **lint → typecheck → test → coverage → Docker build**. Cada gate es un job independiente en GitHub Actions. No hay deploy automático — el pipeline solo valida continuamente.

**Principios de diseño:**
- **5 gates, 0 deploy** — validación continua sin despliegue automático
- **Cada job independiente** — un job no comparte estado con otro (excepto dependencies vía `needs`)
- **Fail fast** — si lint falla, no se ejecutan test/coverage/Docker build
- **Docker build con cache** — `docker/build-push-action` con `cache_from: type=gha`, `cache_to: type=gha` reduce build time de ~2min a ~30s
- **Cero nuevas dependencias** — los gates usan herramientas ya instaladas (ruff, mypy, pytest, docker)
- **Python 3.12 consistente** — todos los jobs usan `actions/setup-python@v5` con `3.12`

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| 5 gates secuenciales | lint → typecheck → test → coverage → Docker build. Cada gate depende del anterior. Si uno falla, los siguientes no se ejecutan |
| Jobs independientes (no steps en un solo job) | Cada job tiene su propio runner limpio. No hay contaminación de estado. Facilita debugging (cada job tiene su log separado) |
| `needs: lint` en typecheck, `needs: typecheck` en test, etc. | Dependencias explícitas. Falla rápido: si un gate falla, los dependientes se skipped |
| Docker build como último gate | Valida que el Dockerfile compila. Es el gate más lento, por eso va al final. Si lint/typecheck/test fallan, no se pierde tiempo en Docker build |
| `docker/build-push-action` con `type=gha` cache | GitHub Actions cache es más rápido que registry cache para builds en CI. Reduce build time significativamente en runs subsecuentes |
| No push a registry en CI | Solo valida que el build compila. No hay deploy automático. Push a registry es manual o en un workflow separado |
| Coverage gate mantiene `--cov-fail-under=80` | El umbral global de 80% es el mínimo. Los thresholds por paquete (domain ≥90%, application ≥85%) se validan dentro del step de coverage |
| Sin deploy automático | Deploy es manual. El pipeline es de validación continua, no de entrega continua |

---

## Current State (v0.6.0)

El `ci.yml` actual tiene 3 gates:

```yaml
# Gate 1: lint (ruff)
# Gate 2: test (pytest) — needs: lint
# Gate 3: coverage (pytest --cov-fail-under=80) — needs: lint (misnamed: runs in same job as test)
```

### Problems with Current CI

| Problema | Impacto |
|----------|---------|
| Coverage corre como step dentro de `test` job | Si test falla, coverage no corre. Pero coverage es un gate distinto con semántica diferente |
| No hay typecheck gate | mypy strict puede fallar localmente pero pasar desapercibido en CI |
| No hay Docker build gate | Dockerfile puede romperse sin detección hasta que alguien intenta `docker build` |
| Coverage step re-instala dependencies | Redundante con el step anterior en el mismo job |
| No hay cache de Docker | Docker build desde cero cada vez (~2min) |

---

## Target State (v1.0.0)

5 gates secuenciales, cada uno como job independiente:

```
lint ──→ typecheck ──→ test ──→ coverage ──→ docker-build
  │          │            │         │              │
  ruff     mypy --strict  pytest   --cov-fail-    docker build
  check    src/                    under=80       (cached)
```

---

## GitHub Actions Workflow

### `.github/workflows/ci.yml` — Full Rewrite

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  # ── Gate 1: Lint ────────────────────────────────────────────────
  # Ruff detecta errores de estilo, imports y bugs
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run ruff
        run: make lint

  # ── Gate 2: Type Check ─────────────────────────────────────────
  # mypy strict valida tipos en src/ (tests excluidos)
  typecheck:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run mypy strict
        run: make typecheck

  # ── Gate 3: Tests ──────────────────────────────────────────────
  # pytest con todo el suite (unit + integration + e2e + security)
  test:
    runs-on: ubuntu-latest
    needs: typecheck
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run tests
        run: make test

  # ── Gate 4: Coverage ───────────────────────────────────────────
  # Coverage global ≥80%, domain/ ≥90%, application/ ≥85%
  coverage:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run coverage (global ≥80%)
        run: pytest --cov=src --cov-report=term-missing --cov-fail-under=80
      - name: Check domain coverage ≥90%
        run: pytest --cov=src.domain --cov-report=term-missing --cov-fail-under=90
      - name: Check application coverage ≥85%
        run: pytest --cov=src.application --cov-report=term-missing --cov-fail-under=85

  # ── Gate 5: Docker Build ───────────────────────────────────────
  # Valida que el Dockerfile compila sin errores
  # Usa GitHub Actions cache (type=gha) para acelerar builds
  docker-build:
    runs-on: ubuntu-latest
    needs: coverage
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      - name: Build Docker image (cached)
        uses: docker/build-push-action@v6
        with:
          context: .
          push: false
          cache-from: type=gha
          cache-to: type=gha,mode=max
          tags: stock-historial:latest
```

---

## Gate Details

### Gate 1: Lint

| Aspecto | Detalle |
|---------|---------|
| Herramienta | `ruff check src tests` |
| Comando | `make lint` |
| Config | `pyproject.toml [tool.ruff]` |
| Fallo si | Cualquier error de lint (0 tolerancia) |
| Duración estimada | ~5s |

### Gate 2: Type Check

| Aspecto | Detalle |
|---------|---------|
| Herramienta | `mypy src/ --strict` |
| Comando | `make typecheck` |
| Config | `pyproject.toml [tool.mypy]` — strict=true, tests.* override |
| Fallo si | Cualquier error de tipos en `src/` |
| Duración estimada | ~15s |
| Nota | Tests excluidos (`strict=false` override en pyproject.toml) |

### Gate 3: Tests

| Aspecto | Detalle |
|---------|---------|
| Herramienta | `pytest` |
| Comando | `make test` |
| Config | `pyproject.toml [tool.pytest.ini_options]` |
| Fallo si | Cualquier test falla (205+ tests) |
| Duración estimada | ~30s (unit), ~60s (integration+e2e con testcontainers) |
| Nota | Incluye Hypothesis con `--hypothesis-seed=0` para reproducibilidad |

### Gate 4: Coverage

| Aspecto | Detalle |
|---------|---------|
| Herramienta | `pytest --cov` |
| Comando | `pytest --cov=src --cov-fail-under=80` |
| Sub-gates | `--cov=src.domain --cov-fail-under=90`, `--cov=src.application --cov-fail-under=85` |
| Fallo si | Coverage global <80%, domain <90%, o application <85% |
| Duración estimada | ~60s (misma suite que test, con measurement overhead) |
| Nota | Los 3 sub-gates corren en el mismo job (secuenciales). Si el primero falla, los otros no corren |

### Gate 5: Docker Build

| Aspecto | Detalle |
|---------|---------|
| Herramienta | `docker/build-push-action@v6` |
| Comando | `docker build` (via action) |
| Config | `Dockerfile` (multi-stage, Spec-70) |
| Fallo si | Build exit code ≠ 0 |
| Duración estimada | ~30s (cached), ~2min (cold) |
| Cache | `type=gha` (GitHub Actions cache) |
| Nota | `push: false` — no se pushea imagen a registry |

---

## Coverage Sub-Gates Strategy

### Problem

coverage.py no soporta `fail_under` por paquete nativamente. El `--cov-fail-under=80` es un gate global.

### Solution

Ejecutar 3 comandos pytest secuenciales en el job de coverage:

```bash
# Gate global: ≥80%
pytest --cov=src --cov-report=term-missing --cov-fail-under=80

# Gate domain: ≥90%
pytest --cov=src.domain --cov-report=term-missing --cov-fail-under=90

# Gate application: ≥85%
pytest --cov=src.application --cov-report=term-missing --cov-fail-under=85
```

Cada comando corre la suite completa pero solo mide coverage del paquete especificado. Si el primer gate falla, los siguientes no se ejecutan (fail fast).

### Performance Consideration

Los 3 comandos corren la misma suite 3 veces. Esto es aceptable porque:
- La suite completa toma ~60s (3 runs = ~3min total)
- El coverage job es el 4to de 5 gates — no bloquea lint/typecheck
- La alternativa (custom plugin o script) añade complejidad sin beneficio claro

---

## Docker Build Cache Strategy

### Why `type=gha`

GitHub Actions cache (`type=gha`) es la opción óptima para CI porque:

| Cache Type | Pros | Cons |
|------------|------|------|
| `type=gha` | Sin registry externo, cache en el mismo runner, más rápido para CI | Solo disponible en GitHub Actions |
| `type=registry` | Funciona en cualquier entorno CI, cache compartido entre runners | Requiere registry push/pull, más lento |
| Sin cache | Simple | ~2min por build desde cero |

### Expected Build Times

| Escenario | Tiempo |
|-----------|--------|
| Primera run (cold cache) | ~2min |
| Segunda run (warm cache, sin cambios en requirements) | ~30s |
| Run con cambio en requirements.txt | ~1min (solo re-installa deps) |
| Run con cambio en código (sin deps) | ~30s (re-usa layer de deps) |

### Cache Configuration

```yaml
cache-from: type=gha      # Leer cache de runs anteriores
cache-to: type=gha,mode=max  # Escribir cache completo (todas las layers)
```

`mode=max` guarda todas las layers intermedias, no solo la final. Esto maximiza cache hits para builds futuras.

---

## Pipeline Flow Diagram

```
┌──────────┐    ┌────────────┐    ┌──────────┐    ┌───────────┐    ┌──────────────┐
│   LINT   │───→│ TYPECHECK  │───→│   TEST   │───→│ COVERAGE  │───→│ DOCKER BUILD │
│  ruff    │    │  mypy      │    │  pytest  │    │  ≥80%     │    │  docker build│
│  check   │    │  --strict  │    │  205+    │    │  ≥90% dom │    │  cached gha  │
│          │    │  src/      │    │  tests   │    │  ≥85% app │    │  push:false  │
└──────────┘    └────────────┘    └──────────┘    └───────────┘    └──────────────┘
    ↓ fail          ↓ fail           ↓ fail          ↓ fail           ↓ fail
  SKIPPED         SKIPPED          SKIPPED         SKIPPED          SKIPPED
  remaining       remaining        remaining       remaining        remaining
  gates           gates            gates           gates            gates
```

---

## Files

| File | Description | Action |
|------|-------------|--------|
| `.github/workflows/ci.yml` | 5 gates: lint → typecheck → test → coverage → docker-build | REWRITE |

---

## Acceptance Criteria

- [ ] `ci.yml` tiene 5 jobs secuenciales: lint, typecheck, test, coverage, docker-build
- [ ] Gate lint: `make lint` (ruff check src tests)
- [ ] Gate typecheck: `make typecheck` (mypy strict en `src/`) — `needs: lint`
- [ ] Gate test: `make test` (pytest 205+ tests) — `needs: typecheck`
- [ ] Gate coverage: `pytest --cov=src --cov-fail-under=80` — `needs: test`
- [ ] Gate coverage: sub-gate domain `--cov=src.domain --cov-fail-under=90`
- [ ] Gate coverage: sub-gate application `--cov=src.application --cov-fail-under=85`
- [ ] Gate docker-build: `docker/build-push-action@v6` con `push: false` — `needs: coverage`
- [ ] Docker build usa `cache-from: type=gha` y `cache-to: type=gha,mode=max`
- [ ] Docker build usa `docker/setup-buildx-action@v3`
- [ ] Cada job usa `actions/setup-python@v5` con Python 3.12 (excepto docker-build)
- [ ] Pipeline falla si cualquier gate falla (0 tolerancia)
- [ ] No hay deploy automático — solo validación continua
- [ ] `make lint` pasa sin errores
- [ ] 0 regresiones en tests existentes (205+ tests)

---

## Testing Strategy

F7 no añade tests unitarios ni de integración. La validación del CI/CD es el pipeline mismo:

| Validación | Comando | Criterio |
|------------|---------|----------|
| Lint gate | Push a PR en GitHub | Job `lint` pasa (green check) |
| Typecheck gate | Push a PR en GitHub | Job `typecheck` pasa |
| Test gate | Push a PR en GitHub | Job `test` pasa (205+ tests) |
| Coverage gate | Push a PR en GitHub | Job `coverage` pasa (≥80% global, ≥90% domain, ≥85% application) |
| Docker build gate | Push a PR en GitHub | Job `docker-build` pasa (exit code 0) |
| Fail fast | Introducir error de lint en PR | Jobs typecheck, test, coverage, docker-build se skipped |
| Cache warming | Segundo push sin cambios | Docker build time ~30s (vs ~2min cold) |

### Manual Validation Steps

```bash
# 1. Validar lint gate localmente
make lint

# 2. Validar typecheck gate localmente
make typecheck

# 3. Validar test gate localmente
make test

# 4. Validar coverage gate localmente
pytest --cov=src --cov-report=term-missing --cov-fail-under=80
pytest --cov=src.domain --cov-report=term-missing --cov-fail-under=90
pytest --cov=src.application --cov-report=term-missing --cov-fail-under=85

# 5. Validar Docker build gate localmente
docker build -t stock-historial:latest .
```

---

## Out of Scope

Las siguientes capacidades de CI/CD están **explícitamente excluidas** de F7:

| Capacidad | Razón | Fase futura |
|-----------|-------|-------------|
| Deploy automático (staging/prod) | F7 es validación continua. Deploy es manual | F8+ |
| Push a Docker registry (GHCR, Docker Hub) | No hay destino de deploy definido | F8+ |
| Matrix testing (múltiples Python versions) | Solo Python 3.12 es soportado | F8+ |
| Security scanning (`pip-audit`, `safety`) | Requiere nuevas dev dependencies | F8+ |
| Performance regression testing | Requiere baseline y infraestructura de medición | F8+ |
| Nightly builds | No hay necesidad con el volumen actual de commits | F8+ |
| Release automation (tags, changelog) | Manual en F7, automatizable en el futuro | F8+ |

---

## Resolved Questions

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| F7-72-Q1 | ¿Jobs separados vs steps en un job? | **Jobs separados** | Cada job tiene runner limpio, logs separados, y se puede re-ejecutar independientemente. Steps comparten estado y dificultan debugging |
| F7-72-Q2 | ¿Docker build cache type? | **`type=gha`** | GitHub Actions cache es más rápido para CI que registry cache. Sin configuración de registry externo |
| F7-72-Q3 | ¿Push imagen a registry? | **No (`push: false`)** | F7 no tiene destino de deploy. Solo valida que el Dockerfile compila. Push es manual o en workflow separado |
| F7-72-Q4 | ¿Coverage por paquete en CI? | **Sí, 3 sub-gates secuenciales** | Global ≥80%, domain ≥90%, application ≥85%. 3 comandos pytest secuenciales en el mismo job |
| F7-72-Q5 | ¿Deploy automático? | **No** | F7 es validación continua. Deploy es manual. Se puede añadir en F8+ con GitHub Environments |
| F7-72-Q6 | ¿Security scanning (pip-audit)? | **No en F7** | Añade dependencia dev nueva. Se puede añadir como gate adicional en F8+ |
| F7-72-Q7 | ¿`mode=max` en cache-to? | **Sí** | Guarda todas las layers intermedias, no solo la final. Maximiza cache hits para builds futuras |
| F7-72-Q8 | ¿Docker Buildx setup? | **Sí, `setup-buildx-action@v3`** | Requerido por `docker/build-push-action@v6` para cache y build improvements |
