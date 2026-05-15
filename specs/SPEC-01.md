# SPEC-01: Estructura y convenciones

## Descripción

Establecer la estructura base del proyecto siguiendo Clean Architecture, convenciones de naming y configuración de herramientas de calidad.

## Fase

F0 — Preparación

## Archivos Involucrados

- `src/` — Paquete principal con capas: `domain/`, `application/`, `infrastructure/`, `adapters/`, `core/`
- `tests/` — Suite de pruebas: `unit/`, `integration/`, `e2e/`
- `.gitignore` — Exclusión de secretos, caché, artefactos de build
- `pyproject.toml` — Configuración central de ruff, black, pytest, mypy, coverage

## Criterios de Aceptación

- [x] Estructura `src/` con 5 capas Clean Architecture y subdirectorios vacíos con `__init__.py`
- [x] Estructura `tests/` con `unit/`, `integration/`, `e2e/` y `__init__.py`
- [x] `.gitignore` excluye `.env`, `__pycache__/`, `.venv/`, `*.pyc`, `dist/`, `build/`
- [x] `pyproject.toml` configura ruff (E/W/F/I/N/UP/B/SIM/TCH/RUF), black, pytest, mypy, coverage

## Dependencias

Ninguna

## Estado

**Completado** — 2026-05-14
