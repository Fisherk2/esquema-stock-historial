# Setup Guide — Stock Historial

## Prerequisitos

| Software | Versión mínima | Notas |
|---|---|---|
| Python | 3.12+ | Requiere `pip` |
| PostgreSQL | 16+ | Para desarrollo local (opcional si usas Docker) |
| Docker | 24+ | Para Docker Compose (recomendado) |
| Docker Compose | 2.20+ | Plugin de Docker |
| Git | 2.40+ | Control de versiones |
| GNU Make | 3.82+ | Para ejecutar comandos del Makefile |

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Fisherk2/esquema-stock-historial.git
cd esquema-stock-historial
```

### 2. Instalar dependencias

```bash
make install
```

### 3. Configurar variables de entorno

Copiar `.env.example` a `.env` y ajustar las credenciales:

```bash
cp .env.example .env
```

Editar `.env` con tu editor favorito. La variable más importante es `DATABASE_URL`:

```bash
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/stock_historial
```

### 4. Ejecutar migraciones

```bash
make migrate
```

### 5. (Opcional) Insertar datos de prueba

```bash
make seed
```

## Desarrollo Local

### Con PostgreSQL local

1. Asegúrate de que PostgreSQL está corriendo localmente
2. Configura `DATABASE_URL` en `.env` apuntando a tu instancia local
3. Ejecuta las migraciones: `make migrate`
4. Inicia el servidor:

```bash
make dev
```

El servidor estará disponible en `http://localhost:8000`. La documentación OpenAPI en `/docs`.

### Con Docker (Dev)

Inicia PostgreSQL y la app con Docker Compose:

```bash
make docker-up
```

Esto levanta:
- PostgreSQL en `localhost:5432` (expuesto para debugging)
- FastAPI app en `http://localhost:8000` con hot reload

Para detener:

```bash
make docker-down
```

## Docker (Producción)

El stack de producción difiere del de desarrollo en:
- PostgreSQL **no expuesto** al host (solo comunicación interna)
- Variables de entorno desde `.env`
- Política de restart `unless-stopped`
- Logs en formato JSON

### Levantar

```bash
make docker-prod-up
```

### Verificar

```bash
# Health check
curl http://localhost:8000/v1/health

# Verificar que PostgreSQL NO está expuesto
ss -tlnp | grep 5432  # Debe estar vacío
```

### Detener

```bash
make docker-prod-down
```

## Demo

Con el servidor corriendo (local o Docker), ejecuta el script de demostración:

```bash
make demo
```

Esto ejecuta un flujo completo: health check → crear categoria → crear producto → movimiento IN → consultar stock → movimiento OUT → consultar stock actualizado → stock histórico → listar movimientos.

La URL base se configura con `DEMO_BASE_URL`:

```bash
DEMO_BASE_URL=http://localhost:8000 make demo
```

## Variables de Entorno

| Variable | Default | Descripción | Desde |
|---|---|---|---|
| `APP_NAME` | Stock Historial | Nombre de la app para logs | F0 |
| `APP_HOST` | 0.0.0.0 | Interfaz de red | F0 |
| `APP_PORT` | 8000 | Puerto HTTP | F0 |
| `LOG_LEVEL` | info | Nivel de log (debug/info/warning/error) | F0 |
| `LOG_FORMAT` | text | Formato (text/json) | F0 |
| `ENVIRONMENT` | development | Entorno (development/staging/production) | F0 |
| `DATABASE_URL` | — | DSN asyncpg de conexión | F0 |
| `SCHEDULER_ENABLED` | true | Habilitar scheduler | F5 |
| `SCHEDULER_REFRESH_INTERVAL_MINUTES` | 5 | Intervalo refresh MV | F5 |
| `SCHEDULER_MISFIRE_GRACE_TIME_SECONDS` | 60 | Tolerancia jobs retrasados | F5 |
| `SCHEDULER_STATEMENT_TIMEOUT_SECONDS` | 30 | Timeout refresh job | F5 |
| `API_STATEMENT_TIMEOUT_SECONDS` | 5 | Timeout queries API | F5 |
| `POSTGRES_USER` | stock_user | Usuario PostgreSQL prod | F7 |
| `POSTGRES_PASSWORD` | — | Contraseña PostgreSQL prod | F7 |
| `POSTGRES_DB` | stock_historial | Base de datos prod | F7 |
| `DEMO_BASE_URL` | http://localhost:8000 | URL base demo script | F7 |

## Migraciones

```bash
# Ejecutar migraciones
make migrate

# Insertar datos de prueba
make seed
```

Las migraciones están en `migrations/` y se ejecutan con el módulo `src.infrastructure.db.migrate`.

## Troubleshooting

| Problema | Solución |
|---|---|
| **`asyncpg.exceptions.ConnectionDoesNotExistError`** | Verifica que PostgreSQL está corriendo. Revisa `DATABASE_URL` en `.env` |
| **`Connection refused` al hacer `make docker-up`** | Puerto 5432 en uso por otra instancia de PostgreSQL. Detén la instancia local o cambia el puerto |
| **`POSTGRES_PASSWORD is required`** | Define `POSTGRES_PASSWORD` en tu archivo `.env` antes de `make docker-prod-up` |
| **`make test` falla con `testcontainers`** | Docker daemon no disponible. Verifica `docker ps` |
| **`make lint` falla con import errors** | Dependencias no instaladas. Ejecuta `make install` |
| **Health check retorna `degraded`** | La app no puede conectar a la DB. Verifica `DATABASE_URL` y que PostgreSQL está accesible |
| **`make demo` falla con `curl` error** | El servidor no está corriendo. Ejecuta `make dev` o `make docker-up` primero |
| **Vista materializada no actualizada** | El scheduler puede estar deshabilitado. Verifica `SCHEDULER_ENABLED=true` en `.env` |
| **`mypy` reporta errores de tipo** | Ejecuta `make typecheck` para ver los errores detallados |
| **Docker build falla** | Verifica que `requirements.txt` está actualizado y no hay dependencias rotas |

## Links Útiles

- [Arquitectura](ARCHITECTURE.md) — Diagramas y patrones
- [API Reference](API_REFERENCE.md) — 11 endpoints documentados
- [Contributing](../CONTRIBUTING.md) — Guía para contribuidores
- [AGENTS.md](../AGENTS.md) — Guía para agentes de desarrollo
