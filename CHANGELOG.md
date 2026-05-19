# Registro de Cambios (Changelog)

Todos los cambios notables de este proyecto serán documentados en este archivo.

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Sin Lanzar]

### [0.4.0] — 2026-05-18 — F3: Adaptadores de Datos (Completado)

#### Agregado
- **4 Repositorios Postgres:** `PostgresMovementRepository`, `PostgresProductRepository`, `PostgresCategoryRepository`, `PostgresStockQueryRepository` — todos con `asyncpg` y SQL explícito
- **3 Mappers:** Funciones puras `row_to_product()`, `row_to_category()`, `row_to_movement()` con validación de tipos
- **Vista Materializada:** Migración 008 crea `mv_stock_historical` con índice único en `product_id` para `REFRESH CONCURRENTLY`
- **Refresh Function:** `refresh_stock_view()` con `REFRESH CONCURRENTLY`, manejo de errores y métricas de latencia
- **Unit of Work:** `IUnitOfWork` (Protocol) + `PostgresUnitOfWork` con context manager auto-commit/rollback
- **Módulo de re-exports:** `src/infrastructure/repositories/__init__.py` con imports centralizados

#### Validación
- 98 tests unitarios + 43 tests de integración (100% pass)
- Cobertura de repositorios: 96.30% (target >70%)
- `make lint` y `black --check` sin errores
- Documentación auditada: 10/10 (docstrings con Args/Returns/Raises/Examples)

#### Corregido
- `asyncpg` 0.31.0 con Python 3.14 requiere `json.dumps()` para parámetros JSONB
- Docstring de `refresh_stock_view()` corregido: capturaba `UndefinedTableError` pero decía que lo lanzaba
- Docstrings mejorados en 3 archivos: explicación de estrategia MV+fallback, razón de inmutabilidad de movimientos, comentario sobre JSONB quirk

### [0.1.0] — 2026-05-14 — F0: Preparación (Completado)

#### Agregado
- Estructura Clean Architecture: `src/{domain,application,infrastructure,adapters}` + `tests/{unit,integration,e2e}`
- `pyproject.toml` con configuración de ruff, black, pytest, mypy
- `requirements.txt` con dependencias pinned para F0-F7
- `Makefile` con comandos: `install`, `dev`, `lint`, `format`, `test`, `test-cov`, `build`, `docker-up`, `docker-down`
- `Dockerfile` multi-stage (builder + runtime)
- `docker-compose.yml` con PostgreSQL 16 + app, ambos con healthchecks
- `.env.example` con variables documentadas
- `.pre-commit-config.yaml` con hooks: ruff, black, trailing-whitespace, end-of-file-fixer, check-yaml
- `.github/workflows/ci.yml` con jobs de lint y test
- FastAPI app factory (`src/main.py`) con endpoint `GET /v1/health`
- Configuración pydantic-settings (`src/core/config.py`)
- Pool de conexión asyncpg placeholder (`src/infrastructure/db/connection.py`)
- Test smoke de health endpoint (`tests/unit/test_health.py`)
- Fixture de test con `TestClient` (`tests/conftest.py`)
- Reglas de importación Clean Architecture documentadas en `docs/agents/architecture-design.md`

#### Corregido
- Import `AsyncGenerator` migrado de `typing` a `collections.abc` (Python 3.12+)
- Import `TestClient` movido a bloque `TYPE_CHECKING` para cumplir regla TC002 de ruff
- `pythonpath` agregado a `pyproject.toml` para resolver imports en pytest

---

---

## Información del Proyecto

### Repositorio
- **Nombre**: Esquema stock con historial
- **Descripción**: Esquema relacional normalizado para productos, movimientos y consultas analíticas de stock histórico.
- **Repositorio**: https://github.com/Fisherk2/esquema-stock-historial
- **Licencia**: MIT License

### Stack Tecnológico
...

### Documentación Relacionada
...

### Instrucciones de Actualización

#### Desde Versiones Anteriores
...

#### Para Versiones Futuras
...

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

- **Rastrea la evolución** de la plantilla de desarrollo asistido por IA
- **Comunica cambios** a usuarios y contribuyentes
- **Proporciona guía de actualización** para lanzamientos futuros
- **Documenta decisiones arquitectónicas** y su racional
- **Habilita procesos de lanzamiento automatizados** con seguimiento estructurado de cambios