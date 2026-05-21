# Registro de Cambios (Changelog)

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Sin Lanzar]

---

## [1.0.0] - 2026-05-21

### Lanzamiento Inicial — Production Ready

Sistema de gestión de inventario con **Fuente Inmutable de Verdad** (Immutable Source of Truth),
API REST y consultas de stock histórico en **<100ms** mediante vistas materializadas.
88 especificaciones implementadas a través de 8 fases (F0–F7).

---

#### F0: Preparación (2026-05-14)

_Scaffolding del proyecto, tooling y configuración inicial._

##### Agregado

- **Estructura del proyecto**: scaffolding con FastAPI, health endpoint y configuración base
- **Tooling**: Ruff (linter), Black (formatter), pre-commit hooks, mypy (type checker)
- **Configuración**: `pyproject.toml` con ruff, black, pytest, mypy y coverage
- **Makefile**: 16 comandos para build, test, lint, format, docker, etc.
- **Dependencias**: `requirements.txt` con 7 runtime + 11 dev packages
- **Documentación de trabajo**: AGENTS.md, WORKFLOW.md, CHANGELOG.md inicial
- **Skills de agente**: Instalación de skills del stack tecnológico a nivel de proyecto
- **Gitignore**: Configuración general ignorando directorios de IA, entornos virtuales, etc.
- **Licencia**: MIT License

---

#### F1: Infraestructura DB (2026-05-15)

_Esquema de base de datos, migraciones, pool de conexiones y health check._

##### Agregado

- **SPEC-10, SPEC-11, SPEC-12**: Especificaciones formales de infraestructura DB
- **Esquema relacional**: Migraciones 001–007 para tablas `categories`, `products`, `movements`
- **Pool de conexiones**: asyncpg connection pool con lifespan management y `statement_timeout`
- **Health check DB**: Endpoint con `SELECT 1` para verificación de conectividad
- **Seed data**: Script de datos de inicialización (`seed.py`)
- **Migraciones transaccionales y no transaccionales**: Soporte para `CREATE INDEX CONCURRENTLY`

##### Corregido

- Bug en `seed.py`: corrección de `pool.transaction()` y adición de docstrings con ejemplos

---

#### F2: Núcleo de Dominio (2026-05-15)

_Entidades, Value Objects, reglas de negocio, puertos (protocolos) y excepciones._

##### Agregado

- **SPEC-20, SPEC-21, SPEC-22**: Especificaciones del núcleo de dominio
- **Entidades**: `Product`, `Movement`, `Category` como `@dataclass(frozen=True)`
- **Value Objects**: `SKU` (validación regex `^[A-Za-z0-9\-_]{1,50}$`), `Quantity` (no negativa), `MovementType` (IN, OUT, ADJUSTMENT, TRANSFER via StrEnum)
- **Reglas de negocio**: Stock no negativo, inmutabilidad de movimientos, validación condicional de metadatos (ADJUSTMENT requiere `reason`; TRANSFER requiere `origin` + `destination`)
- **Puertos (Ports)**: 4 protocolos via `typing.Protocol` — `ICategoryRepository`, `IProductRepository`, `IMovementRepository`, `IStockQueryRepository`
- **Excepciones de dominio**: 7 errores específicos (`ProductNotFoundError`, `InsufficientStockError`, `InvalidMovementError`, etc.)
- **Plan de ejecución**: Desglose detallado para implementación de la fase
- **Pruebas unitarias**: 89 tests, 99.56% de cobertura de dominio

---

#### F3: Adaptadores de Datos (2026-05-18)

_Implementación concreta de repositorios PostgreSQL, mappers, Unit of Work y vista materializada._

##### Agregado

- **SPEC-30, SPEC-31, SPEC-32**: Especificaciones de adaptadores de datos
- **17 tareas implementadas** en 4 sub-fases:
  - **Tarea 1**: Mappers puros con 8 tests unitarios (`asyncpg.Record` → Entity)
  - **Tareas 2–5**: 4 repositorios concretos — `PostgresCategoryRepository` (6 tests), `PostgresProductRepository` (8 tests), `PostgresMovementRepository` (7 tests), `PostgresStockQueryRepository` (4 tests)
  - **Tarea 6**: Re-exports limpios en `__init__.py` de repositorios
  - **Tarea 9**: Migración 008 — vista materializada `mv_stock_historical`
  - **Tarea 10**: `refresh_stock_view()` con manejo graceful de errores
  - **Tarea 11**: Optimización de `StockQueryRepo` con vista materializada
  - **Tarea 12**: 5 tests de integración para vista materializada
  - **Tarea 13**: Protocolo `IUnitOfWork` en `domain/ports`
  - **Tareas 14+15**: `PostgresUnitOfWork` con context manager y 5 tests de integración
  - **Tarea 17**: Documentación post-implementación en archivos de repositorios
- **BasePostgresRepository**: Clase abstracta con pool y conexión compartidos
- **Cobertura**: 98 unit + 43 integration tests, 96.30% global

##### Cambiado

- Formateo Black en 4 archivos de infraestructura

---

#### F4: Capa API (2026-05-18 — 2026-05-19)

_Use Cases, DTOs, Routers, Error Mapping y pruebas de integración._

##### Agregado

- **SPEC-40, SPEC-41, SPEC-42**: Especificaciones de la capa API
- **6 Use Cases**: `RecordMovement`, `QueryCurrentStock`, `QueryStockAtDate`, `CreateProduct`, `CreateCategory`, `ListProducts`
- **DTOs de entrada/salida**: Pydantic con `strict=True`, `extra="forbid"`
- **5 Routers FastAPI**: health, categories, products, movements, stock
- **Middleware**: Error mapping (excepciones de dominio → códigos HTTP), request logging
- **DI Container**: Inyección de dependencias en `dependencies.py`
- **11 endpoints REST**:
  - `GET /v1/health` — Health check con verificación DB
  - `POST /v1/categories` — Crear categoría
  - `GET /v1/categories` — Listar categorías
  - `POST /v1/products` — Crear producto (valida FK de categoría)
  - `GET /v1/products` — Listar productos (paginado: limit/offset)
  - `GET /v1/products/{id}` — Obtener producto por ID
  - `POST /v1/movements` — Registrar movimiento de stock
  - `GET /v1/movements/{id}` — Obtener movimiento por ID
  - `GET /v1/movements` — Listar movimientos por producto (paginado)
  - `GET /v1/stock/{id}/current` — Stock actual (vista materializada + fallback)
  - `GET /v1/stock/{id}/at-date` — Stock histórico en fecha ISO 8601
- **Pruebas de integración API**: Fixtures, categories, products, movements, stock, error mapping
- **Optimización de fixtures**: 1 contenedor PostgreSQL por sesión (de 88 contenedores → 1), reduciendo tiempo de pruebas de ~20 min a ~20 s

---

#### F5: Scheduler & Concurrencia (2026-05-19)

_APScheduler, reintentos con backoff, logging estructurado._

##### Agregado

- **SPEC-50, SPEC-51, SPEC-52**: Especificaciones de scheduler y concurrencia
- **APScheduler**: Cron para refresco concurrente de `mv_stock_historical`
- **Intervalo configurable**: Default 5 minutos, con `misfire_grace_time` y `statement_timeout`
- **Decorador `@retry`**: Reintentos con exponential backoff para operaciones transitorias
- **Logging estructurado**: JSON logging con contexto de solicitud
- **Fallback automático**: Cálculo directo de stock con paginación si la MV no está disponible
- **Control de concurrencia**: `READ COMMITTED` + retry para optimistic concurrency

---

#### F6: Testing Integral (2026-05-20)

_Hypothesis PBT, mypy strict, edge cases, E2E, seguridad._

##### Agregado

- **SPEC-60, SPEC-61, SPEC-62, SPEC-63**: Especificaciones de testing integral
- **Property-Based Testing (Hypothesis)**: Generación de datos de entrada para descubrimiento de edge cases
- **mypy strict**: Type checking estricto en todo el código `src/`
- **Pruebas E2E**: Flujos HTTP completos con verificación de latencia (**p95 < 100ms** para stock histórico)
- **Pruebas de seguridad**: SQL injection, fuga de información en errores, validación de entrada
- **Edge case tests**: Repositorios, MV, UoW, API en condiciones límite
- **205+ tests**: Suite completa con 99.34% de cobertura global
- **Lint fixes**: Correcciones para pasar ruff sin advertencias

##### Cambiado

- Versión actualizada a 1.0.0-alpha → 1.0.0-rc en el pipeline

---

#### F7: Despliegue & Documentación (2026-05-20 — 2026-05-21)

_Docker, CI/CD, documentación final, hardening pre-lanzamiento._

##### Agregado

- **SPEC-70, SPEC-71, SPEC-72**: Especificaciones de despliegue y documentación
- **Dockerfile**: Multi-stage build (builder + runtime) con usuario no-root y labels OCI
- **Docker Compose dev**: PostgreSQL efímera + aplicación con hot-reload
- **Docker Compose prod**: Políticas de restart, sin exposición de DB, healthchecks
- **CI/CD (GitHub Actions)**: Pipeline de 5 gates secuenciales:
  1. `lint` — ruff sin advertencias
  2. `typecheck` — mypy `--strict` en `src/`
  3. `test` — suite completa de pruebas
  4. `coverage` — global ≥80%, dominio ≥90%, aplicación ≥85%
  5. `docker-build` — validación de compilación multi-stage
- **Especificaciones**: 26 archivos de spec (SPEC-01 a SPEC-72)
- **Documentación del proyecto**:
  - `README.md` con badges, arquitectura y guía rápida
  - `ARCHITECTURE.md` con diagramas C4
  - `API_REFERENCE.md` con los 11 endpoints documentados
  - `SETUP.md` con guía de instalación y configuración
  - `USER_GUIDE.md` con ejemplos de uso
  - `CONTRIBUTING.md` reestructurado bajo marco Diátaxis
- **Documentación para agentes de IA**: Traducción al inglés de 44 archivos de documentación agéntica
- **Documentación de workflow**: Roadmap, spec-tracking, dependency graphs, process rules, stakeholder matrix

##### Cambiado

- **SPEC.md**: Refactorizado de monolito (1579→204 líneas) a orquestador que referencia specs individuales
- **Makefile**: Estandarización de comandos y consolidación de fixtures de prueba
- **CONTRIBUTING.md**: Reestructuración completa con marco Diátaxis

---

#### Hardening y Revisiones Post-Fase (2026-05-20 — 2026-05-21)

_Revisiones 5-axis, correcciones post-ship y preparación para primer push._

##### Seguridad

- **Security headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store`
- **Serialización JSONB**: Corrección en repositorio para serializar `metadata` como dict → JSON en columna JSONB de asyncpg
- **Validación estricta**: Pydantic `strict=True`, `extra="forbid"` en todos los DTOs de entrada

##### Corregido

- **Dead code removal**: Eliminación de código muerto identificado en revisión post-ship
- **Clean Architecture fixes**: Corrección de violaciones de dependencia inversa
- **Paginación DB**: Implementación correcta de limit/offset en consultas de base de datos
- **Scheduler fixes**: Correcciones en configuración de APScheduler y manejo de misfire
- **Bugs críticos pre-MVP**: Correcciones identificadas en revisión `/ship` — bug de concurrencia, validación de movimientos, edge cases en límites de stock

##### Cambiado

- **Refactor F0-F3**: Hardening tras revisión 5-axis del proyecto
- **Refactor F4-F5**: Hardening tras revisión 5-axis del proyecto
- **Refactor F6-F7**: Hardening tras revisión 5-axis post-release
- **Documentación**: Actualización tras hardening — specs, agent docs, workflow

##### Removido

- Scripts y stubs vacíos de diseño (`chore: remove empty scripts and stub design docs`)

---

### Stack Tecnológico

| Componente | Tecnología | Versión |
|---|---|---|
| **Runtime** | Python | 3.12+ |
| **Web Framework** | FastAPI | 0.136.1 |
| **Validación** | Pydantic | 2.13.4 |
| **DB Driver** | asyncpg | 0.31.0 |
| **Scheduler** | APScheduler | 3.11.2 |
| **Base de Datos** | PostgreSQL | 16+ |
| **Servidor ASGI** | uvicorn | 0.47.0 |
| **Linter** | Ruff | 0.15.13 |
| **Formatter** | Black | 26.3.1 |
| **Type Checker** | mypy | 2.1.0 (strict) |
| **Testing** | pytest + pytest-asyncio | 9.0.3 / 1.3.0 |
| **Property-Based Testing** | Hypothesis | 6.141.1 |
| **Container Testing** | testcontainers | 4.14.2 |
| **Time Mocking** | freezegun | 1.5.5 |
| **Benchmarks** | pytest-benchmark | 5.2.3 |
| **Cobertura** | pytest-cov | 7.1.0 |
| **CI/CD** | GitHub Actions | 5 gates secuenciales |
| **Containerización** | Docker + Docker Compose | Multi-stage build |

### Documentación Relacionada

- [WORKFLOW.md](WORKFLOW.md) — Orquestación de fases, estado actual y enlaces a docs detallados
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Arquitectura Clean Architecture + DDD + Hexagonal
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md) — Referencia completa de los 11 endpoints REST
- [docs/SETUP.md](docs/SETUP.md) — Guía de instalación, configuración y Docker
- [docs/USER_GUIDE.md](docs/USER_GUIDE.md) — Ejemplos de uso y casos de consumo
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) — Guía de contribución (marco Diátaxis)
- [docs/agents/](docs/agents/) — Guías detalladas para agentes de IA (arquitectura, desarrollo, testing, seguridad, performance, tooling)
- [docs/workflow/](docs/workflow/) — Roadmap, spec-tracking, graphs de dependencias, reglas de proceso, matriz de stakeholders
- [specs/](specs/) — 26 especificaciones formales (SPEC-01 a SPEC-72)

### Instrucciones de Actualización

#### Desde Versiones Anteriores

No aplica — este es el lanzamiento inicial v1.0.0.

#### Para Versiones Futuras

1. **Agregar cambios** en la sección `[Sin Lanzar]` a medida que se desarrollan
2. **Antes de un lanzamiento**, mover los cambios de `[Sin Lanzar]` a una nueva sección con versión y fecha
3. **Seguir versionado semántico** (v1.x.x para cambios rupturantes, v1.x.x para features, v1.x.x para parches)
4. **Actualizar referencias de versión** en WORKFLOW.md, README.md y archivos de configuración
5. **Ejecutar suite completa** de pruebas antes de etiquetar un release

### Contribuyendo al CHANGELOG

Al contribuir a este proyecto:

1. **Agrega entradas** a la sección `[Sin Lanzar]`
2. **Sigue versionado semántico** para cambios rupturantes
3. **Usa categorías apropiadas** (Agregado, Cambiado, Deprecado, Removido, Corregido, Seguridad)
4. **Incluye fechas** en formato `YYYY-MM-DD`
5. **Proporciona descripciones claras** explicando el impacto de los cambios
6. **Agrupa por fase** (Definir, Planear, Construir, Verificar, Revisar, Lanzar)
7. **Referencia issues relacionados** o pull requests cuando aplique

### Por Qué Este CHANGELOG Importa

Este CHANGELOG sirve como documentación viva que:

- **Rastrea la evolución** del sistema de gestión de inventario
- **Comunica cambios** a usuarios y contribuyentes
- **Proporciona guía de actualización** para lanzamientos futuros
- **Documenta decisiones arquitectónicas** y su racional
- **Habilita procesos de lanzamiento automatizados** con seguimiento estructurado de cambios
