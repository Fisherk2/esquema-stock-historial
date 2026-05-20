# SPEC-63: Pruebas de Seguridad — SQL Injection + Input Validation

**Fase:** F6 — Testing Integral
**Dependencias:** Spec-42 (Rutas FastAPI) ✅ Completado, Spec-52 (Logging & Errors) ✅ Completado
**Prioridad:** Media
**Estado:** Aprobado

---

## Objective

Implementar la suite de tests de seguridad que valida las dos áreas críticas del sistema: (1) **SQL Injection** — verificar que los repositorios y endpoints son inmunes a payloads de inyección SQL; (2) **Input Validation** — verificar que los DTOs Pydantic rechazan inputs maliciosos, fuera de rango, o malformados. El scope se limita a estas dos áreas (no incluye autenticación, autorización, ni timing attacks).

**Principios de diseño:**
- **Tests de seguridad como regression suite** — no son one-time audits; se ejecutan en cada CI run
- **Cero nuevas dependencias de producción** — los tests usan `httpx.AsyncClient` existente
- **Payloads reales de OWASP** — no inventar payloads; usar los catalogados en OWASP Testing Guide v4
- **Scope explícito** — solo SQL injection + input validation. Auth, rate limiting, y CORS quedan fuera de F6
- **Cero regresiones** — todos los tests existentes deben seguir pasando

---

## Design Decisions

| Decisión | Racional |
|----------|----------|
| Scope: SQL injection + input validation solo | Auth/authorization no existen en el sistema (no hay usuarios). Rate limiting y CORS son de F7+. Timing attacks requieren infraestructura de medición fuera de scope |
| Payloads de OWASP Testing Guide v4 | Standard de la industria. No inventar payloads propios reduce falsos positivos |
| Tests contra API (httpx) + tests contra repositorios (asyncpg) | Doble validación: la API es la primera línea de defensa (Pydantic), los repositorios son la última (parameterized queries) |
| No añadir `sqlmap` ni herramientas externas | `sqlmap` requiere servidor corriendo y es no-determinista. Los tests de pytest son deterministas, reproducibles, y se integran en CI |
| Directorio `tests/security/` separado | Separación clara de concerns. Los tests de seguridad no se mezclan con unit/integration/e2e |
| Error leakage tests en security (no en integration) | La verificación de que los errores no exponen stack traces o SQL internals es inherentemente una preocupación de seguridad |

---

## SQL Injection Tests

### Strategy

Los repositorios usan **parameterized queries** (`$1`, `$2`, `$3`) con asyncpg. Este patrón es inherentemente seguro contra SQL injection porque los parámetros se envían fuera del query text. Los tests verifican que:

1. **Payloads de SQL injection en path params** → FastAPI type coercion (int) rechaza antes de llegar a SQL
2. **Payloads de SQL injection en query params** → Pydantic validation rechaza antes de llegar a SQL
3. **Payloads de SQL injection en body fields** → Pydantic `strict=True` rechaza tipos inesperados
4. **Payloads de SQL injection en repositorios** → asyncpg parameterized queries tratan el payload como valor literal, no como SQL

### `tests/security/test_sql_injection.py`

```python
"""Tests de seguridad: SQL Injection.

Valida que el sistema es inmune a payloads de SQL injection
catalogados en OWASP Testing Guide v4. Los tests cubren:
1. Path parameters (product_id, movement_id)
2. Query parameters (date, limit, offset)
3. Body fields (SKU, reference, metadata values)
4. Repository-level parameterized queries

La defensa opera en tres capas:
- Capa 1: FastAPI type coercion (int para path params)
- Capa 2: Pydantic strict validation (tipos, rangos, regex)
- Capa 3: asyncpg parameterized queries ($1, $2, $3)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx
    import asyncpg


# ── OWASP SQL Injection Payloads ─────────────────────────────────────────

SQL_INJECTION_PATH_PARAMS = [
    "1 OR 1=1",
    "1; DROP TABLE movements;--",
    "1 UNION SELECT * FROM products--",
    "1' OR '1'='1",
    "1; INSERT INTO movements VALUES (1, 'IN', 999, '{}', NULL, now());--",
    "../../../etc/passwd",
    "1 AND (SELECT * FROM (SELECT(SLEEP(5)))a)",
]

SQL_INJECTION_STRING_FIELDS = [
    "' OR '1'='1;--",
    "'; DROP TABLE movements;--",
    "' UNION SELECT id, sku, name, 1, 1, 'unit' FROM products--",
    "1; EXEC xp_cmdshell 'dir';--",
    "' OR 1=1 --",
    "Robert'); DROP TABLE students;--",
    "<script>alert('xss')</script>",
    "${7*7}",
    "{{7*7}}",
    "null",
    "undefined",
    "NaN",
    "Infinity",
]


class TestSQLInjectionPathParams:
    """SQL injection en path parameters debe ser rechazado por FastAPI."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_PATH_PARAMS)
    async def test_stock_current_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """GET /v1/stock/{payload}/current → 422 (FastAPI rechaza non-int)."""
        resp = await api_client.get(f"/v1/stock/{payload}/current")
        assert resp.status_code in (404, 422)
        # Verificar que no hay SQL error en la respuesta
        body = resp.json()
        assert "syntax error" not in str(body).lower()
        assert "sql" not in str(body).lower()

    @pytest.mark.parametrize("payload", SQL_INJECTION_PATH_PARAMS)
    async def test_stock_at_date_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """GET /v1/stock/{payload}/at-date → 422 (FastAPI rechaza non-int)."""
        resp = await api_client.get(f"/v1/stock/{payload}/at-date?date=2025-01-01T00:00:00Z")
        assert resp.status_code in (404, 422)
        body = resp.json()
        assert "syntax error" not in str(body).lower()

    @pytest.mark.parametrize("payload", SQL_INJECTION_PATH_PARAMS)
    async def test_movement_get_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """GET /v1/movements/{payload} → 422 (FastAPI rechaza non-int)."""
        resp = await api_client.get(f"/v1/movements/{payload}")
        assert resp.status_code in (404, 422)
        body = resp.json()
        assert "syntax error" not in str(body).lower()

    @pytest.mark.parametrize("payload", SQL_INJECTION_PATH_PARAMS)
    async def test_product_get_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """GET /v1/products/{payload} → 422 (FastAPI rechaza non-int)."""
        resp = await api_client.get(f"/v1/products/{payload}")
        assert resp.status_code in (404, 422)


class TestSQLInjectionQueryParams:
    """SQL injection en query parameters debe ser rechazado por Pydantic/FastAPI."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_STRING_FIELDS)
    async def test_stock_at_date_date_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """GET /v1/stock/1/at-date?date={payload} → 422 (datetime validation)."""
        resp = await api_client.get(f"/v1/stock/1/at-date?date={payload}")
        assert resp.status_code == 422

    @pytest.mark.parametrize("payload", SQL_INJECTION_PATH_PARAMS)
    async def test_list_movements_product_id_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """GET /v1/movements?product_id={payload} → 422 (int validation)."""
        resp = await api_client.get(f"/v1/movements?product_id={payload}")
        assert resp.status_code == 422

    async def test_list_movements_limit_overflow(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """GET /v1/movements?limit=999999 → 422 (le=1000 constraint)."""
        resp = await api_client.get("/v1/movements?product_id=1&limit=999999")
        assert resp.status_code == 422

    async def test_list_movements_negative_offset(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """GET /v1/movements?offset=-1 → 422 (ge=0 constraint)."""
        resp = await api_client.get("/v1/movements?product_id=1&offset=-1")
        assert resp.status_code == 422


class TestSQLInjectionBodyFields:
    """SQL injection en body fields debe ser rechazado por Pydantic strict mode."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_STRING_FIELDS)
    async def test_create_movement_reference_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """POST /v1/movements con reference={payload} → no causa SQL error."""
        # Primero crear categoría y producto
        cat = await api_client.post("/v1/categories", json={"name": "sec-test"})
        cat_id = cat.json()["id"]
        product = await api_client.post("/v1/products", json={
            "sku": "SEC-REF-001",
            "name": "Security Test Product",
            "unit_of_measure": "unit",
            "category_id": cat_id,
        })
        product_id = product.json()["id"]

        resp = await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 10,
            "reference": payload,
        })
        # El movimiento se crea (el reference es un string válido para Pydantic)
        # pero el payload NO debe ejecutarse como SQL
        assert resp.status_code in (201, 422)
        if resp.status_code == 201:
            body = resp.json()
            # Verificar que el reference se almacenó literalmente
            assert body["reference"] == payload
            # Verificar que no hay SQL error
            assert "syntax error" not in str(body).lower()
            assert "sql" not in str(body).lower()

    @pytest.mark.parametrize("payload", SQL_INJECTION_STRING_FIELDS)
    async def test_create_product_sku_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """POST /v1/products con sku={payload} → 422 o almacenamiento literal."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-sku"})
        cat_id = cat.json()["id"]

        resp = await api_client.post("/v1/products", json={
            "sku": payload,
            "name": "Security Test",
            "unit_of_measure": "unit",
            "category_id": cat_id,
        })
        # SKU tiene regex validation — payloads con caracteres especiales → 422
        # Si pasa, debe almacenarse literalmente (no ejecutarse como SQL)
        assert resp.status_code in (201, 409, 422)
        if resp.status_code == 201:
            body = resp.json()
            assert body["sku"] == payload
            assert "sql" not in str(body).lower()


class TestSQLInjectionRepositoryLevel:
    """SQL injection a nivel de repositorio (parameterized queries asyncpg).

    Estos tests validan la capa más baja de defensa: asyncpg parameterized
    queries. Incluso si un payload pasara Pydantic y FastAPI, asyncpg
    lo trataría como un valor literal, no como SQL ejecutable.
    """

    async def test_movement_repo_injection_in_product_id(
        self, db_pool: asyncpg.Pool
    ) -> None:
        """MovementRepository.create() con string en product_id → error de tipo, no SQL."""
        from src.infrastructure.repositories.movement_repository import (
            PostgresMovementRepository,
        )

        repo = PostgresMovementRepository(db_pool)
        # Si se intenta pasar un string como product_id, asyncpg lanzaría
        # TypeError o ProgrammingError (no SQL injection)
        with pytest.raises((TypeError, Exception)):
            # Esto falla porque product_id es int en la firma del método
            await repo.get_by_id("1 OR 1=1")  # type: ignore[arg-type]

    async def test_stock_repo_injection_in_product_id(
        self, db_pool: asyncpg.Pool
    ) -> None:
        """StockQueryRepository con string en product_id → error de tipo, no SQL."""
        from src.infrastructure.repositories.stock_query_repository import (
            PostgresStockQueryRepository,
        )

        repo = PostgresStockQueryRepository(db_pool)
        with pytest.raises((TypeError, Exception)):
            await repo.get_current_stock("1; DROP TABLE movements;--")  # type: ignore[arg-type]

    async def test_parameterized_query_treats_payload_as_literal(
        self, db_pool: asyncpg.Pool
    ) -> None:
        """Un payload de SQL injection se almacena como string literal, no se ejecuta."""
        # Crear categoría y producto para el test
        cat_id = await db_pool.fetchval(
            "INSERT INTO categories (name) VALUES ($1) RETURNING id",
            "sec-literal-test",
        )
        product_id = await db_pool.fetchval(
            "INSERT INTO products (sku, name, unit_of_measure, category_id) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            "SEC-LIT-001", "Security Literal", "unit", cat_id,
        )

        # Insertar un movimiento con reference que contiene SQL
        injection = "'; DROP TABLE movements;--"
        movement_id = await db_pool.fetchval(
            "INSERT INTO movements (product_id, movement_type, quantity, metadata, reference, created_at) "
            "VALUES ($1, $2, $3, $4, $5, now()) RETURNING id",
            product_id, "IN", 10, "{}", injection,
        )

        # Verificar: el movimiento se creó con el reference literal
        row = await db_pool.fetchrow(
            "SELECT reference FROM movements WHERE id = $1", movement_id
        )
        assert row["reference"] == injection

        # Verificar: la tabla movements sigue existiendo (no se ejecutó el DROP)
        exists = await db_pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'movements')"
        )
        assert exists is True
```

---

## Input Validation Tests

### Strategy

Los DTOs Pydantic con `strict=True` y `Field` constraints son la primera línea de defensa. Los tests verifican que:

1. **Tipos incorrectos** → `strict=True` rechaza int como string, bool como int, etc.
2. **Campos fuera de rango** → `gt=0`, `le=1000`, `max_length=255` rechazan valores inválidos
3. **Campos requeridos ausentes** → 422 con detalle del campo faltante
4. **Campos extra desconocidos** → `strict=True` los rechaza
5. **Payloads malformados** → JSON inválido, body vacío, content-type incorrecto
6. **Metadata injection** → dict[str,str] con claves/valores maliciosos
7. **Unicode/encoding edge cases** → caracteres NULL, surrogates, overlong encoding

### `tests/security/test_input_validation.py`

```python
"""Tests de seguridad: Input Validation.

Valida que los DTOs Pydantic con strict=True rechazan inputs
maliciosos, fuera de rango, o malformados. Los tests cubren:
1. Tipos incorrectos (strict mode)
2. Valores fuera de rango (Field constraints)
3. Campos requeridos ausentes
4. Campos extra desconocidos
5. Payloads malformados (JSON inválido, body vacío)
6. Metadata con contenido malicioso
7. Unicode/encoding edge cases
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx


class TestCreateMovementInputValidation:
    """POST /v1/movements — validación de CreateMovementInput."""

    async def test_missing_required_fields(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Body vacío → 422 con detalle de campos faltantes."""
        resp = await api_client.post("/v1/movements", json={})
        assert resp.status_code == 422
        body = resp.json()
        missing_fields = {e["loc"][-1] for e in body.get("detail", [])}
        assert "product_id" in missing_fields
        assert "movement_type" in missing_fields
        assert "quantity" in missing_fields

    async def test_extra_fields_rejected(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Campos extra desconocidos → 422 (strict mode)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "IN",
            "quantity": 10,
            "extra_malicious_field": "hack",
        })
        # strict=True en Pydantic rechaza campos extra
        assert resp.status_code == 422

    async def test_negative_quantity(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """quantity=-5 → 422 (gt=0 constraint)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "IN",
            "quantity": -5,
        })
        assert resp.status_code == 422

    async def test_zero_quantity(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """quantity=0 → 422 (gt=0 constraint)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "IN",
            "quantity": 0,
        })
        assert resp.status_code == 422

    async def test_negative_product_id(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """product_id=-1 → 422 (gt=0 constraint)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": -1,
            "movement_type": "IN",
            "quantity": 10,
        })
        assert resp.status_code == 422

    async def test_zero_product_id(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """product_id=0 → 422 (gt=0 constraint)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 0,
            "movement_type": "IN",
            "quantity": 10,
        })
        assert resp.status_code == 422

    async def test_invalid_movement_type(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """movement_type='HACK' → 422 (enum validation)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "HACK",
            "quantity": 10,
        })
        assert resp.status_code == 422

    async def test_quantity_as_string(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """quantity="ten" → 422 (strict mode rechaza string como int)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "IN",
            "quantity": "ten",
        })
        assert resp.status_code == 422

    async def test_product_id_as_string(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """product_id="abc" → 422 (strict mode rechaza string como int)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": "abc",
            "movement_type": "IN",
            "quantity": 10,
        })
        assert resp.status_code == 422

    async def test_quantity_overflow(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """quantity=999999999999999999 → acepta o 422 (verificar comportamiento con INT_MAX)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "IN",
            "quantity": 999_999_999_999_999_999,
        })
        # Puede pasar Pydantic pero fallar en DB (integer overflow)
        assert resp.status_code in (201, 422, 500)

    async def test_reference_too_long(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """reference con 300 caracteres → 422 (max_length=255)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "IN",
            "quantity": 10,
            "reference": "A" * 300,
        })
        assert resp.status_code == 422

    async def test_transfer_without_required_metadata(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """TRANSFER sin origin/destination en metadata → 422."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "TRANSFER",
            "quantity": 10,
        })
        assert resp.status_code == 422

    async def test_adjustment_without_reason(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """ADJUSTMENT sin reason en metadata → 422."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "ADJUSTMENT",
            "quantity": 10,
        })
        assert resp.status_code == 422

    async def test_metadata_with_nested_objects(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """metadata con objetos anidados → 422 (dict[str,str] rechaza dict values)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "IN",
            "quantity": 10,
            "metadata": {"nested": {"key": "value"}},
        })
        assert resp.status_code == 422


class TestCreateProductInputValidation:
    """POST /v1/products — validación de CreateProductInput."""

    async def test_empty_sku(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """sku="" → 422 (regex validation)."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-prod"})
        cat_id = cat.json()["id"]

        resp = await api_client.post("/v1/products", json={
            "sku": "",
            "name": "Test",
            "unit_of_measure": "unit",
            "category_id": cat_id,
        })
        assert resp.status_code == 422

    async def test_sku_with_special_characters(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """sku="TEST; DROP TABLE products;--" → 422 (regex validation)."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-prod2"})
        cat_id = cat.json()["id"]

        resp = await api_client.post("/v1/products", json={
            "sku": "TEST; DROP TABLE products;--",
            "name": "Test",
            "unit_of_measure": "unit",
            "category_id": cat_id,
        })
        assert resp.status_code == 422

    async def test_nonexistent_category_id(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """category_id=99999 → error de FK (producto no se crea)."""
        resp = await api_client.post("/v1/products", json={
            "sku": "SEC-NO-CAT",
            "name": "No Category",
            "unit_of_measure": "unit",
            "category_id": 99999,
        })
        assert resp.status_code in (400, 409, 422, 500)

    async def test_negative_min_stock_threshold(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """min_stock_threshold=-5 → 422 (ge=0 constraint)."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-prod3"})
        cat_id = cat.json()["id"]

        resp = await api_client.post("/v1/products", json={
            "sku": "SEC-NEG-THRESH",
            "name": "Negative Threshold",
            "unit_of_measure": "unit",
            "category_id": cat_id,
            "min_stock_threshold": -5,
        })
        assert resp.status_code == 422


class TestCreateCategoryInputValidation:
    """POST /v1/categories — validación de CreateCategoryInput."""

    async def test_empty_name(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """name="" → 422."""
        resp = await api_client.post("/v1/categories", json={"name": ""})
        assert resp.status_code == 422

    async def test_name_with_only_spaces(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """name="   " → verificar comportamiento (puede aceptar o rechazar)."""
        resp = await api_client.post("/v1/categories", json={"name": "   "})
        # Depende de si hay strip validation en el DTO
        assert resp.status_code in (201, 422)

    async def test_missing_name_field(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Body sin campo name → 422."""
        resp = await api_client.post("/v1/categories", json={"description": "test"})
        assert resp.status_code == 422


class TestMalformedPayloads:
    """Payloads malformados que no son JSON válido."""

    async def test_invalid_json_body(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Body que no es JSON válido → 422."""
        resp = await api_client.post(
            "/v1/movements",
            content=b"{invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_empty_body(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Body completamente vacío → 422."""
        resp = await api_client.post(
            "/v1/movements",
            content=b"",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_wrong_content_type(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Content-Type: text/plain → 422 o acepta con warning."""
        resp = await api_client.post(
            "/v1/movements",
            content=b'{"product_id": 1, "movement_type": "IN", "quantity": 10}',
            headers={"Content-Type": "text/plain"},
        )
        # FastAPI puede rechazar o intentar parsear
        assert resp.status_code in (200, 201, 422)

    async def test_null_body(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Body = null → 422."""
        resp = await api_client.post(
            "/v1/movements",
            content=b"null",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_array_body(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Body = [] (array en vez de object) → 422."""
        resp = await api_client.post(
            "/v1/movements",
            content=b"[]",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422


class TestUnicodeEdgeCases:
    """Unicode y encoding edge cases que podrían causar problemas."""

    async def test_null_byte_in_reference(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Reference con byte nulo → rechazado o almacenado literalmente."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-unicode"})
        cat_id = cat.json()["id"]
        product = await api_client.post("/v1/products", json={
            "sku": "SEC-UNI-001",
            "name": "Unicode Test",
            "unit_of_measure": "unit",
            "category_id": cat_id,
        })
        product_id = product.json()["id"]

        resp = await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 10,
            "reference": "test\x00injection",
        })
        # PostgreSQL rechaza null bytes en text columns
        assert resp.status_code in (201, 422, 500)

    async def test_emoji_in_name(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Nombre de categoría con emojis → acepta (Unicode válido)."""
        resp = await api_client.post("/v1/categories", json={
            "name": "📦 Categoría Test 📦",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "📦 Categoría Test 📦"

    async def test_very_long_string_in_metadata(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Metadata value con string de 10000 caracteres → acepta o 422."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-long"})
        cat_id = cat.json()["id"]
        product = await api_client.post("/v1/products", json={
            "sku": "SEC-LONG-001",
            "name": "Long Metadata Test",
            "unit_of_measure": "unit",
            "category_id": cat_id,
        })
        product_id = product.json()["id"]

        resp = await api_client.post("/v1/movements", json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 10,
            "metadata": {"note": "A" * 10_000},
        })
        # JSONB no tiene límite de longitud por valor
        assert resp.status_code in (201, 422)
```

---

## Error Leakage Tests

### `tests/security/test_error_leakage.py`

```python
"""Tests de seguridad: Error Leakage.

Valida que las respuestas de error NO exponen información sensible:
1. Stack traces de Python
2. SQL queries o fragments
3. Nombres de tablas o columnas (más allá de lo esperado en ErrorResponse)
4. Rutas de archivos del servidor
5. Versiones de software interno
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx


LEAKAGE_PATTERNS = [
    "traceback",
    "stack trace",
    "file \"",
    "line ",
    ".py\"",  # Python file paths
    "asyncpg",
    "psycopg",
    "sqlalchemy",
    "internal server error",  # Generic 500 without detail
]

SQL_LEAKAGE_PATTERNS = [
    "select ",
    "insert ",
    "update ",
    "delete ",
    "drop ",
    "from movements",
    "from products",
    "where ",
    "syntax error",
    "unterminated string",
]


class TestNoErrorLeakage:
    """Las respuestas de error no deben exponer información interna."""

    @pytest.mark.parametrize("payload", [
        {"product_id": -1, "movement_type": "IN", "quantity": 10},
        {"product_id": 1, "movement_type": "HACK", "quantity": 10},
        {"product_id": 1, "movement_type": "IN", "quantity": -5},
    ])
    async def test_validation_errors_no_leakage(
        self, api_client: httpx.AsyncClient, payload: dict
    ) -> None:
        """Errores de validación 422 no exponen stack traces ni SQL."""
        resp = await api_client.post("/v1/movements", json=payload)
        body_str = str(resp.json()).lower()

        for pattern in LEAKAGE_PATTERNS:
            assert pattern.lower() not in body_str, f"Leakage detected: '{pattern}'"

        for pattern in SQL_LEAKAGE_PATTERNS:
            assert pattern.lower() not in body_str, f"SQL leakage: '{pattern}'"

    async def test_404_errors_no_leakage(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Errores 404 no exponen información interna."""
        resp = await api_client.get("/v1/products/99999")
        if resp.status_code == 404:
            body_str = str(resp.json()).lower()
            for pattern in LEAKAGE_PATTERNS:
                assert pattern.lower() not in body_str

    async def test_server_errors_no_stack_trace(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Errores 500 no exponen stack traces.

        Nota: Este test verifica el comportamiento en producción.
        En desarrollo, FastAPI puede incluir tracebacks.
        """
        # Intentar crear un movimiento con product_id que causa FK error
        resp = await api_client.post("/v1/movements", json={
            "product_id": 99999,
            "movement_type": "IN",
            "quantity": 10,
        })
        body_str = str(resp.json()).lower()
        # Verificar que no hay stack trace detallado
        assert "traceback" not in body_str


class TestImmutabilityEnforcement:
    """Los movimientos no deben poder modificarse ni eliminarse via API."""

    async def test_no_update_endpoint(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """PUT /v1/movements/1 → 405 Method Not Allowed."""
        resp = await api_client.put("/v1/movements/1", json={
            "quantity": 999,
        })
        assert resp.status_code == 405

    async def test_no_patch_endpoint(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """PATCH /v1/movements/1 → 405 Method Not Allowed."""
        resp = await api_client.patch("/v1/movements/1", json={
            "quantity": 999,
        })
        assert resp.status_code == 405

    async def test_no_delete_endpoint(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """DELETE /v1/movements/1 → 405 Method Not Allowed."""
        resp = await api_client.delete("/v1/movements/1")
        assert resp.status_code == 405
```

---

## Files

| File | Description | Action |
|------|-------------|--------|
| `tests/security/__init__.py` | Package marker | NEW |
| `tests/security/conftest.py` | Fixtures compartidos (reutiliza `db_pool`, `db_clean`, `api_client`) | NEW |
| `tests/security/test_sql_injection.py` | SQL injection tests (OWASP payloads) | NEW |
| `tests/security/test_input_validation.py` | Input validation boundary tests | NEW |
| `tests/security/test_error_leakage.py` | Error leakage + immutability enforcement | NEW |

---

## Acceptance Criteria

- [ ] `tests/security/` directory con 3 archivos de test + conftest + __init__
- [ ] SQL injection tests: path params, query params, body fields, repository-level
- [ ] SQL injection tests: payloads OWASP Testing Guide v4 (mínimo 7 path payloads, 13 string payloads)
- [ ] SQL injection tests: ningún payload causa SQL syntax error o data modification
- [ ] Input validation tests: tipos incorrectos, rangos, campos requeridos, campos extra, metadata anidada
- [ ] Input validation tests: payloads malformados (JSON inválido, body vacío, content-type incorrecto, null, array)
- [ ] Input validation tests: Unicode edge cases (null bytes, emojis, strings largos)
- [ ] Error leakage tests: ningún error expone stack trace, SQL, rutas de archivos, versiones internas
- [ ] Immutability enforcement: PUT/PATCH/DELETE en /v1/movements/ → 405
- [ ] 0 regresiones en tests existentes
- [ ] `make lint` pasa sin errores

---

## Testing Strategy

- **SQL injection tests:** Envían payloads OWASP a cada capa de entrada (path params, query params, body). Verifican que: (a) la API rechaza con 422, o (b) el payload se almacena literalmente sin ejecutarse
- **Repository-level injection tests:** Pasan strings directamente a métodos de repositorio que esperan `int`. Verifican que asyncpg lanza TypeError, no ejecuta SQL
- **Input validation tests:** Envían inputs fuera de rango, tipos incorrectos, campos extra, y payloads malformados. Verifican 422 con detalle del error
- **Error leakage tests:** Verifican que las respuestas de error no contienen patrones de información interna (stack traces, SQL, file paths)
- **Immutability tests:** Verifican que los endpoints HTTP de modificación/eliminación de movimientos no existen (405)

### Ejecución

```bash
# Todos los tests de seguridad
pytest tests/security/ -v

# Solo SQL injection
pytest tests/security/test_sql_injection.py -v

# Solo input validation
pytest tests/security/test_input_validation.py -v

# Solo error leakage
pytest tests/security/test_error_leakage.py -v
```

---

## Out of Scope

Las siguientes áreas de seguridad están **explícitamente excluidas** de F6:

| Área | Razón | Fase futura |
|------|-------|-------------|
| Authentication / Authorization | No existe sistema de usuarios en el sistema | F8+ |
| Rate Limiting | Requiere middleware adicional y configuración de infraestructura | F7+ |
| CORS Configuration | Configuración de deployment, no de aplicación | F7+ |
| Timing Attacks | Requiere infraestructura de medición estadística (miles de muestras) | Fuera de scope |
| SSRF / CSRF | Sistema es API-only (no hay formularios, no hay server-side requests) | N/A |
| Dependency Vulnerability Scanning | Requiere `pip-audit` o `safety` — se añade en CI/CD (Spec-72) | F7 |
| HTTPS/TLS | Configuración de infraestructura (reverse proxy) | F7+ |

---

## Resolved Questions

| # | Pregunta | Decisión | Rationale |
|---|----------|----------|-----------|
| F6-63-Q1 | ¿Scope de seguridad? | **SQL injection + input validation solo** | No hay auth en el sistema. Rate limiting y CORS son de F7+. Timing attacks requieren infraestructura fuera de scope |
| F6-63-Q2 | ¿Usar `sqlmap`? | **No** — tests manuales con pytest | `sqlmap` requiere servidor corriendo y es no-determinista. Los tests de pytest son deterministas, reproducibles, y se integran en CI |
| F6-63-Q3 | ¿Tests de timing attacks? | **No** | Requieren miles de muestras, análisis estadístico, y control del entorno de ejecución. Fuera de scope de F6 |
| F6-63-Q4 | ¿Verificar inmutabilidad de movimientos? | **Sí** — tests HTTP 405 | Los movimientos son Source of Truth inmutable. Verificar que no existen endpoints de modificación es una prueba de seguridad |
| F6-63-Q5 | ¿Error leakage como test de seguridad? | **Sí** — verificación de patrones en respuestas de error | Exponer stack traces o SQL en errores es una vulnerabilidad de información que facilita ataques |
