# Matriz de Stakeholders

| Rol | Nombre | Contacto | Responsabilidades |
|-----|--------|----------|-------------------|
| Arquitecto/Dev Principal | Fisherk2 | GitHub/Local | Diseño, implementación, revisión de specs, mantenimiento de `AGENTS.md` y `WORKFLOW.md` |
| QA / Tester Automatizado | CI/CD Pipeline | GitHub Actions | Validación de contratos, ejecución de tests, métricas de cobertura |
| Reviewer Técnico | Portfolio Evaluator | GitHub PRs | Validación de SLA, calidad arquitectónica, trazabilidad de specs |

## Referencias

| Documento | Ruta | Propósito |
|-----------|------|-----------|
| AGENTS.md | `/AGENTS.md` | Fuente de verdad arquitectónica, patrones, guías SOLID, prohibiciones |
| WORKFLOW.md | `/WORKFLOW.md` | Orden de ejecución y trazabilidad de specs |
| README.md | `/README.md` | Onboarding, setup local, estructura del proyecto |
| specs/ | `/specs/` | Specs individuales con contratos, SQL, fixtures |
| docs/openapi.json | `/docs/openapi.json` | Contrato REST generado desde FastAPI/Pydantic |
| CONTRIBUTING.md | `/CONTRIBUTING.md` | Guía de estilo, pre-commit hooks, flujo de PRs |
