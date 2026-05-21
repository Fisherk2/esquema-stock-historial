# Estrategia de Testing

## Fases de Testing

1. **Unitarias:** Validan lógica de negocio pura y mapeo DTOs. Sin DB real. Usan `unittest.mock` o `pytest-mock` contra protocolos.
2. **Integración:** Levantan PostgreSQL efímero con `testcontainers.postgres`. Ejecutan scripts SQL de migración, insertan fixtures, validan resultados de vistas y queries.
3. **E2E / Contract:** Lanzan servidor FastAPI en modo test. Simulan requests HTTP, validan respuestas JSON contra esquemas Pydantic y miden latencia `<100ms`.

## Frameworks y Patrones

- **Pytest + pytest-asyncio:** Estándar para código asíncrono.
- **Factory Boy:** Generación determinista de fixtures de prueba.
- **SQLAlchemy Core (solo para tests):** Uso opcional para seed data rápido sin comprometer la capa de prod.
- **Aislamiento:** Cada test suite transaccional. Rollback automático post-test. Contenedores destruidos al finalizar CI.

## Fixtures de Integración

### Arquitectura de Fixtures

Los tests de integración usan **un solo contenedor PostgreSQL por sesión**, con limpieza entre tests mediante TRUNCATE + re-seed:

| Fixture | Scope | Propósito | Cuando usar |
|---------|-------|-----------|-------------|
| `db_pool` | `session` | 1 contenedor, migraciones + seed al inicio | Tests de estructura (tablas, índices, triggers) |
| `db_clean` | `function` | TRUNCATE + re-seed + refresh MV antes de cada test | Tests que insertan/consultan datos (repos, API) |
| `api_client` | `function` | FastAPI app + `db_clean` + HTTP client | Tests HTTP de endpoints |

### Beneficios

- **Antes:** ~88 contenedores por sesión → ~20 minutos
- **Después:** 1 contenedor por sesión → ~20 segundos
- **Reducción:** ~99% menos overhead de contenedores

### Implementación

```python
# tests/conftest.py (raíz del proyecto)
@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """1 contenedor session-scoped: migraciones + seed + MV."""

@pytest_asyncio.fixture(scope="function")
async def db_clean(db_pool: asyncpg.Pool) -> AsyncGenerator[asyncpg.Pool, None]:
    """Datos limpios por test: TRUNCATE + re-seed + refresh MV."""
```

Los fixtures `db_pool` y `db_clean` están definidos en `tests/conftest.py`
(raíz) y están disponibles automáticamente en `tests/integration/`,
`tests/e2e/` y `tests/security/` gracias al mecanismo de conftest de pytest.
El fixture `db_pool` usa `Settings.db_pool_min_size` y `db_pool_max_size`
para consistencia con la configuración de producción.

### Reglas

1. **Nunca definir `db_pool` localmente** en archivos de test (evita duplicados que ocultan el fixture compartido).
2. **Usar `db_clean`** para tests que insertan/leen datos (repos, API, schema con inserts).
3. **Usar `db_pool`** para tests que solo verifican estructura (tablas, columnas, índices, ENUMs).
4. **`api_client`** depende de ambos: `db_clean` para datos limpios, `db_pool` para DI override.

## Métricas de Calidad

- **Cobertura:** `>85%` en `domain/` y `application/`. `>70%` en `infrastructure/`. Global `>80%`.
- **Tests totales:** 477 — unitarios + integracion + e2e + seguridad.
- **Complejidad Ciclomática:** `<10` por función. Si supera, refactorizar con SRP.
- **Deuda Técnica:** Cero `FIXME` o `TODO` críticos en rama `main`.

### Nuevos tipos de tests de integracion

| Tipo | Cubre | Ejemplo |
|------|-------|---------|
| Security headers | Verifica cabeceras en respuestas | `X-Content-Type-Options: nosniff` presente |
| Pagination bounds | Validacion de limit/offset | `limit=0` → 422, `limit=1001` → 422 |
| Timezone handling | Datetime naive → UTC | `_ensure_timezone_aware` unit + integration |
| Error handler origin | Traceback verification | ValueError desde DTO → 400, desde infra → 500 |

## Mockeo y Aislamiento

- **DB Mocking:** En unit tests, inyectar `MockRepository` que retorna `AsyncMock`.
- **Scheduler Mocking:** `APScheduler` se desactiva en modo `TESTING`. Se verifica registro de jobs, no ejecución real.
- **Time Mocking:** `freezegun` para validar consultas históricas deterministas.
