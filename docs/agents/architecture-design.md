# Arquitectura y Diseño

## Patrón Arquitectónico: Clean Architecture + Ports & Adapters

El sistema sigue estrictamente el **Dependency Inversion Principle (DIP)**. Las dependencias de código fuente apuntan siempre hacia el centro (Dominio/Aplicación). PostgreSQL, FastAPI y APScheduler son detalles externos intercambiables.

```mermaid
graph TD
    subgraph "Capa Externa (Infraestructura)"
        API[FastAPI Router / Controllers]
        SCHED[APScheduler Background Tasks]
        DB[(PostgreSQL 16+)]
    end

subgraph "Capa de Adaptadores (infrastructure/repositories/)"
IMovRepo[IMovementRepository Protocol]
IProdRepo[IProductRepository Protocol]
ICatRepo[ICategoryRepository Protocol]
IStockRepo[IStockQueryRepository Protocol]
BaseRepo[BasePostgresRepository — abstract]
MovRepoImpl[PostgresMovementRepository]
ProdRepoImpl[PostgresProductRepository]
CatRepoImpl[PostgresCategoryRepository]
StockRepoImpl[PostgresStockQueryRepository]
Mappers[mappers.py — asyncpg.Record → Entity]
end

    subgraph "Capa de Aplicación"
        UseCase[RecordMovementUseCase]
        UseCase2[QueryStockAtDateUseCase]
        DTOs[Pydantic Input/Output DTOs]
        UoW[PostgresUnitOfWork]
    end

subgraph "Capa de Dominio"
Ent[Entity: Product, Movement, Category — frozen=True]
Rules[Business Rules: StockValidation, Immutability]
Errs[Domain Exceptions: DomainError, ProductNotFoundError, CategoryNotFoundError, InsufficientStockError, ...]
VOs[Value Objects: SKU, Quantity, MovementType (StrEnum)]
end

    API --> IMovRepo
    API --> IProdRepo
    API --> UseCase
    SCHED --> IStockRepo
    UseCase --> IMovRepo
    UseCase --> IStockRepo
    UseCase --> Rules
    UseCase --> DTOs
MovRepoImpl -.-> IMovRepo
ProdRepoImpl -.-> IProdRepo
CatRepoImpl -.-> ICatRepo
StockRepoImpl -.-> IStockRepo
MovRepoImpl --> BaseRepo
ProdRepoImpl --> BaseRepo
CatRepoImpl --> BaseRepo
StockRepoImpl --> BaseRepo
MovRepoImpl --> Mappers
    ProdRepoImpl --> Mappers
    CatRepoImpl --> Mappers
    StockRepoImpl --> Mappers
    DB -.-> MovRepoImpl
    DB -.-> ProdRepoImpl
    DB -.-> StockRepoImpl
    UoW --> MovRepoImpl
    UoW --> ProdRepoImpl
    UseCase --> UoW
    Rules --> Errs
    Rules --> VOs
    Ent --> VOs
    Ent --> Errs
```

## Estrategia de Comunicación y Estado

- **Comandos (Write):** Se envían a `RecordMovementUseCase`. Validan reglas de negocio (stock no negativo, tipo de movimiento válido) y delegan al repositorio.
- **Consultas (Read):** `QueryStockAtDateUseCase` lee de la vista materializada `mv_stock_historical`. Si la vista no está lista, fallback a cálculo directo con límite de paginación.
- **Manejo de Concurrencia:** Optimistic Concurrency con reintentos exponenciales. Versión transaccional o `READ COMMITTED` + retry en `asyncpg`.

## Justificación Técnica

- **SQL Explícito:** Control total sobre `EXPLAIN ANALYZE`, índices compuestos y CTEs. Sin ORM que oculte planes de ejecución.
- **FastAPI + Pydantic:** OpenAPI 3.0 nativo. Validación estricta sin boilerplate.
- **APScheduler Interno:** Refresh como tarea asíncrona aislada del ciclo request/response. Swappable a Celery/RQ sin tocar dominio.

## Reglas de Importación (Clean Architecture Enforcement)

Las siguientes reglas de importación son obligatorias y se verifican en CI:

| Capa | Puede importar de | No puede importar de |
|------|-------------------|---------------------|
| `domain/` | Solo módulos internos de `domain/` | `application/`, `infrastructure/`, `adapters/` |
| `application/` | `domain/`, módulos internos de `application/` | `infrastructure/`, `adapters/` |
| `infrastructure/` | `domain/`, `application/`, libs externas | `adapters/` |
| `adapters/` | `domain/`, `application/`, `infrastructure/`, libs externas | — |

**Verificación automatizada:**
- `ruff` con `ban-relative-imports = "all"` previene imports relativos entre paquetes
- CI ejecuta `make lint` en cada push/PR
- Para enforcement estricto por directorio, considerar `import-linter` en fases futuras

**Convención:** Si un módulo de `domain/` necesita acceso a infraestructura, definir un `Protocol` en `domain/ports/` y dejar la implementación concreta en `infrastructure/repositories/`.

### Mappers (asyncpg.Record → Entity)

Los mappers son **funciones puras** ubicadas en `src/infrastructure/repositories/mappers.py`. Transforman `asyncpg.Record` (tipado explícito) en entidades de dominio (`@dataclass(frozen=True)`). No tienen estado, no acceden a DB, y son determinísticas:

- `map_category_row(record: asyncpg.Record) -> Category`
- `map_product_row(record: asyncpg.Record) -> Product` — construye `SKU` VO desde string
- `map_movement_row(record: asyncpg.Record) -> Movement` — parsea `movement_type` string → `StrEnum`, `quantity` int → `Quantity` VO, `metadata` JSONB → `dict[str, Any]` con manejo de `JSONDecodeError` (fallback a `{}`)

Esta separación mantiene los repositorios enfocados en I/O y delega la transformación a funciones testeables de forma aislada.

### BasePostgresRepository (DRY)

Clase abstracta en `src/infrastructure/repositories/base_repository.py` que centraliza la gestión de conexión compartida:

- `__init__(pool, connection=None)` — acepta pool y conexión opcional (para UoW)
- `_get_conn()` — retorna la conexión activa si existe (transacción), sino el pool

Los 4 repositorios concretos heredan de esta clase, eliminando duplicación de `__init__` y `_get_conn()`.
