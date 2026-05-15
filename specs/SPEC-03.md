# SPEC-03: Calidad y automatización

## Descripción

Configurar herramientas de calidad de código (linter, formatter) y automatización CI/CD con pre-commit hooks y GitHub Actions.

## Fase

F0 — Preparación

## Archivos Involucrados

- `.pre-commit-config.yaml` — Hooks: ruff, ruff-format, black, trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files
- `pyproject.toml` — Configuración de ruff (select E/W/F/I/N/UP/B/SIM/TCH/RUF, ban-relative-imports), black, pytest, mypy
- `.github/workflows/ci.yml` — Pipeline: lint (ruff) + test (pytest) + coverage

## Criterios de Aceptación

- [x] Pre-commit hooks configurados y funcionales
- [x] `make lint` ejecuta ruff sin errores
- [x] `make format` ejecuta black sin errores
- [x] CI ejecuta lint y test en push/PR a main
- [x] CI ejecuta coverage con umbral mínimo de 80%

## Dependencias

Spec-01 (Estructura y convenciones), Spec-02 (Entorno de desarrollo)

## Estado

**Completado** — 2026-05-14
