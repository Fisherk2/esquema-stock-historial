# SPEC-01: Structure and Conventions

## Description

Establish the base project structure following Clean Architecture, naming conventions, and quality tool configuration.

## Phase

F0 — Preparation

## Involved Files

- `src/` — Main package with layers: `domain/`, `application/`, `infrastructure/`, `adapters/`, `core/`
- `tests/` — Test suite: `unit/`, `integration/`, `e2e/`
- `.gitignore` — Exclusion of secrets, cache, build artifacts
- `pyproject.toml` — Central configuration for ruff, black, pytest, mypy, coverage

## Acceptance Criteria

- [x] `src/` structure with 5 Clean Architecture layers and empty subdirectories with `__init__.py`
- [x] `tests/` structure with `unit/`, `integration/`, `e2e/` and `__init__.py`
- [x] `.gitignore` excludes `.env`, `__pycache__/`, `.venv/`, `*.pyc`, `dist/`, `build/`
- [x] `pyproject.toml` configures ruff (E/W/F/I/N/UP/B/SIM/TCH/RUF), black, pytest, mypy, coverage

## Dependencies

None

## Status

**Completed** — 2026-05-14
