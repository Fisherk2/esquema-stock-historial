# SPEC-02: Development Environment

## Description

Set up the local development environment with Docker Compose, environment variables, and automation commands.

## Phase

F0 — Preparation

## Involved Files

- `docker-compose.yml` — PostgreSQL 16 + FastAPI app with healthchecks
- `.env.example` — Environment variable template (`DATABASE_URL`, `APP_HOST`, `APP_PORT`, `LOG_LEVEL`, `ENVIRONMENT`)
- `Makefile` — Commands: `install`, `dev`, `lint`, `format`, `test`, `test-cov`, `build`, `docker-up`, `docker-down`, `clean`
- `requirements.txt` — Pinned dependencies for F0–F7

## Acceptance Criteria

- [x] `docker compose up` starts PostgreSQL and the app with configured healthchecks
- [x] `.env.example` lists all required environment variables
- [x] `Makefile` runs all development commands without errors
- [x] `requirements.txt` has pinned dependencies with exact versions

## Dependencies

Spec-01 (Structure and Conventions)

## Status

**Completed** — 2026-05-14
