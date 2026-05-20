# TODO — F7: Despliegue & Documentación

## Progress: [0/14] ░░░░░░░░░░░░░░ PENDIENTE

## Phase 1: SPEC-70 — Docker Production Infrastructure [0/5]

- [ ] **Task 1:** Harden Dockerfile (non-root user, OCI labels, --chown)
  - `Dockerfile` — +`groupadd`/`useradd` (uid=1000, gid=1000), +5 OCI labels, `COPY --chown=app:app`, `USER app`
  - Verify: `docker build -t stock-historial:latest .` OK, `docker run --rm stock-historial:latest id` → `uid=1000(app)`

- [ ] **Task 2:** Crear .dockerignore
  - `.dockerignore` — excluir `.git/`, `__pycache__/`, `.venv/`, `.mypy_cache/`, `.ruff_cache/`, `docs/ai-agent-setup/`, `.opencode/`, `skills/`, `agents/`, `references/`, `specs/`, `scripts/`, `.env*`
  - Verify: `docker build -t stock-historial:latest .` OK (contexto reducido)

- [ ] **Task 3:** Crear docker-compose.prod.yml
  - `docker-compose.prod.yml` — app + db, PostgreSQL sin puerto expuesto, `restart: unless-stopped`, vars desde `.env`
  - Verify: `docker compose -f docker-compose.prod.yml config` OK, `docker compose -f docker-compose.prod.yml up -d` + healthcheck OK

- [ ] **Task 4:** Expandir .env.example (6 → 17 variables)
  - `.env.example` — +APP_NAME, +LOG_FORMAT, +scheduler vars (F5), +POSTGRES_USER/PASSWORD/DB (F7), +DEMO_BASE_URL
  - Verify: `grep -c "=" .env.example` → 17+

- [ ] **Task 5:** Añadir comandos Makefile (demo, docker-prod-up, docker-prod-down)
  - `Makefile` — +`.PHONY` entries, +3 targets, +3 help lines
  - Verify: `make help | grep -E "demo|docker-prod-up|docker-prod-down"` → 3 líneas

### Checkpoint: SPEC-70 Complete [ ]
- [ ] Dockerfile: `USER app`, OCI labels, `--chown=app:app`
- [ ] `.dockerignore`: 15+ patrones excluidos
- [ ] Prod stack arranca: app + db, PostgreSQL no expuesto
- [ ] `.env.example`: 17 variables documentadas
- [ ] Makefile: demo, docker-prod-up, docker-prod-down
- [ ] `docker build` OK, non-root user verificado
- [ ] `make lint` pasa, 0 regresiones en 205+ tests
- [ ] **Revisar con humano antes de continuar**

---

## Phase 2: SPEC-71 — Documentation & Demo [0/6]

- [ ] **Task 6:** Crear scripts/demo.sh
  - `scripts/demo.sh` — 9 pasos: health → categoría → producto → IN → stock → OUT → stock → histórico → movimientos
  - `set -euo pipefail`, `curl -sf`, `DEMO_BASE_URL`, `python3 -m json.tool`
  - Verify: `make demo` exit 0 (con servidor), `DEMO_BASE_URL=http://invalid:9999 make demo` exit ≠ 0

- [ ] **Task 7:** Reescribir README.md a v1.0.0
  - `README.md` — badges, features, stack, commands, quick start (3 pasos), estructura, docs, API endpoints (11), estado
  - Verify: links internos válidos, tabla API con 11 filas, quick start con 3 pasos

- [ ] **Task 8:** Reescribir docs/ARCHITECTURE.md
  - `docs/ARCHITECTURE.md` — overview, diagrama capas (Mermaid), capas detalladas, patrones, decisiones, reglas importación (tabla), diagrama datos (ER), diagrama request flow (sequence)
  - Verify: 3 bloques Mermaid, tabla importación con 4 filas

- [ ] **Task 9:** Reescribir docs/API_REFERENCE.md
  - `docs/API_REFERENCE.md` — overview, error format, error codes table, 11 endpoints con curl + error examples, paginación
  - Verify: 11 secciones de endpoint, cada una con curl + error example

- [ ] **Task 10:** Reescribir docs/SETUP.md
  - `docs/SETUP.md` — prereqs, install, dev local, Docker dev, Docker prod, demo, tabla 17 env vars, troubleshooting (6+)
  - Verify: tabla env vars con 17 filas, tabla troubleshooting con 6+ filas

- [ ] **Task 11:** Reescribir CONTRIBUTING.md
  - `CONTRIBUTING.md` — setup, workflow, commits (`type(scope): desc`), calidad, typecheck, coverage, arquitectura, testing, PR
  - Verify: convención commits con tipos (feat, fix, docs...), scopes (domain, application...)

### Checkpoint: SPEC-71 Complete [ ]
- [ ] Demo script funciona end-to-end
- [ ] README v1.0.0 con badges y quick start
- [ ] 3 diagramas Mermaid en ARCHITECTURE.md
- [ ] 11 endpoints documentados con curl + errores
- [ ] SETUP.md con tabla de 17 variables y troubleshooting
- [ ] CONTRIBUTING.md con convenciones y flujo PR
- [ ] Todos los links internos válidos
- [ ] `make lint` pasa, 0 regresiones
- [ ] **Revisar con humano antes de continuar**

---

## Phase 3: SPEC-72 — CI/CD Pipeline [0/1]

- [ ] **Task 12:** Reescribir .github/workflows/ci.yml (5 gates)
  - `.github/workflows/ci.yml` — 5 jobs: lint → typecheck → test → coverage (3 sub-gates) → docker-build
  - Coverage: global ≥80%, domain ≥90%, application ≥85%
  - Docker: `setup-buildx-action@v3`, `build-push-action@v6`, `push: false`, `type=gha` cache
  - Verify: YAML válido, 5 jobs con `needs` correctos, 3 sub-steps en coverage

### Checkpoint: SPEC-72 Complete [ ]
- [ ] 5 gates secuenciales con fail-fast
- [ ] Coverage sub-gates: ≥80% / ≥90% / ≥85%
- [ ] Docker build gate con cache GHA
- [ ] No deploy automático
- [ ] `make lint` pasa, 0 regresiones
- [ ] **Revisar con humano antes de continuar**

---

## Phase 4: Validation & Documentation Update [0/2]

- [ ] **Task 13:** Build completo + smoke tests
  - `make lint` + `make typecheck` + `make test` + coverage gates
  - `docker build` + non-root user + prod stack + healthcheck + demo script
  - Verify: `make build` exit 0, Docker smoke tests pasan

- [ ] **Task 14:** Actualizar documentación del proyecto
  - `WORKFLOW.md` — F7 "Completada"
  - `docs/workflow/spec-tracking.md` — SPEC-70/71/72 [17/17] [12/12] [14/14]
  - `SPEC.md` — F7 ✅, versión 1.0.0
  - `AGENTS.md` — Fase F7 completada
  - Verify: archivos actualizados y precisos

### Checkpoint: F7 Complete [ ]
- [ ] Todos los criterios de SPEC-70/71/72 cumplidos
- [ ] `make build` pasa
- [ ] Docker build OK, non-root user verificado
- [ ] Prod stack arranca y healthcheck pasa
- [ ] Demo script funciona
- [ ] CI/CD pipeline con 5 gates
- [ ] Toda la documentación reescrita y precisa
- [ ] Versión 1.0.0
- [ ] Listo para revisión humana → Release

---

## Summary

| Phase | Tasks | Completed | Type |
|-------|-------|-----------|------|
| Phase 1: SPEC-70 Docker Prod | 5 | 0/5 | Infrastructure |
| Phase 2: SPEC-71 Docs & Demo | 6 | 0/6 | Documentation |
| Phase 3: SPEC-72 CI/CD | 1 | 0/1 | Infrastructure |
| Phase 4: Validation & Docs | 2 | 0/2 | Validation |
| **Total** | **14** | **0/14** | — |

---

## Implementation Order Reference

```
Tasks 1, 2, 4 (parallel: Dockerfile + .dockerignore + .env.example)
↓
Task 3 (docker-compose.prod.yml) ←── needs Task 1
↓
Task 5 (Makefile additions) ←── needs Task 3
↓
Tasks 6, 7, 8, 9 (parallel: demo.sh + README + ARCHITECTURE + API_REFERENCE)
↓
Task 10 (SETUP.md) ←── needs Tasks 4, 5
↓
Task 11 (CONTRIBUTING.md) ←── needs Task 10
↓
Task 12 (CI/CD) ←── needs Task 1 (can start earlier, but Dockerfile must be ready)
↓
Task 13 (full validation) ←── needs ALL
↓
Task 14 (documentation update) ←── needs Task 13
```
