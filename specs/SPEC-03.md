# SPEC-03: Quality and Automation

## Description

Set up code quality tools (linter, formatter) and CI/CD automation with pre-commit hooks and GitHub Actions.

## Phase

F0 — Preparation

## Involved Files

- `.pre-commit-config.yaml` — Hooks: ruff, ruff-format, black, trailing-whitespace, end-of-file-fixer, check-yaml, check-added-large-files
- `pyproject.toml` — Ruff configuration (select E/W/F/I/N/UP/B/SIM/TCH/RUF, ban-relative-imports), black, pytest, mypy
- `.github/workflows/ci.yml` — Pipeline: lint (ruff) + test (pytest) + coverage

## Acceptance Criteria

- [x] Pre-commit hooks configured and functional
- [x] `make lint` runs ruff without errors
- [x] `make format` runs black without errors
- [x] CI runs lint and test on push/PR to main
- [x] CI runs coverage with minimum threshold of 80%

## Dependencies

Spec-01 (Structure and Conventions), Spec-02 (Development Environment)

## Status

**Completed** — 2026-05-14
