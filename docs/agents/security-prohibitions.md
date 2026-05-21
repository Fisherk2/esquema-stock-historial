# Security and Prohibitions

## Validation and Sanitization

- **Inputs:** Pydantic validates types, ranges, UUID/ISO8601 formats. Automatic rejection of malformed payloads (`HTTP 422`).
- **SQL Injection:** Zero tolerance. Strict use of positional/named parameters (`$1`, `$2`). Never string concatenation for queries, including `SET` statements (e.g., `SET statement_timeout = $1`, not f-string).
- **JSONB:** asyncpg handles `dict → JSONB` natively. Never use `json.dumps()` for JSONB parameters — this duplicates serialization and can cause double-encoding.
- **Secrets:** `.env` never versioned. Sensitive variables loaded via `pydantic-settings`. Automatic rotation in CI.

## Exception Control and Limits

- **Rate Limiting:** Basic middleware in FastAPI (`slowapi` or manual) for bulk read endpoints.
- **Deadlines:** Explicit timeouts in `asyncpg.connect()`. Implicit circuit breaker via retry limits.
- **Logging:** Structured (JSON). Never log sensitive data or full stacks in prod.

## Prohibited Practices

1. Hardcoded credentials, URLs, or SQL queries in code.
2. Hidden side-effects: functions that read/write to the DB without being declared as such.
3. Temporal coupling: logic that depends on implicit execution order of imports or global modules.
4. God Objects / Fat Controllers: classes >300 lines or functions with multiple responsibilities.
5. ORM for complex analytical queries: SQLAlchemy ORM for CTEs/Window Functions is prohibited.
6. `print()` in production. Use `logging` or `structlog`.
7. Ignoring `async/await`: mixing synchronous code in async routes blocks the event loop.
8. Modifying historical data: `UPDATE` or `DELETE` on `movements` table. Only `INSERT`. If there is an error, insert a compensatory movement.

## MVP Security Status (Pre-Production)

> **Note:** This project in its current state is an **MVP without real production deployment**. The following limitations are known and must be resolved before a production deployment.

### Known MVP Limitations

| Component | MVP Status | Pre-Production Requirement |
|---|---|---|
| **Authentication** | ❌ Not implemented | API keys or JWT/OAuth2 with RBAC |
| **Authorization** | ❌ Not implemented | Roles: admin, warehouse, readonly |
| **Rate Limiting** | ❌ Not implemented | `slowapi` or manual middleware |
| **CORS** | ❌ Not implemented | `CORSMiddleware` with origin allowlist |
| **OpenAPI Docs** | ⚠️ Active in prod | Disable `/docs`, `/redoc`, `/openapi.json` |
| **Security Headers** | ✅ Implemented | `nosniff`, `deny`, `no-store`, `referrer-policy` |
| **SQL Injection** | ✅ Prevented | asyncpg parameterized in all queries |
| **Input Validation** | ✅ Implemented | Pydantic `strict=True`, `extra="forbid"` |
| **Error Handling** | ✅ Implemented | No stack trace leakage. ValueError handler verifies traceback origin. |
| **Race Conditions** | ✅ Prevented | `SELECT FOR UPDATE` + direct calculation inside UoW |
| **Statement Timeout** | ✅ Enforcement | `server_settings` in pool — applies to all connections |

### Pre-production deployment checklist

Before deploying to production, complete:

- [ ] Implement authentication (API key or JWT)
- [ ] Configure role-based authorization
- [ ] Add rate limiting (slowapi)
- [ ] Configure CORS with specific origins
- [ ] Disable OpenAPI docs in production
- [ ] Add HSTS via reverse proxy (nginx/traefik)
- [ ] Configure monitoring and alerts
- [ ] Document rollback plan
- [ ] Run dependency audit (`pip-audit`)
- [ ] Verify that all environment variables are configured
