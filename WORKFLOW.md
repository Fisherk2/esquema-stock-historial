# WORKFLOW.md

**Project Name:** Historical Inventory & Date-Based Stock
**Version:** 1.0.0
**Current Status:** F7 Completed ✅ — Version 1.0.0 (production)
**Owner:** Fisherk2 (Lead Developer / Architect)

Inventory management system with Immutable Source of Truth, REST API, and historical stock in `<100ms`.

> **F0: Preparation** completed on 2026-05-14. All specs (01-04) in Completed state.
> **F1: DB Infrastructure** completed on 2026-05-15. Specs Spec-10/11/12 in Completed state.
> **F2: Domain Core** completed on 2026-05-15. Specs Spec-20/21/22 in Completed state. 89 unit tests, 99.56% domain coverage.
> **F3: Data Adapters** completed on 2026-05-18. Specs Spec-30/31/32 in Completed state. 17 tasks implemented, 98 unit tests + 43 integration tests (100% pass), 96.30% coverage. 4 Postgres repositories (movement, product, category, stock_query), 3 mappers, materialized view `mv_stock_historical` with concurrent refresh and fallback, Unit of Work with context manager. Documentation audited 10/10. Ready for F4.
> **F4: API Layer** completed on 2026-05-19. Specs Spec-40/41/42 in Completed state.
> **F5: Scheduler & Concurrency** completed on 2026-05-19. Specs Spec-50/51/52 in Completed state.
> **F6: Comprehensive Testing** completed on 2026-05-20. Specs Spec-60/61/62/63 in Completed state.
> **F7: Deployment & Documentation** completed on 2026-05-21. Specs Spec-70/71/72 in Completed state.
> **Version 1.0.0 — production ready.**

## Detailed Docs

- [Roadmap and Phases](docs/workflow/roadmap-phases.md) — Timeline, milestones, key deliverables
- [Spec Tracking](docs/workflow/spec-tracking.md) — Spec table, states, dependencies
- [Dependency Graphs](docs/workflow/dependency-graphs.md) — Mermaid diagrams of phases and specs
- [Process Rules](docs/workflow/process-rules.md) — Spec-driven workflow, approvals, conventions
- [Stakeholder Matrix](docs/workflow/stakeholder-matrix.md) — Roles, contacts, responsibilities
