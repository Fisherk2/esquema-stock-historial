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

## Métricas de Calidad

- **Cobertura:** `>85%` en `domain/` y `application/`. `>70%` en `infrastructure/`.
- **Complejidad Ciclomática:** `<10` por función. Si supera, refactorizar con SRP.
- **Deuda Técnica:** Cero `FIXME` o `TODO` críticos en rama `main`.

## Mockeo y Aislamiento

- **DB Mocking:** En unit tests, inyectar `MockRepository` que retorna `AsyncMock`.
- **Scheduler Mocking:** `APScheduler` se desactiva en modo `TESTING`. Se verifica registro de jobs, no ejecución real.
- **Time Mocking:** `freezegun` para validar consultas históricas deterministas.
