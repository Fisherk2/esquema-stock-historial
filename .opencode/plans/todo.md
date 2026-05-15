# F0 Task List: stock-historial — Preparación

**Status:** COMPLETED (2026-05-14)

## Task 1: pyproject.toml + requirements.txt

**Description:** Create the project's central configuration file and pin all F0 dependencies.

**Acceptance criteria:**
- [x] `pyproject.toml` exists with project metadata, ruff, black, pytest, mypy configs
- [x] `requirements.txt` lists all F0 deps pinned: fastapi, uvicorn, pydantic, pydantic-settings, asyncpg, apscheduler, pytest, pytest-asyncio, httpx, testcontainers, ruff, black, freezegun, mypy
- [x] `pip install -r requirements.txt` succeeds
- [x] `ruff --version` and `black --version` return valid versions

**Verification:**
- `pip install -r requirements.txt && ruff check --version && python -c "import fastapi"`

**Dependencies:** None
**Files likely touched:**
- `pyproject.toml`
- `requirements.txt`
**Estimated scope:** Small (2 files)

---

## Task 2: Makefile

**Description:** Replace stub with real developer commands that delegate to pyproject.toml-configured tools.

**Acceptance criteria:**
- [x] `make install` installs dependencies
- [x] `make lint` runs ruff and exits 0 (no source code yet)
- [x] `make format` runs black + ruff fix
- [x] `make test` runs pytest and exits 0 (no tests yet)
- [x] `make dev` starts uvicorn with src.main:app
- [x] `make build`, `make docker-up`, `make docker-down` targets exist

**Verification:**
- `make lint && make test && make format`

**Dependencies:** Task 1
**Files likely touched:**
- `Makefile`
**Estimated scope:** Small (1 file)

---

## Checkpoint: Foundation

- [x] `pip install -r requirements.txt` succeeds
- [x] `make lint` and `make test` exit green
- [x] Review with human before proceeding

---

## Task 3: src/ package tree + main.py with health endpoint

**Description:** Add `__init__.py` to every package dir, create FastAPI app factory with health endpoint, and pydantic-settings config.

**Acceptance criteria:**
- [x] Every dir under `src/` has `__init__.py`
- [x] `src/core/__init__.py` and `src/core/config.py` exist with `Settings` class (pydantic-settings)
- [x] `src/main.py` has `create_app()` factory returning a FastAPI instance
- [x] `src/adapters/api/routers/health.py` has `GET /health` returning `{"status": "ok"}`
- [x] `make dev` starts uvicorn; `curl http://localhost:8000/health` returns 200 + `{"status": "ok"}`
- [x] `make lint` passes on new files

**Verification:**
- `make dev &` then `curl http://localhost:8000/health`; kill uvicorn
- `make lint`

**Dependencies:** Task 2
**Files likely touched:**
- `src/__init__.py`
- `src/core/__init__.py`
- `src/core/config.py`
- `src/domain/__init__.py`
- `src/domain/entities/__init__.py`
- `src/domain/value_objects/__init__.py`
- `src/domain/exceptions/__init__.py`
- `src/domain/rules/__init__.py`
- `src/domain/ports/__init__.py`
- `src/application/__init__.py`
- `src/application/use_cases/__init__.py`
- `src/application/dtos/__init__.py`
- `src/application/interfaces/__init__.py`
- `src/infrastructure/__init__.py`
- `src/infrastructure/db/__init__.py`
- `src/infrastructure/repositories/__init__.py`
- `src/infrastructure/scheduler/__init__.py`
- `src/infrastructure/logging/__init__.py`
- `src/adapters/__init__.py`
- `src/adapters/api/__init__.py`
- `src/adapters/api/routers/__init__.py`
- `src/adapters/api/routers/health.py`
- `src/adapters/api/middleware/__init__.py`
- `src/adapters/api/dependencies.py`
- `src/main.py`
**Estimated scope:** Medium (many tiny files + 3 real files)

---

## Task 4: tests/conftest.py + health smoke test

**Description:** Create shared test fixtures and a smoke test that verifies the health endpoint via async HTTP client.

**Acceptance criteria:**
- [x] `tests/conftest.py` has `async_client` fixture using `httpx.AsyncClient` + `ASGITransport`
- [x] `tests/unit/test_health.py` hits `/health` and asserts status 200 + `{"status": "ok"}`
- [x] `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/e2e/__init__.py` exist
- [x] `make test` passes

**Verification:**
- `make test`

**Dependencies:** Task 3
**Files likely touched:**
- `tests/conftest.py`
- `tests/unit/__init__.py`
- `tests/unit/test_health.py`
- `tests/integration/__init__.py`
- `tests/e2e/__init__.py`
**Estimated scope:** Small (4 files)

---

## Checkpoint: App Skeleton

- [x] `make dev` starts FastAPI
- [x] `GET /health` returns `{"status": "ok"}`
- [x] `make test` passes the health smoke test
- [x] Review with human before proceeding

---

## Task 5: Dockerfile + docker-compose.yml

**Description:** Replace stubs with a multi-stage Dockerfile and dev docker-compose with PostgreSQL 16 + app, both with healthchecks.

**Acceptance criteria:**
- [x] `Dockerfile` has builder stage (install deps) and runtime stage (copy app, run uvicorn)
- [x] `docker-compose.yml` has `db` service (PostgreSQL 16 with healthcheck) and `app` service (with healthcheck hitting `/health`)
- [x] `docker compose up -d` starts both containers
- [x] `docker compose ps` shows both healthy after ~10s

**Verification:**
- `make docker-up && sleep 10 && docker compose ps && curl http://localhost:8000/health && make docker-down`

**Dependencies:** Task 3
**Files likely touched:**
- `Dockerfile`
- `docker-compose.yml`
**Estimated scope:** Small (2 files)

---

## Task 6: .env.example + DB connection config

**Description:** Document all required env vars and create a placeholder asyncpg connection module.

**Acceptance criteria:**
- [x] `.env.example` lists: `DATABASE_URL`, `APP_HOST`, `APP_PORT`, `LOG_LEVEL`, `ENVIRONMENT`
- [x] `src/infrastructure/db/connection.py` has asyncpg pool placeholder (init on startup, close on shutdown)
- [x] App starts with `make dev` reading config from env; no crash if DB unreachable (graceful log)
- [x] `make lint` passes on new files

**Verification:**
- `make dev` with `.env` values loads without error
- `make lint`

**Dependencies:** Task 5
**Files likely touched:**
- `.env.example`
- `src/infrastructure/db/connection.py`
**Estimated scope:** Small (2 files)

---

## Checkpoint: Containerization

- [x] `docker compose up` starts PostgreSQL + app
- [x] Healthchecks pass for both containers
- [x] `.env.example` lists all required env vars
- [x] Review with human before proceeding

---

## Task 7: .pre-commit-config.yaml

**Description:** Configure pre-commit hooks for automated quality enforcement on every commit.

**Acceptance criteria:**
- [x] `.pre-commit-config.yaml` has hooks: ruff (lint + fix), black, trailing-whitespace-fixer, end-of-file-fixer, check-yaml
- [x] `pre-commit run --all-files` passes
- [x] `git commit` triggers hooks automatically

**Verification:**
- `pre-commit install && pre-commit run --all-files`

**Dependencies:** Task 1
**Files likely touched:**
- `.pre-commit-config.yaml`
**Estimated scope:** Small (1 file)

---

## Task 8: Clean Architecture import rules + CI stub

**Description:** Enforce and document Clean Architecture layer boundaries, and create a CI workflow stub.

**Acceptance criteria:**
- [x] `pyproject.toml` has ruff rule or `import-linter` config to flag domain importing from infrastructure/adapters
- [x] `docs/agents/architecture-design.md` updated with enforcement section documenting import rules
- [x] `.github/workflows/ci.yml` runs lint + test on push to main and PRs
- [x] `make lint` catches a domain file importing from infrastructure (tested with temp violation)
- [x] `make lint` passes after removing temp violation

**Verification:**
- Create temp file `src/domain/test_violation.py` with `from src.infrastructure.db.connection import pool`, run `make lint`, confirm error. Delete temp file, confirm `make lint` passes.
- Push to branch and confirm CI triggers (or verify workflow YAML is valid with `actionlint`)

**Dependencies:** Task 7
**Files likely touched:**
- `pyproject.toml`
- `docs/agents/architecture-design.md`
- `.github/workflows/ci.yml`
**Estimated scope:** Medium (3 files)

---

## Checkpoint: Complete

- [x] `make lint` passes with 0 errors
- [x] `make test` exits green
- [x] `make dev` starts FastAPI; `GET /health` returns `{"status": "ok"}`
- [x] `docker compose up` starts PostgreSQL + app with healthchecks
- [x] Pre-commit hooks run ruff + black on commit
- [x] `pyproject.toml` configures ruff, black, pytest, mypy
- [x] Clean Architecture import rules documented and enforceable
- [x] `.env.example` lists all required environment variables
- [x] `requirements.txt` has all F0 dependencies pinned
- [x] Ready for review
