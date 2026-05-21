# SPEC-72: CI/CD Pipeline

**Phase:** F7 — Deployment & Documentation
**Dependencies:** Spec-03 (Quality and automation) ✅ Completed, Spec-60 (Hypothesis + mypy strict) ✅ Completed, Spec-70 (Dockerfile & Docker Compose Prod) ✅ Completed
**Priority:** High
**Status:** Approved

---

## Objective

Extend the existing CI/CD pipeline (3 gates: lint → test → coverage) to 5 sequential gates: **lint → typecheck → test → coverage → Docker build**. Each gate is an independent job in GitHub Actions. No automatic deployment — the pipeline only validates continuously.

**Design principles:**
- **5 gates, 0 deploy** — continuous validation without automatic deployment
- **Each job independent** — no job shares state with another (except dependencies via `needs`)
- **Fail fast** — if lint fails, test/coverage/Docker build are not executed
- **Docker build with cache** — `docker/build-push-action` with `cache_from: type=gha`, `cache_to: type=gha` reduces build time from ~2min to ~30s
- **Zero new dependencies** — gates use already installed tools (ruff, mypy, pytest, docker)
- **Consistent Python 3.12** — all jobs use `actions/setup-python@v5` with `3.12`

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| 5 sequential gates | lint → typecheck → test → coverage → Docker build. Each gate depends on the previous one. If one fails, the following ones don't execute |
| Independent jobs (not steps in a single job) | Each job has its own clean runner. No state contamination. Facilitates debugging (each job has its separate log) |
| `needs: lint` in typecheck, `needs: typecheck` in test, etc. | Explicit dependencies. Fails fast: if a gate fails, dependent ones are skipped |
| Docker build as last gate | Validates that the Dockerfile compiles. It's the slowest gate, which is why it goes at the end. If lint/typecheck/test fail, no time is wasted on Docker build |
| `docker/build-push-action` with `type=gha` cache | GitHub Actions cache is faster than registry cache for CI builds. Significantly reduces build time in subsequent runs |
| No push to registry in CI | Only validates that the build compiles. No automatic deployment. Push to registry is manual or in a separate workflow |
| Coverage gate uses 1× pytest + report | Per-package thresholds are verified via `coverage report --include` on already collected data — tests are not re-executed (3× → 1×, ~80% less time) |
| No automatic deployment | Deploy is manual. The pipeline is for continuous validation, not continuous delivery |

---

## Current State (v0.6.0)

The current `ci.yml` has 3 gates:

```yaml
# Gate 1: lint (ruff)
# Gate 2: test (pytest) — needs: lint
# Gate 3: coverage (pytest --cov-fail-under=80) — needs: lint (misnamed: runs in same job as test)
```

### Problems with Current CI

| Problem | Impact |
|----------|---------|
| Coverage runs as a step inside `test` job | If test fails, coverage doesn't run. But coverage is a distinct gate with different semantics |
| No typecheck gate | mypy strict can fail locally but go unnoticed in CI |
| No Docker build gate | Dockerfile can break without detection until someone attempts `docker build` |
| Coverage step re-installs dependencies | Redundant with the previous step in the same job |
| No Docker cache | Docker build from scratch every time (~2min) |

---

## Target State (v1.0.0)

5 sequential gates, each as an independent job:

```
    lint ──→ typecheck ──→ test ──→ coverage ──→ docker-build
      │          │            │         │              │
      ruff     mypy --strict  pytest   1× pytest     docker build
      check    src/                   + report        (cached)
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
  # Ruff detects style errors, imports, and bugs
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
  # mypy strict validates types in src/ (tests excluded)
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
  # pytest with the full suite (unit + integration + e2e + security)
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
  # Global coverage ≥80%, domain/ ≥90%, application/ ≥85%
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
  # Validates that the Dockerfile compiles without errors
  # Uses GitHub Actions cache (type=gha) to speed up builds
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

| Aspect | Detail |
|---------|---------|
| Tool | `ruff check src tests` |
| Command | `make lint` |
| Config | `pyproject.toml [tool.ruff]` |
| Fails if | Any lint error (0 tolerance) |
| Estimated duration | ~5s |

### Gate 2: Type Check

| Aspect | Detail |
|---------|---------|
| Tool | `mypy src/ --strict` |
| Command | `make typecheck` |
| Config | `pyproject.toml [tool.mypy]` — strict=true, tests.* override |
| Fails if | Any type error in `src/` |
| Estimated duration | ~15s |
| Note | Tests excluded (`strict=false` override in pyproject.toml) |

### Gate 3: Tests

| Aspect | Detail |
|---------|---------|
| Tool | `pytest` |
| Command | `make test` |
| Config | `pyproject.toml [tool.pytest.ini_options]` |
| Fails if | Any test fails (205+ tests) |
| Estimated duration | ~30s (unit), ~60s (integration+e2e with testcontainers) |
| Note | Includes Hypothesis with `--hypothesis-seed=0` for reproducibility |

### Gate 4: Coverage

| Aspect | Detail |
|---------|---------|
| Tool | `pytest --cov` + `coverage report --include` |
| Command | `pytest --cov=src --cov-report=term-missing --cov-report=json` |
| Sub-gates | `coverage report --include="src/domain/*" --fail-under=90`, `coverage report --include="src/application/*" --fail-under=85` |
| Fails if | Global coverage <80%, domain <90%, or application <85% |
| Estimated duration | ~60s (1 test run + threshold verifications without re-executing) |
| Note | Single `pytest --cov` run; sub-gates use `coverage report` on already collected data — tests are not re-executed |

### Gate 5: Docker Build

| Aspect | Detail |
|---------|---------|
| Tool | `docker/build-push-action@v6` |
| Command | `docker build` (via action) |
| Config | `Dockerfile` (multi-stage, Spec-70) |
| Fails if | Build exit code ≠ 0 |
| Estimated duration | ~30s (cached), ~2min (cold) |
| Cache | `type=gha` (GitHub Actions cache) |
| Note | `push: false` — image is not pushed to registry |

---

## Coverage Sub-Gates Strategy

### Problem

coverage.py doesn't natively support per-package `fail_under`. The `--cov-fail-under=80` is a global gate.

### Solution (v1.0.0+)

A single pytest run with coverage, then per-package threshold verifications via `coverage report`:

```bash
# Single run: generates complete coverage data
pytest --cov=src --cov-report=term-missing --cov-report=json

# Global threshold verification ≥80% (via inline script)
python -c "import json; d=json.load(open('coverage.json')); \
  pct=d['totals']['percent_covered_display']; \
  print(f'Global coverage: {pct}%'); \
  exit(0 if float(pct)>=80 else 1)"

# Per-package threshold verification without re-executing tests
coverage report --include="src/domain/*" --fail-under=90
coverage report --include="src/application/*" --fail-under=85
```

### Performance Improvement

| Metric | Before (3× pytest) | After (1× pytest) | Improvement |
|---------|-------------------|---------------------|--------|
| Test suite runs | 3 | 1 | **66% less** |
| Estimated time | ~3min total | ~60s | **~80% less** |
| Testcontainers containers | 3 lifecycle | 1 lifecycle | **66% less overhead** |

### Rationale

`coverage report --include` reads already collected coverage data (`.coverage` file). Verifying per-package thresholds doesn't require re-executing tests, only re-analyzing existing data.

---

## Docker Build Cache Strategy

### Why `type=gha`

GitHub Actions cache (`type=gha`) is the optimal option for CI because:

| Cache Type | Pros | Cons |
|------------|------|------|
| `type=gha` | No external registry, cache on the same runner, faster for CI | Only available in GitHub Actions |
| `type=registry` | Works in any CI environment, cache shared between runners | Requires registry push/pull, slower |
| No cache | Simple | ~2min per build from scratch |

### Expected Build Times

| Scenario | Time |
|-----------|--------|
| First run (cold cache) | ~2min |
| Second run (warm cache, no changes in requirements) | ~30s |
| Run with change in requirements.txt | ~1min (only re-installs deps) |
| Run with code change (no deps) | ~30s (re-uses deps layer) |

### Cache Configuration

```yaml
cache-from: type=gha      # Read cache from previous runs
cache-to: type=gha,mode=max  # Write full cache (all layers)
```

`mode=max` saves all intermediate layers, not just the final one. This maximizes cache hits for future builds.

---

## Pipeline Flow Diagram

```
┌──────────┐    ┌────────────┐    ┌──────────┐    ┌───────────────────┐    ┌──────────────┐
│   LINT   │───→│ TYPECHECK  │───→│   TEST   │───→│    COVERAGE       │───→│ DOCKER BUILD │
│  ruff    │    │  mypy      │    │  pytest  │    │  1× pytest --cov  │    │  docker build│
│  check   │    │  --strict  │    │  205+    │    │  + report checks  │    │  cached gha  │
│          │    │  src/      │    │  tests   │    │  ≥90% dom ≥85% app│    │  push:false  │
└──────────┘    └────────────┘    └──────────┘    └───────────────────┘    └──────────────┘
    ↓ fail          ↓ fail           ↓ fail          ↓ fail                 ↓ fail
  SKIPPED         SKIPPED          SKIPPED         SKIPPED                 SKIPPED
  remaining       remaining        remaining       remaining               remaining
  gates           gates            gates           gates                   gates
```

---

## Files

| File | Description | Action |
|------|-------------|--------|
| `.github/workflows/ci.yml` | 5 gates: lint → typecheck → test → coverage → docker-build | REWRITE |

---

## Acceptance Criteria

- [ ] `ci.yml` has 5 sequential jobs: lint, typecheck, test, coverage, docker-build
- [ ] Gate lint: `make lint` (ruff check src tests)
- [ ] Gate typecheck: `make typecheck` (mypy strict on `src/`) — `needs: lint`
- [ ] Gate test: `make test` (pytest 205+ tests) — `needs: typecheck`
- [ ] Gate coverage: `pytest --cov=src --cov-fail-under=80` — `needs: test`
- [ ] Gate coverage: sub-gate domain `--cov=src.domain --cov-fail-under=90`
- [ ] Gate coverage: sub-gate application `--cov=src.application --cov-fail-under=85`
- [ ] Gate docker-build: `docker/build-push-action@v6` with `push: false` — `needs: coverage`
- [ ] Docker build uses `cache-from: type=gha` and `cache-to: type=gha,mode=max`
- [ ] Docker build uses `docker/setup-buildx-action@v3`
- [ ] Each job uses `actions/setup-python@v5` with Python 3.12 (except docker-build)
- [ ] Pipeline fails if any gate fails (0 tolerance)
- [ ] No automatic deployment — only continuous validation
- [ ] `make lint` passes without errors
- [ ] 0 regressions in existing tests (205+ tests)

---

## Testing Strategy

F7 does not add unit or integration tests. CI/CD validation is the pipeline itself:

| Validation | Command | Criteria |
|------------|---------|----------|
| Lint gate | Push to PR on GitHub | Job `lint` passes (green check) |
| Typecheck gate | Push to PR on GitHub | Job `typecheck` passes |
| Test gate | Push to PR on GitHub | Job `test` passes (205+ tests) |
| Coverage gate | Push to PR on GitHub | Job `coverage` passes (≥80% global, ≥90% domain, ≥85% application) |
| Docker build gate | Push to PR on GitHub | Job `docker-build` passes (exit code 0) |
| Fail fast | Introduce lint error in PR | Jobs typecheck, test, coverage, docker-build are skipped |
| Cache warming | Second push without changes | Docker build time ~30s (vs ~2min cold) |

### Manual Validation Steps

```bash
# 1. Validate lint gate locally
make lint

# 2. Validate typecheck gate locally
make typecheck

# 3. Validate test gate locally
make test

# 4. Validate coverage gate locally (1× pytest + coverage report)
pytest --cov=src --cov-report=term-missing --cov-report=json
coverage report --include="src/domain/*" --fail-under=90
coverage report --include="src/application/*" --fail-under=85

# 5. Validate Docker build gate locally
docker build -t stock-historial:latest .
```

---

## Out of Scope

The following CI/CD capabilities are **explicitly excluded** from F7:

| Capability | Reason | Future phase |
|-----------|-------|-------------|
| Automatic deployment (staging/prod) | F7 is continuous validation. Deploy is manual | F8+ |
| Push to Docker registry (GHCR, Docker Hub) | No deploy destination defined | F8+ |
| Matrix testing (multiple Python versions) | Only Python 3.12 is supported | F8+ |
| Security scanning (`pip-audit`, `safety`) | Requires new dev dependencies | F8+ |
| Performance regression testing | Requires baseline and measurement infrastructure | F8+ |
| Nightly builds | No need with the current commit volume | F8+ |
| Release automation (tags, changelog) | Manual in F7, automatable in the future | F8+ |

---

## Resolved Questions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| F7-72-Q1 | Separate jobs vs steps in a single job? | **Separate jobs** | Each job has a clean runner, separate logs, and can be re-executed independently. Steps share state and make debugging difficult |
| F7-72-Q2 | Docker build cache type? | **`type=gha`** | GitHub Actions cache is faster for CI than registry cache. No external registry configuration |
| F7-72-Q3 | Push image to registry? | **No (`push: false`)** | F7 has no deploy destination. Only validates that the Dockerfile compiles. Push is manual or in a separate workflow |
| F7-72-Q4 | Per-package coverage in CI? | **Yes, 3 sequential sub-gates** | Global ≥80%, domain ≥90%, application ≥85%. 3 sequential pytest commands in the same job |
| F7-72-Q5 | Automatic deployment? | **No** | F7 is continuous validation. Deploy is manual. Can be added in F8+ with GitHub Environments |
| F7-72-Q6 | Security scanning (pip-audit)? | **No in F7** | Adds new dev dependency. Can be added as an additional gate in F8+ |
| F7-72-Q7 | `mode=max` in cache-to? | **Yes** | Saves all intermediate layers, not just the final one. Maximizes cache hits for future builds |
| F7-72-Q8 | Docker Buildx setup? | **Yes, `setup-buildx-action@v3`** | Required by `docker/build-push-action@v6` for cache and build improvements |
