# Stock Historial

Sistema de gestión de inventario con **Source of Truth Inmutable** y consultas de stock histórico en `<100ms`.

Cada movimiento es atómico e inalterable. Las consultas de stock se resuelven mediante vistas materializadas en PostgreSQL.

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Runtime | Python 3.12+ |
| Framework | FastAPI |
| Validación | Pydantic 2 |
| Base de datos | PostgreSQL 16+ |
| Driver DB | asyncpg |
| Scheduler | APScheduler |
| Linter | Ruff |
| Formatter | Black |
| Testing | pytest + pytest-asyncio |
| Integración | testcontainers |
| Containerización | Docker + Docker Compose |

## Comandos Principales

```bash
make install       # Instalar dependencias
make dev           # Iniciar servidor FastAPI (uvicorn --reload)
make lint          # Ejecutar ruff linter
make format        # Ejecutar black formatter
make test          # Ejecutar pytest
make test-cov      # Ejecutar pytest con reporte de cobertura
make build         # lint + format + test
make typecheck     # Ejecutar mypy --strict
make docker-up     # Iniciar PostgreSQL + app con Docker Compose
make docker-down   # Detener servicios Docker
make clean         # Eliminar caché y artefactos
```

## Estructura del Proyecto

```
src/
├── domain/              # Entidades, value objects, excepciones, reglas de negocio
│   ├── entities/        # Product, Movement, Category
│   ├── value_objects/   # MovementType, SKU, Quantity
│   ├── exceptions/      # InsufficientStockError, ImmutabilityViolationError
│   ├── rules/           # Validación de stock, inmutabilidad
│   └── ports/           # Protocolos: IMovementRepository, IStockQueryRepository
├── application/         # Casos de uso, DTOs
│   ├── use_cases/       # CreateMovementUseCase, QueryStockAtDateUseCase, etc.
│   └── dtos/            # Modelos Pydantic input/output
├── infrastructure/      # DB, scheduler, logging
│   ├── db/              # Pool asyncpg, migraciones, Unit of Work
│   ├── repositories/    # Implementaciones PostgresRepository
│   ├── scheduler/       # APScheduler, política de refresh
│   └── logging/         # Logging estructurado
├── adapters/            # Capa HTTP: routers FastAPI, middleware
│   └── api/
│       ├── routers/     # /v1/movements, /v1/stock, /v1/products, /v1/categories
│       └── middleware/  # Mapeo de errores, rate limiting
└── main.py              # App factory, entrypoint
```

## Arquitectura

Clean Architecture + Ports & Adapters. El dominio no importa de infraestructura ni adaptadores. Las dependencias apuntan siempre hacia el centro.

Ver [docs/agents/architecture-design.md](docs/agents/architecture-design.md) para detalles.

## Documentación

| Archivo | Descripción |
|---|---|
| [AGENTS.md](AGENTS.md) | Guía para agentes de desarrollo |
| [WORKFLOW.md](WORKFLOW.md) | Estado del proyecto y fases |
| [SPEC.md](SPEC.md) | Especificación F0 |
| [CHANGELOG.md](CHANGELOG.md) | Registro de cambios |
| [docs/agents/](docs/agents/) | Guías de arquitectura, desarrollo, testing, seguridad |
| [docs/workflow/](docs/workflow/) | Roadmap, spec-tracking, dependencias |

## Estado Actual

**Fase:** F6 ✅ Completada | F7 🚧 Aprobada — lista para iniciar

- F0: Preparación ✅ | F1: Infraestructura DB ✅ | F2: Núcleo de Dominio ✅ | F3: Adaptadores de Datos ✅ | F4: Capa API ✅ | F5: Scheduler & Concurrencia ✅ | F6: Testing Integral ✅
- **F6 completada:** 205 tests unitarios pasando (99.34% cobertura). Hypothesis PBT con max_examples=100, seed=0. mypy --strict limpio (74 archivos). Edge cases de integración, E2E con SLA p95<100ms, pruebas de seguridad OWASP (SQL injection + input validation). Version 0.6.0.
- **F7 aprobada:** Despliegue & Documentación — Docker multi-stage, CI/CD pipeline, README técnico y demo script.

Fases completadas: 81 de 88 specs implementados. F7 en cola para iniciar.
