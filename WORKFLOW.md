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
> **F5: Scheduler & Concurrencia** completada el 2026-05-19. Specs Spec-50/51/52 en estado Completado.
> **F6: Testing Integral** completada el 2026-05-20. Specs Spec-60/61/62/63 en estado Completado.
> **F7: Despliegue & Documentación** completada el 2026-05-20. Specs Spec-70/71/72 en estado Completado.
> **Version 1.0.0 — lista para producción.**
> **Hardening post-v1.0.0 /ship review:** 2 commits de hardening aplicados tras revision /ship (3-axis: code-reviewer, security-auditor, test-engineer).
> **Revisión Post-F7 (F0→F3):** Hardening aplicado tras code review 5-axis. 14 cambios aplicados: nuevas excepciones de dominio, `BasePostgresRepository` abstracto, entidades `frozen=True`, `MovementType` → `StrEnum`, SQL parametrizado, pool configurable, migraciones non-transactional, UoW rollback seguro, eliminación de `json.dumps()`, validación centralizada en `Movement.__post_init__`, manejo `JSONDecodeError` en mappers. 211 tests pasando, `make lint` limpio.
> **Revisión Post-F7 (F4→F5):** Hardening aplicado tras code review 5-axis de capas API y Scheduler. 5 correcciones: (1) SQL injection latente en scheduler.py `SET LOCAL` → query parametrizada `$1` (Critical), (2) `assert` reemplazado por `HTTPException(500)` en products.py y categories.py (seguro con `-O`) (Important), (3) Retry decorator `exceptions` default cambiado de `(Exception,)` a `()` con validación `ValueError` (Important), (4) `extra="forbid"` agregado a `CreateProductInput` y `CreateCategoryInput` (Suggestion), (5) `metadata` tipo actualizado a `dict[str, Any]` (Suggestion). 212 tests pasando, `make lint` limpio.
> **Revisión Post-F7 (F6+F7 — 5-Axis Review Fixes):** Hardening aplicado tras code review post-release de cambios F6/F7. 6 correcciones: (1) **Critical:** `Movement.__post_init__` delega a `validate_movement_type_consistency()` — single source of truth (SPEC-21), (2) **Pre-existing bug:** SQL constants restauradas en `PostgresProductRepository` y `PostgresCategoryRepository` (perdidas en refactor `BasePostgresRepository`), (3) CI coverage gate consolidado: 1× pytest run → 3 verificaciones de umbral (3× menos tiempo CI), (4) `db_pool` fixture usa `Settings` pool sizes configurables, (5) docstrings actualizados en `movement_consistency.py`, (6) campos docker-only en `Settings` documentados. 212 tests pasando, `make lint` + `make typecheck` limpios.

## Detailed Docs

- [Roadmap y Fases](docs/workflow/roadmap-phases.md) — Timeline, milestones, hitos clave
- [Seguimiento de Specs](docs/workflow/spec-tracking.md) — Tabla de specs, estados, dependencias
- [Grafos de Dependencia](docs/workflow/dependency-graphs.md) — Diagramas Mermaid de fases y specs
- [Reglas de Proceso](docs/workflow/process-rules.md) — Workflow spec-driven, aprobaciones, convenciones
- [Matriz de Stakeholders](docs/workflow/stakeholder-matrix.md) — Roles, contactos, responsabilidades
