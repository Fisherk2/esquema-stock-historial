# Guías de Desarrollo

## Principios SOLID Aplicados

1. **SRP:** Cada archivo cumple una única responsabilidad. `repositories.py` solo maneja I/O de datos. `use_cases.py` solo orquesta lógica. `base_repository.py` centraliza gestión de conexión.
2. **OCP:** Nuevos tipos de movimientos se añaden extendiendo clases o enums, no modificando condicionales existentes.
3. **LSP:** Las implementaciones de repositorio deben ser sustituibles por mocks sin alterar contratos Pydantic.
4. **DIP:** Los casos de uso dependen de protocolos (`abc.ABC` o `typing.Protocol`), no de `asyncpg` directamente.
5. **ISP:** Interfaces granulares (`IMovementRepository`, `IStockQueryRepository`). No se exponen métodos `delete` si el dominio requiere inmutabilidad.

## Patrones de Diseño

- **Repository Pattern:** Abstrae acceso a PostgreSQL. `create_movement()`, `get_stock_at_date()`. Todos los repos heredan de `BasePostgresRepository`.
- **Unit of Work:** Transacciones explícitas vía `asyncpg.transaction()`. Commit/Rollback determinístico. Si rollback falla con excepción activa, se preserva la excepción original.
- **Humble Object:** Lógica compleja en SQL puro. Python solo valida, mapea y coordina.
- **Strategy (Refresh):** Scheduler inyecta política de refresco. Permite swapping futuro sin tocar dominio.

## Convenciones y Estructura

```
src/
├── domain/          # Entidades, excepciones, reglas de negocio puras, ports (protocols)
├── application/     # UseCases, DTOs, Interfaces (Protocols)
├── infrastructure/ # DB (connection, uow, migrations, seed), repositories (asyncpg wrappers), scheduler, logging
│ ├── db/ # connection.py, uow.py, migrate.py (non-transactional support), seed.py
│ ├── repositories/ # base_repository.py, movement_repository.py, product_repository.py, category_repository.py, stock_query_repository.py, mappers.py
│   ├── scheduler/   # APScheduler config
│   └── logging/     # Logging estructurado
├── adapters/        # FastAPI routers, controllers, dependency injection
└── main.py          # DI Container, setup, entrypoint
tests/
├── unit/            # Mocked protocols, pure business logic
├── integration/     # Testcontainers, SQL real, endpoints
└── e2e/             # Flujos completos, load testing básico
```

## Checklist Pre-Commit

- [ ] Linter (`ruff`) sin warnings críticos.
- [ ] Formato (`black`/`isort`) aplicado.
- [ ] Tests unitarios passing (`>80%` cobertura dominio).
- [ ] Migraciones/queries validadas con `EXPLAIN` en staging local.
- [ ] No hardcode, no `print()` en producción, loggers configurados.

## Manejo de Errores y Fallbacks

- **Errores de dominio:** Excepciones específicas (`ProductNotFoundError`, `CategoryNotFoundError`, `InsufficientStockError`) se mapean a HTTP status codes en middleware. Los use cases lanzan excepciones de dominio (no `ValueError` genérico).
- **Errores DB:** `asyncpg.PostgresError` y `asyncpg.DataError` se capturan en middleware → HTTP 500. Los repositorios NO envuelven errores de asyncpg en `ValueError`; dejan que bubblen up al handler existente.
- **Timeouts:** `statement_timeout=5s` en queries analíticas (SQL parametrizado: `SET statement_timeout = $1`). Fallback a respuesta cached o `503 Service Unavailable`.
- **Reintentos:** Decorador `@retry` con backoff exponencial para conflictos de concurrencia.
- **Mappers:** `JSONDecodeError` en metadata JSONB se maneja con fallback a `{}` y warning log (no crash).
