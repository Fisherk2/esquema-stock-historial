# Contributing — Stock Historial

Gracias por tu interés en contribuir a Stock Historial. Esta guía cubre desde tu primer cambio hasta el proceso de PR, pasando por convenciones, calidad y arquitectura.

---

## TL;DR — Referencia Rápida

Si ya conoces el proyecto, esto es todo lo que necesitas recordar:

```bash
# 1. Entorno
python3 -m venv .venv && source .venv/bin/activate && make install

# 2. Calidad antes de commitear
make build       # ruff + black + pytest (todo debe pasar)
make typecheck   # mypy --strict (cero errores)
make test-cov    # cobertura: domain ≥90%, app ≥85%, infra ≥70%

# 3. Commits convencionales
# feat(scope): description  |  fix(scope): description  |  docs: description

# 4. PR
# Título claro + descripción: qué cambió, por qué, cómo probarlo
```

---

## Tu Primera Contribución

Este tutorial te guía paso a paso para hacer tu primer cambio en el proyecto. Está diseñado para que tengas éxito incluso si es tu primera vez contribuyendo a un repositorio Python.

### 1. Encuentra algo que hacer

Busca issues etiquetados con `good-first-issue` o `help-wanted`. Si no encuentras, cualquier mejora pequeña sirve: un test faltante, una docstring, un edge case.

### 2. Configura tu entorno

Sigue los pasos de [Setup](#setup) más abajo. Al finalizar, ejecuta `make build` para verificar que todo funciona.

### 3. Crea una rama

```bash
git checkout -b feat/add-validation-for-negative-quantity
```

El nombre debe reflejar el cambio: `feat/`, `fix/`, `refactor/`, `docs/` seguido de una descripción breve.

### 4. Haz un cambio pequeño

Ejemplo: agregar un test para un caso borde no cubierto. Ubica el archivo de tests correspondiente, por ejemplo `tests/unit/domain/test_stock_validation.py`, y añade:

```python
def test_validate_stock_not_negative_with_zero_stock():
    """OUT con stock actual en cero debe lanzar error."""
    from src.domain.rules.stock_validation import validate_stock_not_negative
    from src.domain.value_objects.movement_type import MovementType
    from src.domain.exceptions.insufficient_stock import InsufficientStockError

    with pytest.raises(InsufficientStockError):
        validate_stock_not_negative(MovementType.OUT, quantity=5, current_stock=0)
```

### 5. Verifica calidad

```bash
make build       # lint + format + test
make typecheck   # mypy --strict
```

### 6. Commitea

```bash
git add tests/unit/domain/test_stock_validation.py
git commit -m "test: add edge case for OUT movement with zero stock"
```

### 7. Abre un Pull Request

Empuja tu rama y crea un PR en GitHub. Sigue las pautas de [Proceso de PR](#proceso-de-pr).

---

## Setup

### Requisitos

| Software | Versión |
|---|---|
| Python | 3.12+ |
| Docker | 24+ (recomendado) |
| Docker Compose | 2.20+ |
| GNU Make | 3.82+ |

### Instalación

```bash
git clone https://github.com/Fisherk2/esquema-stock-historial.git
cd esquema-stock-historial
python3 -m venv .venv && source .venv/bin/activate
make install
```

Para una guía más detallada (Docker, migraciones, seed data), consulta [docs/SETUP.md](docs/SETUP.md).

---

## Flujo de Trabajo

1. **Fork** el repositorio
2. **Crea una rama** descriptiva, ej: `feat/add-transfer-movements`
3. **Revisa las guías de desarrollo** en `docs/agents/` — contienen las convenciones arquitectónicas, restricciones y patrones del proyecto
4. **Implementa** los cambios siguiendo la arquitectura y las reglas de calidad
5. **Escribe tests** para todo el código nuevo. La cobertura no debe disminuir
6. **Verifica** calidad: `make build` + `make typecheck`
7. **Commitea** con mensajes convencionales
8. **Abre un PR** siguiendo el proceso descrito abajo

---

## Tareas Comunes

### Cómo añadir una dependencia

1. Agrega el paquete a `requirements.txt` con la versión exacta (`paquete==X.Y.Z`)
2. Ejecuta `make install` para verificar que se instala correctamente
3. Si es una dependencia de desarrollo, documéntalo como comentario en el `requirements.txt`
4. Si añade un nuevo tool (linter, formateador), actualiza también la configuración en `pyproject.toml` y el CI

### Cómo ejecutar un subconjunto de tests

```bash
# Solo tests unitarios del dominio
python -m pytest tests/unit/domain/

# Solo un archivo específico
python -m pytest tests/unit/domain/test_stock_validation.py

# Solo un test específico
python -m pytest tests/unit/domain/test_stock_validation.py::test_validate_stock_not_negative

# Tests de integración (requiere Docker)
python -m pytest tests/integration/

# Tests E2E con benchmark
python -m pytest tests/e2e/ --benchmark-only
```

### Cómo crear una migración

1. Crea un archivo SQL numerado en `migrations/`, ej: `migrations/008_add_location_field.sql`
2. Si la migración no puede ejecutarse dentro de una transacción (ej: `CREATE INDEX CONCURRENTLY`), agrega `-- non-transactional` como primera línea del archivo
3. Agrega tests de integración en `tests/integration/` que validen el nuevo schema
4. Ejecuta `make migrate` para probar localmente

### Cómo depurar un test fallido

```bash
# Ejecutar con salida detallada
python -m pytest tests/unit/domain/test_stock_validation.py -vvs

# Ejecutar con traceback completo
python -m pytest tests/unit/domain/ --tb=long

# Ver cobertura del archivo específico
python -m pytest tests/unit/domain/ --cov=src/domain --cov-report=term-missing
```

### Cómo regenerar documentación

La documentación API se genera desde el código. Si agregas o modificas endpoints:

1. Actualiza los modelos Pydantic en `src/application/dtos/`
2. Verifica que la documentación OpenAPI se actualiza automáticamente
3. Actualiza manualmente `docs/API_REFERENCE.md` si los cambios son significativos
4. Si cambias la estructura del proyecto, actualiza el árbol en `README.md`

---

## Convención de Commits

Formato: `type(scope): descripción en imperativo`

### Tipos

| Tipo | Uso | Ejemplo |
|---|---|---|
| `feat` | Nueva funcionalidad | `feat(api): add transfer movement endpoint` |
| `fix` | Corrección de bug | `fix(repo): handle null metadata in movement` |
| `docs` | Cambios en documentación | `docs: update API reference with new endpoints` |
| `style` | Formateo de código | `style: run black formatter` |
| `refactor` | Refactorización sin cambio de comportamiento | `refactor(domain): extract stock validation rule` |
| `test` | Tests nuevos o corregidos | `test: add edge case for negative stock` |
| `chore` | Mantenimiento, dependencias | `chore: bump pytest-asyncio to 0.23` |
| `ci` | Cambios en CI/CD | `ci: add docker-build gate to pipeline` |

### Scopes

| Scope | Capa |
|---|---|
| `domain` | Entidades, value objects, reglas, ports |
| `application` | Use cases, DTOs |
| `infrastructure` | Repositorios, DB, scheduler, logging |
| `adapters` | Routers API, middleware |
| `db` | Migraciones, schema, seed |
| `scheduler` | APScheduler, política de refresh |
| `docs` | Documentación |
| `ci` | GitHub Actions, Makefile |

### Commits Atómicos

Cada commit debe hacer **una sola cosa**:

```
✅ feat(domain): add InsufficientStockError exception
✅ fix(repo): handle null metadata in movement query
✅ test: add edge case for stock at future date

❌ feat: add stock system + fix bug + update docs
```

---

## Calidad de Código

### Pre-commit

Ejecuta antes de cada commit:

```bash
make build      # ruff + black + pytest
make typecheck  # mypy --strict
```

### Type Checking

Todos los archivos en `src/` deben pasar `mypy --strict`. Si agregas código sin type hints, el CI fallará.

### Tests

Escribe tests para todo código nuevo. La cobertura no debe disminuir:

```bash
make test-cov
```

Métricas mínimas:

| Capa | Cobertura mínima |
|---|---|
| Global | ≥80% |
| Domain | ≥90% |
| Application | ≥85% |
| Infrastructure | ≥70% |

### Testing Strategy

| Tipo | Cuándo usar | Ejemplo |
|---|---|---|
| **Unit tests** | Lógica pura del dominio, reglas de negocio | Validación de stock, inmutabilidad |
| **Integration tests** | Repositorios, DB, API endpoints | CRUD con testcontainers |
| **E2E tests** | Flujos completos HTTP | Health → create → query → stock |
| **Security tests** | SQL injection, input validation | OWASP payloads |
| **Property-based tests** | Edge cases con Hypothesis | Generación de datos aleatorios |

---

## Arquitectura

### Reglas de Importación

```
Adapters (HTTP) → Application → Domain ← Infrastructure
```

Las dependencias apuntan siempre hacia el centro. Ninguna capa externa puede importar de una capa más externa que ella.

### Decisiones Clave y su Porqué

| Decisión | Por qué |
|---|---|
| **Clean Architecture** | Separa dominio, aplicación e infraestructura. El dominio es puro Python sin dependencias externas. Esto permite testear reglas de negocio sin base de datos, cambiar la DB sin tocar lógica, y mantener el núcleo portable. |
| **SQL explícito (sin ORM)** | Control total sobre `EXPLAIN ANALYZE`. Sin magia de SQLAlchemy que oculte queries N+1 o joins ineficientes. Las consultas de stock histórico tienen SLA de <100ms — cada milisegundo cuenta. |
| **Movimientos inmutables (append-only)** | La tabla `movements` es sagrada: solo `INSERT`. `UPDATE`/`DELETE` están prohibidos por trigger a nivel DB. Esto garantiza auditoría completa, reconciliación financiera y source of truth confiable. Las correcciones se hacen con movimientos compensatorios (`type: ADJUSTMENT`). |
| **Testcontainers (no mock DB)** | Los tests de integración levantan un PostgreSQL real en contenedor. Mockear PostgreSQL da falsa confianza — los tipos ENUM nativos, triggers, y constraints solo se comportan igual en una DB real. |
| **Vistas materializadas** | `mv_stock_historical` precalcula el stock por producto/fecha. `REFRESH CONCURRENTLY` permite actualizarla sin bloquear lecturas. Si la vista no está disponible, hay un fallback con cálculo directo. |
| **Unit of Work con transacciones explícitas** | Operaciones que cruzan múltiples repositorios (ej: verificar stock + crear movimiento) deben ser atómicas. El UoW maneja commit/rollback con `asyncpg.transaction()`. |

Para diagramas detallados, ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Guías de Desarrollo

Estas guías contienen las convenciones detalladas del proyecto. Tanto contribuyentes humanos como agentes IA deben consultarlas antes de modificar el código:

| Guía | Descripción |
|---|---|
| [Development Guidelines](docs/agents/development-guidelines.md) | Principios SOLID, patrones, estructura, convenciones de código |
| [Architecture & Design](docs/agents/architecture-design.md) | Clean Architecture, puertos y adaptadores, flujo de datos |
| [Testing Strategy](docs/agents/testing-strategy.md) | Fases de testing, frameworks, fixtures, métricas |
| [Security & Prohibitions](docs/agents/security-prohibitions.md) | Validación, SQL injection, prácticas prohibidas |
| [Performance Optimization](docs/agents/performance-optimisation.md) | SQL explícito, vistas materializadas, índices |
| [Tooling & CI/CD](docs/agents/tooling-ci-cd.md) | Linter, formateo, pre-commit hooks, CI/CD |

---

## Proceso de PR

1. **Título claro:** `feat(domain): add stock validation rule`
2. **Descripción:** Incluye qué cambió, por qué, y cómo probarlo
3. **Referencia specs:** Si aplica, menciona el spec relacionado (ej: `Relacionado: SPEC-40`)
4. **Tests:** Todo código nuevo debe incluir tests. Verifica cobertura
5. **Revisión:** Al menos un maintainer debe aprobar el PR
6. **Merge:** Squash and merge en `main`

### Checklist pre-PR

- [ ] `make build` pasa (lint + format + test)
- [ ] `make typecheck` pasa (mypy --strict)
- [ ] `make test-cov` muestra cobertura dentro de los umbrales
- [ ] Los tests nuevos cubren el cambio
- [ ] El commit sigue la convención

---

## Reportar Issues / Solicitar Features

### Reportar un Bug

Incluye la siguiente información:

1. **Descripción:** Qué esperabas que pasara vs qué pasó
2. **Reproducir:** Pasos concretos para reproducir el bug
3. **Entorno:** Versión de Python, Docker, OS
4. **Logs:** Salida relevante de la terminal o logs de la app

### Solicitar una Feature

1. **Problema:** ¿Qué necesidad o limitación motiva la feature?
2. **Solución propuesta:** Describe el comportamiento deseado
3. **Alternativas:** Si consideraste otras soluciones, menciónalas

Para cambios grandes, abre un issue primero para discutirlo antes de implementar.

---

## Links Útiles

- [Architecture](docs/ARCHITECTURE.md) — Diagramas y patrones
- [API Reference](docs/API_REFERENCE.md) — 11 endpoints documentados
- [Setup Guide](docs/SETUP.md) — Instalación detallada
- [README](../README.md) — Descripción general del proyecto
