# Process Rules

## Spec-Driven Workflow

1. **Specification before Code:** No implementation file (`*.py`, `*.sql`) will be created without a validated `specs/SPEC-XX.md` with contracts, payloads, and acceptance criteria.
2. **Strict DAG Order:** A spec only transitions to `In Progress` when **all** its dependencies are `Completed`. Skipping dependencies breaks traceability and is automatically rejected.
3. **Dependency Direction (Clean Architecture):** Code always points toward the domain. `infrastructure` → `application` → `domain`. DIP is applied via `typing.Protocol` and mocks in testing.
4. **Immutability and Append-Only:** The `movements` table is sacred. Direct `UPDATE`/`DELETE` is prohibited. Corrections via compensatory movements (`type: ADJUSTMENT`).
5. **Explicit SQL and Optimization:** Analytical queries use native CTEs/Window Functions. Using ORM for historical stock queries is prohibited. Each complex query must include its `EXPLAIN ANALYZE`.
6. **Testing with Testcontainers:** Integration tests **do not** mock PostgreSQL. `testcontainers.postgres` is used for 1:1 behavior with production.
7. **Commits and Versioning:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`). Each merge to `main` must close a complete spec.
8. **Technical Debt Review:** If a spec has been pending or blocked for >48h, dependent specs are stopped and escalated for risk analysis.

## Notes for Agentic AI

1. Always inject architecture constraints (SRP, DIP, Immutability, Explicit SQL, Testcontainers). If a request contradicts these principles, explicitly reject it and propose an aligned alternative.
2. Before writing implementation, verify that the spec exists, has defined contracts, and its dependencies are completed. If information is missing, request clarification.
3. Maintain a mental record of the current state of each spec. When generating code, implicitly update the checklist and notify the user.
4. Apply Clean Architecture, Spec-Driven Development, and SOLID concepts to justify technical decisions.
5. If a query exceeds `<100ms` in E2E tests, validate `EXPLAIN` first, then adjust partial indexes or narrow date ranges. Document in the spec.
6. Maintain a technical, pedagogical, and direct tone. Use Mermaid for diagrams, tables for contracts, and code blocks with syntax highlighting.
