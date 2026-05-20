# WORKFLOW.md

**Nombre del Proyecto:** Inventario Histórico & Stock por Fecha
**Versión:** 1.0.0
**Estado Actual:** F7 Completada ✅ — Version 1.0.0 (producción)
**Responsable:** Fisherk2 (Desarrollador Principal / Arquitecto)

Sistema de gestión de inventario con Source of Truth Inmutable, API REST y stock histórico en `<100ms`.

> **F0: Preparación** completada el 2026-05-14. Todos los specs (01-04) en estado Completado.
> **F1: Infraestructura DB** completada el 2026-05-15. Specs Spec-10/11/12 en estado Completado.
> **F2: Núcleo de Dominio** completada el 2026-05-15. Specs Spec-20/21/22 en estado Completado. 89 tests unitarios, 99.56% cobertura de dominio.
> **F3: Adaptadores de Datos** completada el 2026-05-18. Specs Spec-30/31/32 en estado Completado. 17 tareas implementadas, 98 tests unitarios + 43 tests de integración (100% pass), cobertura 96.30%. 4 repositorios Postgres (movement, product, category, stock_query), 3 mappers, vista materializada `mv_stock_historical` con refresh concurrente y fallback, Unit of Work con context manager. Documentación auditada 10/10. Lista para F4.
> **F4: Capa API** completada el 2026-05-19. Specs Spec-40/41/42 en estado Completado.
> 6 use cases, 5 DTOs, 4 routers (10 endpoints), error mapping middleware, DI factories.
> 147 unit tests + 88 integration tests (235 total, 100% pass, ~20s).
> Testcontainers optimizado: 1 contenedor/session (antes 88), ~20s vs ~20 min.
> `make lint` limpio. Version 0.4.0.
> **F5: Scheduler & Concurrencia** completada el 2026-05-19. Specs Spec-50/51/52 en estado Completado.
> APScheduler integrado, retry con backoff exponencial, logging estructurado con request_id.
> 282 tests total (194 unit + 88 integration), 100% pass. `make lint` limpio. Version 0.5.0.
> **F6: Testing Integral** completada el 2026-05-20. Specs Spec-60/61/62/63 en estado Completado.
> 205 tests unitarios pasando (99.34% cobertura global). Hypothesis PBT (property-based testing) con max_examples=100, seed=0. mypy --strict limpio en 74 archivos de src/. Domain coverage 99.60%, application 99.01%. Edge cases de integración en archivos separados (*_edge.py). E2E tests con SLA gate p95<100ms via pytest-benchmark. Pruebas de seguridad OWASP: SQL injection en 4 capas (path, query, body, repo), input validation boundary tests, error leakage tests, inmutabilidad enforcement (405). Version 0.6.0.
> **F7: Despliegue & Documentación** completada el 2026-05-20. Specs Spec-70/71/72 en estado Completado.
> Dockerfile hardened: non-root USER app, OCI labels, --chown. .dockerignore con 15+ patrones.
> docker-compose.prod.yml: app + db, PostgreSQL no expuesto, restart policies, .env vars.
> .env.example: 17 variables F0-F7. Makefile: demo, docker-prod-up, docker-prod-down.
> scripts/demo.sh: 9 pasos de flujo completo. README v1.0.0 con badges y quick start.
> docs/ARCHITECTURE.md: 3 diagramas Mermaid, import rules, patrones.
> docs/API_REFERENCE.md: 11 endpoints con curl + error examples.
> docs/SETUP.md: prereqs, dev/prod Docker, tabla 17 env vars, troubleshooting.
> CONTRIBUTING.md: guía para contribuidores con convenciones y flujo PR.
> CI/CD: 5 gates secuenciales (lint → typecheck → test → coverage → docker-build).
> 457 tests pasando (100% pass). Coverage global 90.98%, domain 100%, application 100%.
> **Version 1.0.0 — lista para producción.**

## Detailed Docs

- [Roadmap y Fases](docs/workflow/roadmap-phases.md) — Timeline, milestones, hitos clave
- [Seguimiento de Specs](docs/workflow/spec-tracking.md) — Tabla de specs, estados, dependencias
- [Grafos de Dependencia](docs/workflow/dependency-graphs.md) — Diagramas Mermaid de fases y specs
- [Reglas de Proceso](docs/workflow/process-rules.md) — Workflow spec-driven, aprobaciones, convenciones
- [Matriz de Stakeholders](docs/workflow/stakeholder-matrix.md) — Roles, contactos, responsabilidades
