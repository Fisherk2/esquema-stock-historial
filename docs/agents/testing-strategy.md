# Testing Strategy

## Testing Phases

1. **Unit:** Validate pure business logic and DTO mapping. No real DB. Use `unittest.mock` or `pytest-mock` against protocols.
2. **Integration:** Spin up ephemeral PostgreSQL with `testcontainers.postgres`. Execute migration SQL scripts, insert fixtures, validate view and query results.
3. **E2E / Contract:** Launch FastAPI server in test mode. Simulate HTTP requests, validate JSON responses against Pydantic schemas and measure `<100ms` latency.

## Frameworks and Patterns

- **Pytest + pytest-asyncio:** Standard for async code.
- **Factory Boy:** Deterministic test fixture generation.
- **SQLAlchemy Core (tests only):** Optional use for fast seed data without compromising the prod layer.
- **Isolation:** Each test suite is transactional. Automatic post-test rollback. Containers destroyed after CI completes.

## Integration Fixtures

### Fixture Architecture

Integration tests use **a single PostgreSQL container per session**, with cleanup between tests via TRUNCATE + re-seed:

| Fixture | Scope | Purpose | When to use |
|---------|-------|-----------|-------------|
| `db_pool` | `session` | 1 container, migrations + seed at start | Structure tests (tables, indexes, triggers) |
| `db_clean` | `function` | TRUNCATE + re-seed + refresh MV before each test | Tests that insert/query data (repos, API) |
| `api_client` | `function` | FastAPI app + `db_clean` + HTTP client | HTTP tests for endpoints |

### Benefits

- **Before:** ~88 containers per session → ~20 minutes
- **After:** 1 container per session → ~20 seconds
- **Reduction:** ~99% less container overhead

### Implementation

```python
# tests/conftest.py (project root)
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """1 session-scoped container: migrations + seed + MV."""

@pytest_asyncio.fixture(scope="function")
async def db_clean(db_pool: asyncpg.Pool) -> AsyncGenerator[asyncpg.Pool, None]:
    """Clean data per test: TRUNCATE + re-seed + refresh MV."""
```

The `db_pool` and `db_clean` fixtures are defined in `tests/conftest.py`
(root) and are automatically available in `tests/integration/`,
`tests/e2e/` and `tests/security/` thanks to pytest's conftest mechanism.
The `db_pool` fixture uses `Settings.db_pool_min_size` and `db_pool_max_size`
for consistency with production configuration.

### Rules

1. **Never define `db_pool` locally** in test files (avoids duplicates that shadow the shared fixture).
2. **Use `db_clean`** for tests that insert/read data (repos, API, schema with inserts).
3. **Use `db_pool`** for tests that only verify structure (tables, columns, indexes, ENUMs).
4. **`api_client`** depends on both: `db_clean` for clean data, `db_pool` for DI override.

## Quality Metrics

- **Coverage:** `>85%` in `domain/` and `application/`. `>70%` in `infrastructure/`. Global `>80%`.
- **Total tests:** 477 — unit + integration + e2e + security.
- **Cyclomatic Complexity:** `<10` per function. If exceeded, refactor with SRP.
- **Technical Debt:** Zero critical `FIXME` or `TODO` on `main` branch.

### New types of integration tests

| Type | Covers | Example |
|------|-------|---------|
| Security headers | Verifies headers in responses | `X-Content-Type-Options: nosniff` present |
| Pagination bounds | Validation of limit/offset | `limit=0` → 422, `limit=1001` → 422 |
| Timezone handling | Datetime naive → UTC | `_ensure_timezone_aware` unit + integration |
| Error handler origin | Traceback verification | ValueError from DTO → 400, from infra → 500 |

## Mocking and Isolation

- **DB Mocking:** In unit tests, inject `MockRepository` that returns `AsyncMock`.
- **Scheduler Mocking:** `APScheduler` is disabled in `TESTING` mode. Job registration is verified, not actual execution.
- **Time Mocking:** `freezegun` to validate deterministic historical queries.
