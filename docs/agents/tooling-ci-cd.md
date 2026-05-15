# Tooling y CI/CD

## Linter y Formateo

- **Linter:** `ruff` — configuración en `pyproject.toml` (cuando exista).
- **Formatter:** `black` + `isort` — aplicar antes de cada commit.
- **Pre-commit hooks:** Configurados vía `.pre-commit-config.yaml`.

## Testing

- **Framework:** `pytest` + `pytest-asyncio`.
- **DB en tests:** `testcontainers.postgres` para integraciones (no mockear PostgreSQL).
- **Fixtures:** `Factory Boy` para datos deterministas.
- **Cobertura:** `>85%` dominio, `>70%` infraestructura.

## CI/CD

- **Plataforma:** GitHub Actions (`.github/workflows/`).
- **Pipeline stages (F0 activo):** lint → test → coverage
- **Pipeline stages (F7 pendiente):** build → staging deploy (Spec-72)
- **Quality gates:** Ruff sin warnings, tests passing, cobertura `>=80%`.

## Docker

- **Dev:** `docker-compose.yml` con PostgreSQL efímero.
- **Prod:** `Dockerfile` multi-stage + `docker-compose.prod.yml` (Spec-70, F7).
- **Healthchecks:** Endpoint de healthcheck en FastAPI.
