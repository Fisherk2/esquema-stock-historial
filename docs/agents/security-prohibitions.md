# Seguridad y Prohibiciones

## Validación y Sanitización

- **Inputs:** Pydantic valida tipos, rangos, formatos UUID/ISO8601. Rechazo automático de payloads malformados (`HTTP 422`).
- **SQL Injection:** Zero tolerancia. Uso estricto de parámetros posicionales/nombrados (`$1`, `$2`). Nunca concatenación de strings para queries, incluyendo `SET` statements (ej: `SET statement_timeout = $1`, no f-string).
- **JSONB:** asyncpg maneja `dict → JSONB` nativamente. Nunca usar `json.dumps()` para parámetros JSONB — esto duplica la serialización y puede causar doble-encoding.
- **Secretos:** `.env` nunca versionado. Variables sensibles cargadas vía `pydantic-settings`. Rotación automática en CI.

## Control de Excepciones y Límites

- **Rate Limiting:** Middleware básico en FastAPI (`slowapi` o manual) para endpoints de lectura masiva.
- **Deadlines:** Timeouts explícitos en `asyncpg.connect()`. Circuit breaker implícito vía retry limits.
- **Logging:** Estructurado (JSON). Nunca loggear datos sensibles o stacks completos en prod.

## Prácticas Prohibidas

1. Hardcoded credentials, URLs o queries SQL en código.
2. Side-effects ocultos: funciones que leen/escriben a la DB sin ser declaradas como tal.
3. Acoplamiento temporal: lógica que depende del orden de ejecución implícito de imports o módulos globales.
4. God Objects / Fat Controllers: clases >300 líneas o funciones con múltiples responsabilidades.
5. ORM para queries analíticas complejas: SQLAlchemy ORM para CTEs/Window Functions está prohibido.
6. `print()` en producción. Usar `logging` o `structlog`.
7. Ignorar `async/await`: mezclar código síncrono en rutas async bloquea el event loop.
8. Modificar datos históricos: `UPDATE` o `DELETE` en tabla `movements`. Solo `INSERT`. Si hay error, insertar movimiento compensatorio.

## Estado de Seguridad MVP (Pre-Produccion)

> **Nota:** Este proyecto en su estado actual es un **MVP sin despliegue real a produccion**. Las siguientes limitaciones son conocidas y deben resolverse antes de un despliegue productivo.

### Limitaciones conocidas del MVP

| Componente | Estado MVP | Requisito Pre-Produccion |
|---|---|---|
| **Authentication** | ❌ No implementado | API keys o JWT/OAuth2 con RBAC |
| **Authorization** | ❌ No implementado | Roles: admin, warehouse, readonly |
| **Rate Limiting** | ❌ No implementado | `slowapi` o middleware manual |
| **CORS** | ❌ No implementado | `CORSMiddleware` con allowlist de origenes |
| **OpenAPI Docs** | ⚠️ Activos en prod | Deshabilitar `/docs`, `/redoc`, `/openapi.json` |
| **Security Headers** | ✅ Implementado (v1.0.2) | `nosniff`, `deny`, `no-store`, `referrer-policy` |
| **SQL Injection** | ✅ Prevenido | asyncpg parametrizado en todos los queries |
| **Input Validation** | ✅ Implementado | Pydantic `strict=True`, `extra="forbid"` |
| **Error Handling** | ✅ Implementado (v1.0.2) | Sin leakage de stack traces. ValueError handler verifica origen del traceback. |
| **Race Conditions** | ✅ Prevenido (v1.0.2) | `SELECT FOR UPDATE` + calculo directo dentro del UoW |
| **Statement Timeout** | ✅ Enforcement (v1.0.2) | `server_settings` en pool — aplica a todas las conexiones |

### Checklist pre-despliegue a produccion

Antes de desplegar a produccion, completar:

- [ ] Implementar autenticacion (API key o JWT)
- [ ] Configurar autorizacion por roles
- [ ] Agregar rate limiting (slowapi)
- [ ] Configurar CORS con origenes especificos
- [ ] Deshabilitar OpenAPI docs en produccion
- [ ] Agregar HSTS via reverse proxy (nginx/traefik)
- [ ] Configurar monitorizacion y alertas
- [ ] Documentar plan de rollback
- [ ] Ejecutar auditoria de dependencias (`pip-audit`)
- [ ] Verificar que todas las variables de entorno estan configuradas
