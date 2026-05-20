# SPEC-61: Tests de Integración — Edge Cases & Escenarios Extendidos

**Fase:** F6 — Testing Integral
**Dependencias:** Spec-30 (Repositorios) ✅ Completado, Spec-31 (Vistas Materializadas) ✅ Completado, Spec-60 (Unit Tests) — Pre-requisito inmediato
**Prioridad:** Alta
**Estado:** Aprobado

---

## Objective

Extender la suite de tests de integración existente (97 tests) con edge cases y escenarios no cubiertos que validan el comportamiento real de los repositorios, la vista materializada, el Unit of Work, y los endpoints API contra PostgreSQL real via testcontainers. Los tests de integración existentes validan happy paths; Spec-61 añade unhappy paths, boundary conditions, y escenarios de datos masivos.

**Principios de diseño:**
- **Reutilizar fixtures existentes** — `db_pool` (session), `db_clean` (function), `api_client` (function) sin modificación
- **Cero regresiones** — los 97 tests de integración existentes no se modifican
- **Edge cases por capa** — repositorios, MV, UoW, API endpoints cada uno con sus propios edge cases
- **Datos masivos** — probar con 100+ movimientos para validar rendimiento de MV y paginación
- **Aislamiento garantizado** — cada test usa `db_clean` para estado limpio

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| Reutilizar `db_pool`/`db_clean` sin cambios | Los fixtures existentes son robustos (1 contenedor, ~20s). Modificarlos arriesga regresiones en 97 tests |
| Edge cases en archivos separados | No modificar archivos existentes. Crear `test_*_edge_cases.py` para cada módulo |
| Datos masivos con SQL batch insert | 100+ movimientos insertados con `executemany` o `unnest` para eficiencia. No usar la API para crear 100 movimientos |
| Tests de MV con y sin refresh | Validar consistencia entre MV y cálculo directo con diferentes volúmenes de datos |
| API edge cases contra `httpx.AsyncClient` | Misma infraestructura que los tests de integración existentes |

---

## Repository Edge Cases

### `tests/integration/repositories/test_movement_repository_edge.py`

| Test | Descripción | Expected |
|------|-------------|----------|
| `test_create_movement_returns_id` | Movimiento se crea y retorna ID auto-generado | ID > 0, misma data |
| `test_get_by_id_not_found` | Buscar movimiento inexistente | Retorna `None` |
| `test_list_by_product_empty` | Producto sin movimientos | Lista vacía, total=0 |
| `test_list_by_product_pagination_offset_exceeds` | Offset > total de movimientos | Lista vacía, total correcto |
| `test_list_by_product_pagination_limit_zero` | Limit=0 | Lista vacía, total correcto |
| `test_count_by_product_no_movements` | Contar movimientos de producto sin movimientos | count=0 |

### `tests/integration/repositories/test_product_repository_edge.py`

| Test | Descripción | Expected |
|------|-------------|----------|
| `test_get_by_sku_not_found` | Buscar SKU inexistente | Retorna `None` |
| `test_get_by_id_not_found` | Buscar producto inexistente | Retorna `None` |
| `test_list_below_threshold_none` | Todos los productos con stock > umbral | Lista vacía |
| `test_list_products_pagination_offset_exceeds` | Offset > total | Lista vacía, total correcto |
| `test_count_all_empty` | Contar productos cuando no hay ninguno | count=0 |

### `tests/integration/repositories/test_category_repository_edge.py`

| Test | Descripción | Expected |
|------|-------------|----------|
| `test_get_by_id_not_found` | Buscar categoría inexistente | Retorna `None` |
| `test_list_all_empty` | Listar categorías cuando no hay ninguna | Lista vacía |
| `test_create_duplicate_name` | Crear categoría con nombre duplicado | `UniqueViolationError` de asyncpg |

### `tests/integration/repositories/test_stock_query_repository_edge.py`

| Test | Descripción | Expected |
|------|-------------|----------|
| `test_get_current_stock_product_without_movements` | Producto sin movimientos | Stock = 0.0 |
| `test_get_stock_at_date_future_date` | Fecha futura (no hay movimientos) | Stock = 0.0 |
| `test_get_stock_at_date_exact_movement_time` | Fecha exacta de un movimiento | Incluye ese movimiento |
| `test_get_stock_at_date_before_any_movement` | Fecha anterior a todos los movimientos | Stock = 0.0 |
| `test_get_current_stock_after_mixed_movements` | IN+OUT+ADJUSTMENT en secuencia | Stock neto correcto |
| `test_get_current_stock_fallback_without_mv` | Vista MV dropeada → fallback a cálculo directo | Stock correcto, sin error |

---

## Materialized View Edge Cases

### `tests/integration/test_mv_stock_edge.py`

| Test | Descripción | Expected |
|------|-------------|----------|
| `test_mv_consistency_with_100_movements` | Insertar 100 movimientos, refresh, comparar MV vs cálculo directo | Valores idénticos |
| `test_mv_refresh_concurrently_does_not_block_reads` | Lectura durante refresh concurrente | Lectura retorna datos (posiblemente stale), sin error |
| `test_mv_data_after_partial_truncate` | TRUNCATE movements, refresh → MV actualizada | MV refleja datos actuales |
| `test_mv_stock_multiple_products` | 10 productos × 10 movimientos cada uno | Stock correcto por producto |
| `test_mv_refresh_after_large_batch` | Batch insert de 500 movimientos + refresh | MV correcta, sin timeout con 30s |

### Batch Insert Helper

```python
# tests/integration/helpers.py
async def insert_batch_movements(
    pool: asyncpg.Pool,
    product_id: int,
    count: int,
    movement_type: str = "IN",
    quantity: int = 10,
) -> None:
    """Inserta N movimientos en batch para tests de datos masivos."""
    await pool.executemany(
        """
        INSERT INTO movements (product_id, movement_type, quantity, metadata, created_at)
        VALUES ($1, $2, $3, $4, now() - interval '1 minute' * (random() * 1000)::int)
        """,
        [(product_id, movement_type, quantity, "{}")] * count,
    )
```

---

## Unit of Work Edge Cases

### `tests/integration/test_uow_edge.py`

| Test | Descripción | Expected |
|------|-------------|----------|
| `test_uow_rollback_on_second_repo_error` | Error en segundo repositorio dentro de UoW | Ningún dato persistido |
| `test_uow_shared_connection_between_repos` | Dos repos en misma transacción comparten conexión | Datos consistentes |
| `test_uow_nested_context_managers` | UoW anidado (si se permite) | Comportamiento definido (probablemente error o reutilizar conexión) |
| `test_uow_connection_released_after_exception` | Conexión se libera al pool incluso con excepción | Pool size restaurado |

---

## API Endpoint Edge Cases

### `tests/integration/api/test_movements_api_edge.py`

| Test | Descripción | Expected |
|------|-------------|----------|
| `test_create_movement_invalid_product_id` | product_id no numérico en URL | 422 Unprocessable |
| `test_create_movement_empty_body` | POST sin body | 422 Unprocessable |
| `test_create_movement_extra_fields` | POST con campos extra desconocidos | 422 (strict mode) o ignora |
| `test_get_movement_nonexistent_id` | GET /v1/movements/99999 | 404 Not Found |
| `test_list_movements_invalid_product_id` | product_id=abc en query param | 422 Unprocessable |
| `test_create_movement_negative_quantity` | quantity=-5 | 422 (Pydantic validation) |

### `tests/integration/api/test_stock_api_edge.py`

| Test | Descripción | Expected |
|------|-------------|----------|
| `test_current_stock_nonexistent_product` | GET /v1/stock/99999/current | 404 Not Found |
| `test_stock_at_date_invalid_date_format` | date=not-a-date | 422 Unprocessable |
| `test_stock_at_date_no_query_param` | GET /v1/stock/1/at-date sin ?date= | 422 (missing required param) |

### `tests/integration/api/test_products_api_edge.py`

| Test | Descripción | Expected |
|------|-------------|----------|
| `test_create_product_invalid_sku_format` | SKU con caracteres especiales | 422 Unprocessable |
| `test_create_product_duplicate_sku` | SKU que ya existe | 409 Conflict |
| `test_create_product_nonexistent_category` | category_id=99999 | Error de FK |
| `test_list_products_large_offset` | offset=99999 | 200, lista vacía |
| `test_get_product_nonexistent_id` | GET /v1/products/99999 | 404 Not Found |

### `tests/integration/api/test_categories_api_edge.py`

| Test | Descripción | Expected |
|------|-------------|----------|
| `test_create_category_duplicate_name` | Nombre que ya existe | 409 Conflict |
| `test_create_category_empty_name` | name="" | 422 Unprocessable |
| `test_create_category_name_too_long` | name con 500+ caracteres | 422 o acepta (verificar) |

---

## Files

| File | Description | Action |
|------|-------------|--------|
| `tests/integration/repositories/test_movement_repository_edge.py` | Edge cases de MovementRepository | NEW |
| `tests/integration/repositories/test_product_repository_edge.py` | Edge cases de ProductRepository | NEW |
| `tests/integration/repositories/test_category_repository_edge.py` | Edge cases de CategoryRepository | NEW |
| `tests/integration/repositories/test_stock_query_repository_edge.py` | Edge cases de StockQueryRepository | NEW |
| `tests/integration/test_mv_stock_edge.py` | Edge cases de MV con datos masivos | NEW |
| `tests/integration/test_uow_edge.py` | Edge cases de Unit of Work | NEW |
| `tests/integration/api/test_movements_api_edge.py` | Edge cases de movements API | NEW |
| `tests/integration/api/test_stock_api_edge.py` | Edge cases de stock API | NEW |
| `tests/integration/api/test_products_api_edge.py` | Edge cases de products API | NEW |
| `tests/integration/api/test_categories_api_edge.py` | Edge cases de categories API | NEW |
| `tests/integration/helpers.py` | Helper para batch inserts | NEW |

---

## Acceptance Criteria

- [ ] Edge cases en repositorios: producto sin movimientos, stock_at_date con fecha futura, paginación con offset > total, get_by_id not found, count=0
- [ ] Edge cases en API: content-type inválido, body vacío, campos extra, query params inválidos, IDs inexistentes, fechas inválidas, duplicados
- [ ] Tests de MV: refresh con datos masivos (100+ movimientos), consistencia MV vs cálculo directo, lectura durante refresh
- [ ] Tests de UoW: rollback en segundo repositorio, conexión compartida, conexión liberada tras excepción
- [ ] Coverage `infrastructure/` ≥70%
- [ ] 0 regresiones en 97 tests de integración existentes
- [ ] Todos los edge case tests pasan contra testcontainers PostgreSQL real
- [ ] `make lint` pasa sin errores

---

## Testing Strategy

- **Todos los tests usan testcontainers PostgreSQL real** — no mocks para repositorios de integración
- **`db_clean` para cada test** — datos limpios garantizan aislamiento
- **`api_client` para tests de API** — httpx.AsyncClient con ASGITransport
- **Batch inserts para datos masivos** — `executemany` para eficiencia, no la API
- **Comparación MV vs cálculo directo** — insertar → refresh → comparar con SUM manual

### Ejemplo: Test de edge case en repositorio

```python
# tests/integration/repositories/test_stock_query_repository_edge.py
async def test_get_stock_at_date_future_date(db_clean: asyncpg.Pool) -> None:
    """Edge case: consultar stock en fecha futura retorna 0.0."""
    repo = PostgresStockQueryRepository(db_clean)

    # Crear producto y movimiento en el pasado
    product_id = await _create_test_product(db_clean)
    await _create_test_movement(db_clean, product_id, "IN", 100)

    # Consultar fecha futura
    future_date = datetime.now(timezone.utc) + timedelta(days=365)
    stock = await repo.get_stock_at_date(product_id, future_date)

    # El stock futuro debe ser el mismo que el actual (los movimientos futuros no existen)
    assert stock == 100.0  # Movimientos existentes cuentan
```

---

## Resolved Questions

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| F6-61-Q1 | ¿Modificar tests de integración existentes? | **No** — crear archivos `_edge.py` separados | Los 97 tests existentes son happy paths validados. Modificarlos arriesga regresiones |
| F6-61-Q2 | ¿Datos masivos con API o SQL directo? | **SQL directo (batch insert)** | Crear 100+ movimientos via API sería lento y frágil. SQL directo es eficiente y controlado |
| F6-61-Q3 | ¿Probar MV con datos masivos (500+)? | **Sí, hasta 500** | Valida que refresh no timeout con 30s. Más allá de 500 es para load testing (Spec-62) |
| F6-61-Q4 | ¿Helper de batch insert compartido? | **Sí, `tests/integration/helpers.py`** | Evita duplicación de SQL de setup entre archivos de test |
