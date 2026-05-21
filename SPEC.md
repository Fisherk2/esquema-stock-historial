# Spec: stock-historial — Orquestador de Fases

> **Fuente de verdad arquitectónica:** [AGENTS.md](AGENTS.md)
> **Trazabilidad de specs:** [docs/workflow/spec-tracking.md](docs/workflow/spec-tracking.md)
> **Workflow de ejecución:** [WORKFLOW.md](WORKFLOW.md)

---

## Overview

Sistema de gestión de inventario basado en **Source of Truth Inmutable** — cada movimiento es atómico e inalterable, con consultas de stock histórico en `<100ms` mediante vistas materializadas.

**Fase actual:** F7 — Despliegue & Documentación ✅ Completada · Hardening post-launch ✅

---

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Runtime | Python | 3.12+ |
| Framework | FastAPI | 0.115+ |
| Validation | Pydantic | 2.x |
| DB Driver | asyncpg | 0.30+ |
| Scheduler | APScheduler | 3.10+ |
| DB | PostgreSQL | 16+ |
| Linter | Ruff | 0.8+ |
| Formatter | Black | 24.x |
| Testing | pytest + pytest-asyncio | 8.x / 0.24+ |
| PBT | Hypothesis | 6.x+ |
| Integration | testcontainers | 4.x |
| Benchmark | pytest-benchmark | — |
| Settings | pydantic-settings | 2.x |
| Type Check | mypy | —strict en `src/` |
| Containerization | Docker + Docker Compose | 27+ / 2.x |

---

## Commands

```
Install:      pip install -r requirements.txt
Dev:          make dev
Lint:         make lint
Typecheck:    make typecheck
Format:       make format
Test:         make test
Test (cov):   make test-cov
Build:        make build
Demo:         make demo
Docker dev:   make docker-up / make docker-down
Docker prod:  make docker-prod-up / make docker-prod-down
Migrate:      make migrate
Seed:         make seed
Clean:        make clean
```

---

## Global Conventions

### Code Style

- **Naming:** snake_case funciones/variables, PascalCase clases
- **Type hints:** obligatorios en toda firma de función
- **Imports:** stdlib → third-party → local (isort order)
- **Async:** toda I/O es async; cero sync DB calls
- **Errors:** excepciones de dominio, nunca raw `ValueError` en use cases
- **Max line:** 88 (black default). Complejidad <10 por función. Clases <300 líneas
- **No `print()`** — usar `logging`
- **SQL:** solo parametrizado (`$1`, `$2`), nunca concatenación
- **Docstrings:** Google style en clases/funciones públicas

### Testing Strategy

| Level | Scope | Framework |
|-------|-------|-----------|
| Unit | Domain rules, use cases (mocked repos) | pytest + Hypothesis |
| Integration | SQL real, repos, MV, UoW | pytest + testcontainers |
| E2E | Flujos HTTP completos, latencia | pytest + httpx + pytest-benchmark |
| Security | SQLi, input validation, error leakage | pytest + httpx |

**Coverage targets:** domain/ ≥90%, application/ ≥85%, infrastructure/ ≥70%, global ≥80%

**Hypothesis:** `max_examples=100` CI, `1000` dev. `--hypothesis-seed=0` para reproducibilidad.

### Boundaries

| Always | Never |
|--------|-------|
| Clean Architecture layers (domain never imports infrastructure) | Mutate historical data (`UPDATE`/`DELETE` on `movements`) |
| Validate all inputs with Pydantic at API edge | Use ORM for analytical queries |
| Parameterized SQL only (`$1`, `$2`) | Commit secrets (`.env`, credentials) |
| Non-root container (`USER app`) | Mix sync code in async routes |
| `set -euo pipefail` in bash scripts | `print()` in production |

---

## Phase Index

| Phase | Objective | Specs | Status |
|-------|-----------|-------|--------|
| **F0** | Preparación — skeleton, tooling, CI | [SPEC-01](specs/SPEC-01.md) · [SPEC-02](specs/SPEC-02.md) · [SPEC-03](specs/SPEC-03.md) · [SPEC-04](specs/SPEC-04.md) | ✅ Completada |
| **F1** | Infraestructura DB — schema 3NF, migraciones, pool, health | [SPEC-10](specs/SPEC-10.md) · [SPEC-11](specs/SPEC-11.md) · [SPEC-12](specs/SPEC-12.md) | ✅ Completada |
| **F2** | Núcleo de Dominio — entities, VOs, rules, ports | [SPEC-20](specs/SPEC-20.md) · [SPEC-21](specs/SPEC-21.md) · [SPEC-22](specs/SPEC-22.md) | ✅ Completada |
| **F3** | Adaptadores de Datos — repos, MV, UoW | [SPEC-30](specs/SPEC-30.md) · [SPEC-31](specs/SPEC-31.md) · [SPEC-32](specs/SPEC-32.md) | ✅ Completada |
| **F4** | Capa API — use cases, DTOs, routers, error mapping | [SPEC-40](specs/SPEC-40.md) · [SPEC-41](specs/SPEC-41.md) · [SPEC-42](specs/SPEC-42.md) | ✅ Completada |
| **F5** | Scheduler & Concurrencia — APScheduler, retry, logging | [SPEC-50](specs/SPEC-50.md) · [SPEC-51](specs/SPEC-51.md) · [SPEC-52](specs/SPEC-52.md) | ✅ Completada |
| **F6** | Testing Integral — Hypothesis, mypy strict, E2E, security | [SPEC-60](specs/SPEC-60.md) · [SPEC-61](specs/SPEC-61.md) · [SPEC-62](specs/SPEC-62.md) · [SPEC-63](specs/SPEC-63.md) | ✅ Completada |
| **F7** | Despliegue & Documentación — Docker prod, docs, CI/CD | [SPEC-70](specs/SPEC-70.md) · [SPEC-71](specs/SPEC-71.md) · [SPEC-72](specs/SPEC-72.md) | ✅ Completada |

---

## Implementation DAG

```mermaid
graph LR
    F0["F0 · Preparación<br/>S01–S04"] --> F1["F1 · Infraestructura DB<br/>S10→S11→S12"]
    F1 --> F2["F2 · Núcleo de Dominio<br/>S20→S21→S22"]
    F2 --> F3["F3 · Adaptadores de Datos<br/>S30→S31→S32"]
    F3 --> F4["F4 · Capa API<br/>S40→S41→S42"]
    F4 --> F5["F5 · Scheduler & Concurrencia<br/>S52→S51→S50"]
    F5 --> F6["F6 · Testing Integral<br/>S60→S61→S62→S63"]
    F6 --> F7["F7 · Despliegue & Docs<br/>S70→S71→S72"]

    style F0 fill:#4CAF50,color:#fff
    style F1 fill:#4CAF50,color:#fff
    style F2 fill:#4CAF50,color:#fff
    style F3 fill:#4CAF50,color:#fff
    style F4 fill:#4CAF50,color:#fff
    style F5 fill:#4CAF50,color:#fff
    style F6 fill:#4CAF50,color:#fff
    style F7 fill:#4CAF50,color:#fff
```

> **Leyenda:** 🟢 Completada
> Los DAGs detallados con dependencias cross-phase están en [docs/workflow/spec-tracking.md](docs/workflow/spec-tracking.md).

---

## Cross-Phase Decisions

Decisiones que afectan múltiples fases y no pertenecen a un solo spec:

| Decisión | Fases impactadas | Rationale |
|----------|------------------|-----------|
| `get_current_stock()` retorna `float` | F2, F3, F4 | Resolución F3-Q1: compatibilidad con asyncpg + vista materializada |
| MovementType como `Enum` de 4 valores | F1, F2, F3, F4 | Set cerrado, mapeo 1:1 a PostgreSQL ENUM |
| `mypy --strict` solo en `src/` | F0, F6, F7 | Tests usan mocks/AsyncMock; strict no beneficia |
| SQL explícito (sin ORM) | F1, F3, F4 | Control total sobre EXPLAIN, sin abstracciones ocultas |
| `AsyncIOScheduler` (no BackgroundScheduler) | F5, F7 | Usa event loop existente de FastAPI |
| `logging` estándar (no structlog) | F5 | Suficiente para MVP. Migración posible en F8+ |
| Coverage domain ≥90%, app ≥85%, infra ≥70% | F6, F7 | Refleja confianza por PBT (Hypothesis) |
| Cero nuevas dependencias de producción en F7 | F7 | F7 es infraestructura + docs, no lógica |
| Docker local + demo (no cloud) | F7 | Target de despliegue es Docker Compose local |
| API abierta (sin auth) | F4, F7 | Sin autenticación en MVP. Infraestructura preparada |
| SecurityHeadersMiddleware | F7 | `nosniff`, `DENY`, `no-store`, `referrer-policy` en todas las respuestas |
| `statement_timeout` via `server_settings` | F5, F7 | Timeout aplica a todas las conexiones del pool |
| `SELECT FOR UPDATE` para race conditions | F4, F5 | Dentro del UoW, `get_current_stock_with_lock()` serializa transacciones concurrentes |
| Pagination en DB para categorias | F4 | `LIMIT $1 OFFSET $2` en SQL, no slicing en memoria |
| Non-root container (`USER app`) | F7 | Best practice de seguridad en Docker |

---

## Project Structure

```
stock-historial/
├── src/
│   ├── domain/          # Entities, value objects, exceptions, rules, ports
│   ├── application/     # Use cases, DTOs, interfaces
│   ├── infrastructure/  # DB, repositories, scheduler, logging
│   ├── adapters/        # FastAPI routers, middleware, dependencies
│   ├── core/            # Config, retry decorator
│   └── main.py          # DI container, app factory, entrypoint
├── tests/
│   ├── unit/            # Mocked protocols, pure business logic
│   ├── integration/     # Testcontainers PostgreSQL, real SQL
│   ├── e2e/             # Full HTTP flows, latency benchmarks
│   └── security/        # SQL injection, input validation, error leakage
├── migrations/          # SQL migration files (numbered)
├── scripts/             # Demo, seed, utility scripts
├── specs/               # Detailed spec files per phase
├── docs/                # Architecture, API reference, setup guides
│   ├── agents/          # Agent instruction files
│   └── workflow/        # Spec tracking, dependency graphs
├── .github/workflows/   # CI/CD pipeline (5 gates)
├── docker-compose.yml   # Dev: PostgreSQL + app
├── docker-compose.prod.yml  # Prod: self-contained stack
├── Dockerfile           # Multi-stage production build
├── .dockerignore        # Exclude dev files from Docker context
├── .env.example         # All env vars F0-F7
├── pyproject.toml       # Ruff, black, pytest, mypy, hypothesis config
├── requirements.txt     # Pinned dependencies
├── Makefile             # All developer commands
└── README.md            # Setup instructions, architecture overview
```

---

## Version History

| Versión | Fase | Fecha |
|---------|------|-------|
| 0.1.0   | F0 — Preparación | 2026-05-14 |
| 0.2.0   | F1 — Infraestructura DB | 2026-05-14 |
| 0.3.0   | F2 — Núcleo de Dominio | 2026-05-15 |
| 0.4.0   | F4 — Capa API | 2026-05-16 |
| 0.5.0   | F5 — Scheduler & Concurrencia | 2026-05-17 |
| 0.6.0   | F6 — Testing Integral | 2026-05-18 |
| 1.0.0   | F7 — Despliegue & Documentación | 2026-05-21 |
