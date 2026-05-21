# SPEC-10: DB Configuration

## Description

Configure PostgreSQL 16+ connection with `asyncpg`, connection pooling managed by FastAPI lifespan, and health endpoint with connectivity verification.

## Phase

F1 — DB Infrastructure

## Involved Files

- `src/infrastructure/db/connection.py` — asyncpg connection pool: `init_pool()`, `close_pool()`, `get_pool()`, `get_db()`
- `src/main.py` — FastAPI lifespan that initializes and closes the pool
- `src/adapters/api/routers/health.py` — Endpoint `GET /v1/health` with `SELECT 1`
- `docker-compose.yml` — PostgreSQL 16-alpine service with healthcheck

## Acceptance Criteria

- [x] `init_pool(Settings())` creates asyncpg pool with configurable `min_size` and `max_size` via Settings (`db_pool_min_size`, `db_pool_max_size`, default: 2 and 10)
- [x] Pool initializes on FastAPI startup and closes on shutdown (lifespan)
- [x] `get_pool()` returns the active pool or `None` if not initialized
- [x] `get_db()` is a FastAPI dependency that injects the pool into endpoints
- [x] `GET /v1/health` returns `{"status": "ok", "db": "connected"}` with DB available
- [x] `GET /v1/health` returns `{"status": "degraded", "db": "unavailable"}` without DB
- [x] Pool initialization failure is graceful in development (log warning, pool=None)
- [x] In **production**, `init_pool()` raises `RuntimeError` if DB is not available (no silent startup)
- [x] `statement_timeout` for API queries is configured with **parameterized SQL** (`SET statement_timeout = $1`), not f-string
- [x] Testcontainers DSN converted from `postgresql+psycopg2://` to `postgresql://` for asyncpg
- [x] Unit tests for health endpoint validate both scenarios

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| Pool size configurable via Settings | Allows adjustment without modifying code. Default 2-10 balances resources and concurrency |
| Production fail-hard | In production, do not allow silent startup without DB — better to crash than run invisible degraded service |
| Parameterized SQL (`$1`) | `SET statement_timeout = $1` follows asyncpg convention and prevents SQL injection even for numeric values |
| Graceful fallback in development | DB may not be ready during early startup in dev mode |
| Health degraded (no HTTP error) | Informational indicator, not an error — the app works without data |
| Module-level singleton | Pool managed by lifespan, no class needed |

## Dependencies

Spec-02 (Development Environment)

## Status

**Completed** — 2026-05-15
