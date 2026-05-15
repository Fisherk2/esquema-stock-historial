# SPEC-02: Entorno de desarrollo

## Descripción

Configurar el entorno de desarrollo local con Docker Compose, variables de entorno y comandos de automatización.

## Fase

F0 — Preparación

## Archivos Involucrados

- `docker-compose.yml` — PostgreSQL 16 + app FastAPI con healthchecks
- `.env.example` — Plantilla de variables de entorno (`DATABASE_URL`, `APP_HOST`, `APP_PORT`, `LOG_LEVEL`, `ENVIRONMENT`)
- `Makefile` — Comandos: `install`, `dev`, `lint`, `format`, `test`, `test-cov`, `build`, `docker-up`, `docker-down`, `clean`
- `requirements.txt` — Dependencias pinned para F0–F7

## Criterios de Aceptación

- [x] `docker compose up` inicia PostgreSQL y la app con healthchecks configurados
- [x] `.env.example` lista todas las variables de entorno requeridas
- [x] `Makefile` ejecuta todos los comandos de desarrollo sin errores
- [x] `requirements.txt` tiene dependencias pinned con versiones exactas

## Dependencias

Spec-01 (Estructura y convenciones)

## Estado

**Completado** — 2026-05-14
