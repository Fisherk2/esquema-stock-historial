# AGENTS.md

> **Nota:** Este documento es la fuente de verdad arquitectónica del proyecto. Para el orden de ejecución y trazabilidad de specs, consultar [WORKFLOW.md](WORKFLOW.md).

Sistema de gestión de inventario basado en **Source of Truth Inmutable** — cada movimiento es atómico e inalterable, con consultas de stock histórico en `<100ms` mediante vistas materializadas.

**Fase actual:** F3 — Adaptadores de Datos

## Quick Reference

- **Runtime:** Python 3.12+ · `pip install -r requirements.txt`
- **Build:** `make build`
- **Test:** `make test` (unit + integration + e2e)
- **Lint:** `make lint` (ruff + black --check)
- **DB:** PostgreSQL 16+ · `asyncpg`
- **Framework:** FastAPI + Pydantic + APScheduler

## Detailed Guidelines

- [Arquitectura y Diseño](docs/agents/architecture-design.md) — Clean Architecture, patrones, capas
- [Guías de Desarrollo](docs/agents/development-guidelines.md) — SOLID, estructura, pre-commit, errores
- [Estrategia de Testing](docs/agents/testing-strategy.md) — Fases, frameworks, métricas, mocking
- [Seguridad y Prohibiciones](docs/agents/security-prohibitions.md) — Validación, secretos, prácticas prohibidas
- [Optimización de Rendimiento](docs/agents/performance-optimisation.md) — SQL, vistas, índices, latencia
- [Tooling y CI/CD](docs/agents/tooling-ci-cd.md) — Ruff, Black, pytest, GitHub Actions, Docker
