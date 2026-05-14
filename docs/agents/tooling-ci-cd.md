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
- **Pipeline stages:** lint → test (unit + integration) → coverage → build → (staging deploy).
- **Quality gates:** Ruff sin warnings, tests passing, cobertura umbrales.

## Docker

- **Dev:** `docker-compose.dev.yml` con PostgreSQL efímero.
- **Prod:** `Dockerfile` multi-stage + `docker-compose.prod.yml`.
- **Healthchecks:** Endpoint de healthcheck en FastAPI.
