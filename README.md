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
make docker-up     # Iniciar PostgreSQL + app con Docker Compose
make docker-down   # Detener servicios Docker
make clean         # Eliminar caché y artefactos
```

## Estructura del Proyecto

```
src/
├── domain/              # Entidades, value objects, excepciones, reglas de negocio
│   ├── entities/        # Product, Movement
│   ├── value_objects/   # MovementType, SKU, etc.
│   ├── exceptions/      # InsufficientStockError, ImmutabilityViolationError
│   ├── rules/           # Validación de stock, inmutabilidad
│   └── ports/           # Protocolos: IMovementRepository, IStockQueryRepository
├── application/         # Casos de uso, DTOs, interfaces de aplicación
│   ├── use_cases/       # RecordMovementUseCase, QueryStockAtDateUseCase
│   ├── dtos/            # Modelos Pydantic input/output
│   └── interfaces/      # Protocolos de aplicación
├── infrastructure/      # DB, scheduler, logging
│   ├── db/              # Pool asyncpg, migraciones, Unit of Work
│   ├── repositories/    # Implementaciones PostgresRepository
│   ├── scheduler/       # APScheduler, política de refresh
│   └── logging/         # Logging estructurado
├── adapters/            # Capa HTTP: routers FastAPI, middleware
│   └── api/
│       ├── routers/     # /v1/movements, /v1/stock, /v1/products
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

**Fase:** F3 — Adaptadores de Datos 📋 Especificada

- F0: Preparación ✅ | F1: Infraestructura DB ✅ | F2: Núcleo de Dominio ✅
- **F3:** Especificada — lista para implementación (Spec-30/31/32)
- **F4:** Capa API (próxima)

Specs activos: Spec-30 (Repositorio), Spec-31 (Vistas Materializadas), Spec-32 (Unit of Work) — Open Questions resueltas.
