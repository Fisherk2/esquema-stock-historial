# WORKFLOW.md

**Nombre del Proyecto:** Inventario Histórico & Stock por Fecha
**Versión:** 1.0.0
**Estado Actual:** F3 Completada — Lista para F4: Casos de Uso
**Responsable:** Fisherk2 (Desarrollador Principal / Arquitecto)

Sistema de gestión de inventario con Source of Truth Inmutable, API REST y stock histórico en `<100ms`.

> **F0: Preparación** completada el 2026-05-14. Todos los specs (01-04) en estado Completado.
> **F1: Infraestructura DB** completada el 2026-05-15. Specs Spec-10/11/12 en estado Completado.
> **F2: Núcleo de Dominio** completada el 2026-05-15. Specs Spec-20/21/22 en estado Completado. 89 tests unitarios, 99.56% cobertura de dominio.
> **F3: Adaptadores de Datos** completada el 2026-05-18. Specs Spec-30/31/32 en estado Completado. 17 tareas implementadas, 98 tests unitarios + 43 tests de integración (100% pass), cobertura 96.30%. 4 repositorios Postgres (movement, product, category, stock_query), 3 mappers, vista materializada `mv_stock_historical` con refresh concurrente y fallback, Unit of Work con context manager. Documentación auditada 10/10. Lista para F4.
> **F4: Capa API** completada el 2026-05-18. Specs Spec-40/41/42 en estado Completado. 6 use cases, 5 DTOs, 4 routers (10 endpoints), error mapping middleware, DI factories. 147 unit tests pasan. `make lint` limpio. Version 0.4.0. Lista para F5.

## Detailed Docs

- [Roadmap y Fases](docs/workflow/roadmap-phases.md) — Timeline, milestones, hitos clave
- [Seguimiento de Specs](docs/workflow/spec-tracking.md) — Tabla de specs, estados, dependencias
- [Grafos de Dependencia](docs/workflow/dependency-graphs.md) — Diagramas Mermaid de fases y specs
- [Reglas de Proceso](docs/workflow/process-rules.md) — Workflow spec-driven, aprobaciones, convenciones
- [Matriz de Stakeholders](docs/workflow/stakeholder-matrix.md) — Roles, contactos, responsabilidades
