# Guías de Desarrollo

## Principios SOLID Aplicados

1. **SRP:** Cada archivo cumple una única responsabilidad. `repositories.py` solo maneja I/O de datos. `use_cases.py` solo orquesta lógica.
2. **OCP:** Nuevos tipos de movimientos se añaden extendiendo clases o enums, no modificando condicionales existentes.
3. **LSP:** Las implementaciones de repositorio deben ser sustituibles por mocks sin alterar contratos Pydantic.
4. **DIP:** Los casos de uso dependen de protocolos (`abc.ABC` o `typing.Protocol`), no de `asyncpg` directamente.
5. **ISP:** Interfaces granulares (`IMovementRepository`, `IStockQueryRepository`). No se exponen métodos `delete` si el dominio requiere inmutabilidad.

## Patrones de Diseño

- **Repository Pattern:** Abstrae acceso a PostgreSQL. `create_movement()`, `get_stock_at_date()`.
- **Unit of Work:** Transacciones explícitas vía `asyncpg.transaction()`. Commit/Rollback determinístico.
- **Humble Object:** Lógica compleja en SQL puro. Python solo valida, mapea y coordina.
- **Strategy (Refresh):** Scheduler inyecta política de refresco. Permite swapping futuro sin tocar dominio.

## Convenciones y Estructura

```
src/
├── domain/          # Entidades, excepciones, reglas de negocio puras, ports (protocols)
├── application/     # UseCases, DTOs, Interfaces (Protocols)
├── infrastructure/  # DB (connection, uow, migrations, seed), repositories (asyncpg wrappers), scheduler, logging
│   ├── db/          # connection.py, uow.py, migrate.py, seed.py
│   ├── repositories/  # movement_repository.py, product_repository.py, category_repository.py, stock_query_repository.py, mappers.py
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

- **Errores DB:** Captura explícita de `asyncpg.PostgresError`. Mapeo a `HTTP 4xx/5xx` o excepciones de dominio (`InsufficientStockError`).
- **Timeouts:** `statement_timeout=5s` en queries analíticas. Fallback a respuesta cached o `503 Service Unavailable`.
- **Reintentos:** Decorador `@retry` con backoff exponencial para conflictos de concurrencia.
