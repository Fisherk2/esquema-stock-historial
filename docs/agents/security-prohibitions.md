# Seguridad y Prohibiciones

## Validación y Sanitización

- **Inputs:** Pydantic valida tipos, rangos, formatos UUID/ISO8601. Rechazo automático de payloads malformados (`HTTP 422`).
- **SQL Injection:** Zero tolerancia. Uso estricto de parámetros posicionales/nombrados (`$1`, `$2`). Nunca concatenación de strings para queries.
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
