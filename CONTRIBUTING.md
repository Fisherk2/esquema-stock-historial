# Contributing — Stock Historial

Gracias por tu interés en contribuir a Stock Historial. Esta guía te ayudará a configurar tu entorno de desarrollo y comprender las convenciones del proyecto.

## Setup

1. Sigue la guía de instalación en [docs/SETUP.md](docs/SETUP.md)
2. Asegúrate de que `make build` pasa antes de crear un PR:

```bash
make build  # lint + format + test
make typecheck  # mypy --strict
```

## Flujo de Trabajo

1. **Fork** el repositorio
2. **Crea una rama** descriptiva: `feat/add-transfer-movements`
3. **Implementa** los cambios siguiendo la arquitectura del proyecto
4. **Escribe tests** para todo el código nuevo
5. **Verifica** calidad: `make build` + `make typecheck`
6. **Commitea** siguiendo la convención de commits
7. **Abre un PR** con descripción clara

## Convención de Commits

Formato: `type(scope): description`

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

## Calidad de Código

### Pre-commit

Ejecuta `make build` antes de cada commit:

```bash
make build    # ruff + black + pytest
make typecheck  # mypy --strict
```

### Type Checking

Todos los archivos en `src/` deben pasar `mypy --strict`:

```bash
make typecheck
```

Si agregas nuevo código sin type hints, el CI fallará.

### Tests

**Escribe tests para todo código nuevo.** La cobertura no debe disminuir:

```bash
make test-cov
```

Métricas mínimas:
- Global: ≥80%
- Domain: ≥90%
- Application: ≥85%
- Infrastructure: ≥70%

### Testing Strategy

| Tipo | Cuándo usar | Ejemplo |
|---|---|---|
| **Unit tests** | Lógica pura del dominio, reglas de negocio | Validación de stock, inmutabilidad |
| **Integration tests** | Repositorios, DB, API endpoints | CRUD con testcontainers |
| **E2E tests** | Flujos completos HTTP | Health → create → query |
| **Security tests** | SQL injection, input validation | OWASP payloads |
| **Property-based tests** | Edge cases con Hypothesis | Generación de datos aleatorios |

## Arquitectura

Respeta las reglas de importación entre capas. Ver [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) para detalles.

**Reglas clave:**
- El dominio **nunca** importa de infraestructura ni adaptadores
- Los use cases importan solo del dominio (via protocolos)
- Los adaptadores no importan directamente del dominio
- SQL explícito, sin ORM

## Proceso de PR

1. **Título claro:** `feat(domain): add stock validation rule`
2. **Descripción:** Qué cambió, por qué, cómo probarlo
3. **Referencia specs:** Si aplica, referencia el spec (e.g., `SPEC-40`)
4. **Tests:** Incluir tests que cubran el nuevo código
5. **Revisión:** Al menos un maintainer aprueba el PR
6. **Merge:** Squash and merge en `main`

## Commits Atómicos

Cada commit debe hacer **una sola cosa**:

```
✅ feat(domain): add InsufficientStockError exception
✅ fix(repo): handle null metadata in movement query
✅ test: add edge case for stock at future date

❌ feat: add stock system + fix bug + update docs
```

## Questions?

- Consulta [AGENTS.md](AGENTS.md) para guías de desarrollo
- Consulta [docs/SETUP.md](docs/SETUP.md) para configuración
- Abre un issue para discutir cambios grandes antes de implementarlos
