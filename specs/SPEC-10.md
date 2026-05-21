# SPEC-10: Configuración DB

## Descripción

Configurar la conexión a PostgreSQL 16+ con `asyncpg`, connection pooling gestionado por el lifespan de FastAPI, y health endpoint con verificación de conectividad.

## Fase

F1 — Infraestructura DB

## Archivos Involucrados

- `src/infrastructure/db/connection.py` — Pool de conexiones asyncpg: `init_pool()`, `close_pool()`, `get_pool()`, `get_db()`
- `src/main.py` — Lifespan de FastAPI que inicializa y cierra el pool
- `src/adapters/api/routers/health.py` — Endpoint `GET /v1/health` con `SELECT 1`
- `docker-compose.yml` — Servicio PostgreSQL 16-alpine con healthcheck

## Criterios de Aceptación

- [x] `init_pool(Settings())` crea pool asyncpg con `min_size` y `max_size` configurables via Settings (`db_pool_min_size`, `db_pool_max_size`, default: 2 y 10)
- [x] Pool se inicializa al arrancar FastAPI y se cierra al apagar (lifespan)
- [x] `get_pool()` retorna el pool activo o `None` si no inicializado
- [x] `get_db()` es dependency de FastAPI que inyecta el pool en endpoints
- [x] `GET /v1/health` retorna `{"status": "ok", "db": "connected"}` con DB disponible
- [x] `GET /v1/health` retorna `{"status": "degraded", "db": "unavailable"}` sin DB
- [x] Pool initialization failure es graceful en development (log warning, pool=None)
- [x] En **production**, `init_pool()` lanza `RuntimeError` si la DB no está disponible (no permite startup silencioso)
- [x] `statement_timeout` para queries de API se configura con **SQL parametrizado** (`SET statement_timeout = $1`), no f-string
- [x] DSN de testcontainers convertido de `postgresql+psycopg2://` a `postgresql://` para asyncpg
- [x] Tests unitarios de health endpoint validan ambos escenarios

## Decisiones de Diseño

| Decisión | Racional |
|----------|----------|
| Pool size configurable via Settings | Permite ajuste sin modificar código. Default 2-10 balance entre recursos y concurrencia |
| Production fail-hard | En producción, no permitir startup silencioso sin DB — mejor crash que servicio degradado invisible |
| SQL parametrizado (`$1`) | `SET statement_timeout = $1` sigue la convención asyncpg y previene SQL injection incluso para valores numéricos |
| Graceful fallback en development | La DB puede no estar lista durante startup temprano en modo desarrollo |
| Health degraded (no error HTTP) | Indicador informativo, no error — la app funciona sin datos |
| Singleton a nivel de módulo | Pool gestionado por lifespan, no necesita clase |

## Dependencias

Spec-02 (Entorno de desarrollo)

## Estado

**Completado** — 2026-05-15
