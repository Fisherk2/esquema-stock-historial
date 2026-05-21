# Tooling and CI/CD

## Linting and Formatting

- **Linter:** `ruff` — configuration in `pyproject.toml` (when it exists).
- **Formatter:** `black` + `isort` — apply before each commit.
- **Pre-commit hooks:** Configured via `.pre-commit-config.yaml`.

## Testing

- **Framework:** `pytest` + `pytest-asyncio`.
- **DB in tests:** `testcontainers.postgres` for integrations (do not mock PostgreSQL).
- **Fixtures:** `Factory Boy` for deterministic data.
- **Coverage:** `>85%` domain, `>70%` infrastructure.

## CI/CD

- **Platform:** GitHub Actions (`.github/workflows/`).
- **Pipeline stages (F0 active):** lint → test → coverage
- **Pipeline stages (F7 pending):** build → staging deploy (Spec-72)
- **Quality gates:** Ruff without warnings, tests passing, coverage `>=80%`.

## Docker

- **Dev:** `docker-compose.yml` with ephemeral PostgreSQL.
- **Prod:** `Dockerfile` multi-stage + `docker-compose.prod.yml` (Spec-70, F7).
- **Healthchecks:** Healthcheck endpoint in FastAPI.
