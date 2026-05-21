# SPEC-63: Security Tests — SQL Injection + Input Validation

**Phase:** F6 — Comprehensive Testing
**Dependencies:** Spec-42 (FastAPI Routes) ✅ Completed, Spec-52 (Logging & Errors) ✅ Completed
**Priority:** Medium
**Status:** Approved

---

## Objective

Implement the security test suite that validates the two critical areas of the system: (1) **SQL Injection** — verify that repositories and endpoints are immune to SQL injection payloads; (2) **Input Validation** — verify that Pydantic DTOs reject malicious, out-of-range, or malformed inputs. The scope is limited to these two areas (does not include authentication, authorization, or timing attacks).

**Design principles:**
- **Security tests as regression suite** — they are not one-time audits; they run on every CI run
- **Zero new production dependencies** — tests use existing `httpx.AsyncClient`
- **Real OWASP payloads** — do not invent payloads; use those cataloged in OWASP Testing Guide v4
- **Explicit scope** — only SQL injection + input validation. Auth, rate limiting, and CORS are out of F6
- **Zero regressions** — all existing tests must continue passing

---

## Design Decisions

| Decision | Rationale |
|----------|----------|
| Scope: SQL injection + input validation only | Auth/authorization do not exist in the system (no users). Rate limiting and CORS are for F7+. Timing attacks require measurement infrastructure out of scope |
| Payloads from OWASP Testing Guide v4 | Industry standard. Not inventing our own payloads reduces false positives |
| Tests against API (httpx) + tests against repositories (asyncpg) | Double validation: the API is the first line of defense (Pydantic), repositories are the last (parameterized queries) |
| Do not add `sqlmap` or external tools | `sqlmap` requires a running server and is non-deterministic. pytest tests are deterministic, reproducible, and integrate into CI |
| Separate `tests/security/` directory | Clear separation of concerns. Security tests are not mixed with unit/integration/e2e |
| Error leakage tests in security (not in integration) | Verifying that errors do not expose stack traces or SQL internals is inherently a security concern |

---

## SQL Injection Tests

### Strategy

Repositories use **parameterized queries** (`$1`, `$2`, `$3`) with asyncpg. This pattern is inherently secure against SQL injection because parameters are sent outside the query text. Tests verify that:

1. **SQL injection payloads in path params** → FastAPI type coercion (int) rejects before reaching SQL
2. **SQL injection payloads in query params** → Pydantic validation rejects before reaching SQL
3. **SQL injection payloads in body fields** → Pydantic `strict=True` rejects unexpected types
4. **SQL injection payloads in repositories** → asyncpg parameterized queries treat the payload as a literal value, not as SQL

### `tests/security/test_sql_injection.py`

```python
"""Security tests: SQL Injection.

Validates that the system is immune to SQL injection payloads
cataloged in OWASP Testing Guide v4. Tests cover:
1. Path parameters (product_id, movement_id)
2. Query parameters (date, limit, offset)
3. Body fields (SKU, reference, metadata values)
4. Repository-level parameterized queries

Defense operates in three layers:
- Layer 1: FastAPI type coercion (int for path params)
- Layer 2: Pydantic strict validation (types, ranges, regex)
- Layer 3: asyncpg parameterized queries ($1, $2, $3)
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
    """SQL injection in path parameters must be rejected by FastAPI."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_PATH_PARAMS)
    async def test_stock_current_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """GET /v1/stock/{payload}/current → 422 (FastAPI rejects non-int)."""
        resp = await api_client.get(f"/v1/stock/{payload}/current")
        assert resp.status_code in (404, 422)
        # Verify no SQL error in response
        body = resp.json()
        assert "syntax error" not in str(body).lower()
        assert "sql" not in str(body).lower()

    @pytest.mark.parametrize("payload", SQL_INJECTION_PATH_PARAMS)
    async def test_stock_at_date_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """GET /v1/stock/{payload}/at-date → 422 (FastAPI rejects non-int)."""
        resp = await api_client.get(f"/v1/stock/{payload}/at-date?date=2025-01-01T00:00:00Z")
        assert resp.status_code in (404, 422)
        body = resp.json()
        assert "syntax error" not in str(body).lower()

    @pytest.mark.parametrize("payload", SQL_INJECTION_PATH_PARAMS)
    async def test_movement_get_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """GET /v1/movements/{payload} → 422 (FastAPI rejects non-int)."""
        resp = await api_client.get(f"/v1/movements/{payload}")
        assert resp.status_code in (404, 422)
        body = resp.json()
        assert "syntax error" not in str(body).lower()

    @pytest.mark.parametrize("payload", SQL_INJECTION_PATH_PARAMS)
    async def test_product_get_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """GET /v1/products/{payload} → 422 (FastAPI rejects non-int)."""
        resp = await api_client.get(f"/v1/products/{payload}")
        assert resp.status_code in (404, 422)


class TestSQLInjectionQueryParams:
    """SQL injection in query parameters must be rejected by Pydantic/FastAPI."""

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
    """SQL injection in body fields must be rejected by Pydantic strict mode."""

    @pytest.mark.parametrize("payload", SQL_INJECTION_STRING_FIELDS)
    async def test_create_movement_reference_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """POST /v1/movements with reference={payload} → does not cause SQL error."""
        # First create category and product
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
        # The movement is created (reference is a valid string for Pydantic)
        # but the payload must NOT execute as SQL
        assert resp.status_code in (201, 422)
        if resp.status_code == 201:
            body = resp.json()
            # Verify reference was stored literally
            assert body["reference"] == payload
            # Verify no SQL error
            assert "syntax error" not in str(body).lower()
            assert "sql" not in str(body).lower()

    @pytest.mark.parametrize("payload", SQL_INJECTION_STRING_FIELDS)
    async def test_create_product_sku_injection(
        self, api_client: httpx.AsyncClient, payload: str
    ) -> None:
        """POST /v1/products with sku={payload} → 422 or literal storage."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-sku"})
        cat_id = cat.json()["id"]

        resp = await api_client.post("/v1/products", json={
            "sku": payload,
            "name": "Security Test",
            "unit_of_measure": "unit",
            "category_id": cat_id,
        })
        # SKU has regex validation — payloads with special characters → 422
        # If it passes, it must be stored literally (not executed as SQL)
        assert resp.status_code in (201, 409, 422)
        if resp.status_code == 201:
            body = resp.json()
            assert body["sku"] == payload
            assert "sql" not in str(body).lower()


class TestSQLInjectionRepositoryLevel:
    """SQL injection at repository level (asyncpg parameterized queries).

    These tests validate the lowest defense layer: asyncpg parameterized
    queries. Even if a payload passed Pydantic and FastAPI, asyncpg
    would treat it as a literal value, not as executable SQL.
    """

    async def test_movement_repo_injection_in_product_id(
        self, db_pool: asyncpg.Pool
    ) -> None:
        """MovementRepository.create() with string in product_id → type error, not SQL."""
        from src.infrastructure.repositories.movement_repository import (
            PostgresMovementRepository,
        )

        repo = PostgresMovementRepository(db_pool)
        # If a string is passed as product_id, asyncpg would raise
        # TypeError or ProgrammingError (not SQL injection)
        with pytest.raises((TypeError, Exception)):
            # This fails because product_id is int in the method signature
            await repo.get_by_id("1 OR 1=1")  # type: ignore[arg-type]

    async def test_stock_repo_injection_in_product_id(
        self, db_pool: asyncpg.Pool
    ) -> None:
        """StockQueryRepository with string in product_id → type error, not SQL."""
        from src.infrastructure.repositories.stock_query_repository import (
            PostgresStockQueryRepository,
        )

        repo = PostgresStockQueryRepository(db_pool)
        with pytest.raises((TypeError, Exception)):
            await repo.get_current_stock("1; DROP TABLE movements;--")  # type: ignore[arg-type]

    async def test_parameterized_query_treats_payload_as_literal(
        self, db_pool: asyncpg.Pool
    ) -> None:
        """A SQL injection payload is stored as a string literal, not executed."""
        # Create category and product for the test
        cat_id = await db_pool.fetchval(
            "INSERT INTO categories (name) VALUES ($1) RETURNING id",
            "sec-literal-test",
        )
        product_id = await db_pool.fetchval(
            "INSERT INTO products (sku, name, unit_of_measure, category_id) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            "SEC-LIT-001", "Security Literal", "unit", cat_id,
        )

        # Insert a movement with reference containing SQL
        injection = "'; DROP TABLE movements;--"
        movement_id = await db_pool.fetchval(
            "INSERT INTO movements (product_id, movement_type, quantity, metadata, reference, created_at) "
            "VALUES ($1, $2, $3, $4, $5, now()) RETURNING id",
            product_id, "IN", 10, "{}", injection,
        )

        # Verify: the movement was created with the literal reference
        row = await db_pool.fetchrow(
            "SELECT reference FROM movements WHERE id = $1", movement_id
        )
        assert row["reference"] == injection

        # Verify: the movements table still exists (DROP was not executed)
        exists = await db_pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'movements')"
        )
        assert exists is True
```

---

## Input Validation Tests

### Strategy

Pydantic DTOs with `strict=True` and `Field` constraints are the first line of defense. Tests verify that:

1. **Incorrect types** → `strict=True` rejects int as string, bool as int, etc.
2. **Out-of-range fields** → `gt=0`, `le=1000`, `max_length=255` reject invalid values
3. **Missing required fields** → 422 with missing field detail
4. **Unknown extra fields** → `strict=True` rejects them
5. **Malformed payloads** → Invalid JSON, empty body, incorrect content-type
6. **Metadata injection** → `dict[str, Any]` accepts any JSON value (not restricted to strings).
   Malicious content validation is delegated to the repository layer (parameterized queries).
7. **Unicode/encoding edge cases** → NULL characters, surrogates, overlong encoding

### `tests/security/test_input_validation.py`

```python
"""Security tests: Input Validation.

Validates that Pydantic DTOs with strict=True reject malicious,
out-of-range, or malformed inputs. Tests cover:
1. Incorrect types (strict mode)
2. Out-of-range values (Field constraints)
3. Missing required fields
4. Unknown extra fields
5. Malformed payloads (invalid JSON, empty body)
6. Metadata with malicious content
7. Unicode/encoding edge cases
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx


class TestCreateMovementInputValidation:
    """POST /v1/movements — CreateMovementInput validation."""

    async def test_missing_required_fields(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Empty body → 422 with missing field details."""
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
        """Unknown extra fields → 422 (strict mode)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "IN",
            "quantity": 10,
            "extra_malicious_field": "hack",
        })
        # strict=True in Pydantic rejects extra fields
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
        """quantity="ten" → 422 (strict mode rejects string as int)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "IN",
            "quantity": "ten",
        })
        assert resp.status_code == 422

    async def test_product_id_as_string(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """product_id="abc" → 422 (strict mode rejects string as int)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": "abc",
            "movement_type": "IN",
            "quantity": 10,
        })
        assert resp.status_code == 422

    async def test_quantity_overflow(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """quantity=999999999999999999 → accepts or 422 (verify behavior with INT_MAX)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "IN",
            "quantity": 999_999_999_999_999_999,
        })
        # May pass Pydantic but fail in DB (integer overflow)
        assert resp.status_code in (201, 422, 500)

    async def test_reference_too_long(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """reference with 300 characters → 422 (max_length=255)."""
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
        """TRANSFER without origin/destination in metadata → 422."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "TRANSFER",
            "quantity": 10,
        })
        assert resp.status_code == 422

    async def test_adjustment_without_reason(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """ADJUSTMENT without reason in metadata → 422."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "ADJUSTMENT",
            "quantity": 10,
        })
        assert resp.status_code == 422

    async def test_metadata_with_nested_objects(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """metadata with nested objects → accepts (dict[str, Any] allows any JSON value)."""
        resp = await api_client.post("/v1/movements", json={
            "product_id": 1,
            "movement_type": "IN",
            "quantity": 10,
            "metadata": {"nested": {"key": "value"}},
        })
        # dict[str, Any] accepts nested objects, ints, bools, etc.
        assert resp.status_code == 201
        body = resp.json()
        assert body["metadata"]["nested"] == {"key": "value"}


class TestCreateProductInputValidation:
    """POST /v1/products — CreateProductInput validation."""

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
        """category_id=99999 → FK error (product not created)."""
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
    """POST /v1/categories — CreateCategoryInput validation."""

    async def test_empty_name(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """name="" → 422."""
        resp = await api_client.post("/v1/categories", json={"name": ""})
        assert resp.status_code == 422

    async def test_name_with_only_spaces(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """name="   " → verify behavior (may accept or reject)."""
        resp = await api_client.post("/v1/categories", json={"name": "   "})
        # Depends on whether there is strip validation in the DTO
        assert resp.status_code in (201, 422)

    async def test_missing_name_field(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Body without name field → 422."""
        resp = await api_client.post("/v1/categories", json={"description": "test"})
        assert resp.status_code == 422


class TestMalformedPayloads:
    """Malformed payloads that are not valid JSON."""

    async def test_invalid_json_body(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Body that is not valid JSON → 422."""
        resp = await api_client.post(
            "/v1/movements",
            content=b"{invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_empty_body(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Completely empty body → 422."""
        resp = await api_client.post(
            "/v1/movements",
            content=b"",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_wrong_content_type(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Content-Type: text/plain → 422 or accepts with warning."""
        resp = await api_client.post(
            "/v1/movements",
            content=b'{"product_id": 1, "movement_type": "IN", "quantity": 10}',
            headers={"Content-Type": "text/plain"},
        )
        # FastAPI may reject or attempt to parse
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
        """Body = [] (array instead of object) → 422."""
        resp = await api_client.post(
            "/v1/movements",
            content=b"[]",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422


class TestUnicodeEdgeCases:
    """Unicode and encoding edge cases that could cause issues."""

    async def test_null_byte_in_reference(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Reference with null byte → rejected or stored literally."""
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
        # PostgreSQL rejects null bytes in text columns
        assert resp.status_code in (201, 422, 500)

    async def test_emoji_in_name(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Category name with emojis → accepts (valid Unicode)."""
        resp = await api_client.post("/v1/categories", json={
            "name": "📦 Categoría Test 📦",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "📦 Categoría Test 📦"

    async def test_very_long_string_in_metadata(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Metadata value with 10000 character string → accepts or 422."""
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
        # JSONB has no length limit per value
        assert resp.status_code in (201, 422)
```

---

## Error Leakage Tests

### `tests/security/test_error_leakage.py`

```python
"""Security tests: Error Leakage.

Validates that error responses do NOT expose sensitive information:
1. Python stack traces
2. SQL queries or fragments
3. Table or column names (beyond what is expected in ErrorResponse)
4. Server file paths
5. Internal software versions
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
    """Error responses must not expose internal information."""

    @pytest.mark.parametrize("payload", [
        {"product_id": -1, "movement_type": "IN", "quantity": 10},
        {"product_id": 1, "movement_type": "HACK", "quantity": 10},
        {"product_id": 1, "movement_type": "IN", "quantity": -5},
    ])
    async def test_validation_errors_no_leakage(
        self, api_client: httpx.AsyncClient, payload: dict
    ) -> None:
        """422 validation errors do not expose stack traces or SQL."""
        resp = await api_client.post("/v1/movements", json=payload)
        body_str = str(resp.json()).lower()

        for pattern in LEAKAGE_PATTERNS:
            assert pattern.lower() not in body_str, f"Leakage detected: '{pattern}'"

        for pattern in SQL_LEAKAGE_PATTERNS:
            assert pattern.lower() not in body_str, f"SQL leakage: '{pattern}'"

    async def test_404_errors_no_leakage(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """404 errors do not expose internal information."""
        resp = await api_client.get("/v1/products/99999")
        if resp.status_code == 404:
            body_str = str(resp.json()).lower()
            for pattern in LEAKAGE_PATTERNS:
                assert pattern.lower() not in body_str

    async def test_server_errors_no_stack_trace(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """500 errors do not expose stack traces.

        Note: This test verifies production behavior.
        In development, FastAPI may include tracebacks.
        """
        # Attempt to create a movement with product_id that causes FK error
        resp = await api_client.post("/v1/movements", json={
            "product_id": 99999,
            "movement_type": "IN",
            "quantity": 10,
        })
        body_str = str(resp.json()).lower()
        # Verify no detailed stack trace
        assert "traceback" not in body_str


class TestImmutabilityEnforcement:
    """Movements must not be modifiable or deletable via API."""

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
| `tests/security/conftest.py` | Shared fixtures (reuses `db_pool`, `db_clean`, `api_client`) | NEW |
| `tests/security/test_sql_injection.py` | SQL injection tests (OWASP payloads) | NEW |
| `tests/security/test_input_validation.py` | Input validation boundary tests | NEW |
| `tests/security/test_error_leakage.py` | Error leakage + immutability enforcement | NEW |

---

## Acceptance Criteria

- [ ] `tests/security/` directory with 3 test files + conftest + __init__
- [ ] SQL injection tests: path params, query params, body fields, repository-level
- [ ] SQL injection tests: OWASP Testing Guide v4 payloads (minimum 7 path payloads, 13 string payloads)
- [ ] SQL injection tests: no payload causes SQL syntax error or data modification
- [ ] Input validation tests: incorrect types, ranges, required fields, extra fields, nested metadata
- [ ] Input validation tests: malformed payloads (invalid JSON, empty body, incorrect content-type, null, array)
- [ ] Input validation tests: Unicode edge cases (null bytes, emojis, long strings)
- [ ] Error leakage tests: no error exposes stack trace, SQL, file paths, internal versions
- [ ] Immutability enforcement: PUT/PATCH/DELETE on /v1/movements/ → 405
- [ ] 0 regressions in existing tests
- [ ] `make lint` passes without errors

---

## Testing Strategy

- **SQL injection tests:** Send OWASP payloads to each input layer (path params, query params, body). Verify that: (a) the API rejects with 422, or (b) the payload is stored literally without execution
- **Repository-level injection tests:** Pass strings directly to repository methods that expect `int`. Verify that asyncpg raises TypeError, does not execute SQL
- **Input validation tests:** Send out-of-range inputs, incorrect types, extra fields, and malformed payloads. Verify 422 with error detail
- **Error leakage tests:** Verify that error responses do not contain internal information patterns (stack traces, SQL, file paths)
- **Immutability tests:** Verify that HTTP endpoints for movement modification/deletion do not exist (405)

### Execution

```bash
# All security tests
pytest tests/security/ -v

# SQL injection only
pytest tests/security/test_sql_injection.py -v

# Input validation only
pytest tests/security/test_input_validation.py -v

# Error leakage only
pytest tests/security/test_error_leakage.py -v
```

---

## Out of Scope

The following security areas are **explicitly excluded** from F6:

| Area | Reason | Future Phase |
|------|--------|--------------|
| Authentication / Authorization | No user system exists in the system | F8+ |
| Rate Limiting | Requires additional middleware and infrastructure configuration | F7+ |
| CORS Configuration | Deployment configuration, not application | F7+ |
| Timing Attacks | Requires statistical measurement infrastructure (thousands of samples) | Out of scope |
| SSRF / CSRF | System is API-only (no forms, no server-side requests) | N/A |
| Dependency Vulnerability Scanning | Requires `pip-audit` or `safety` — added in CI/CD (Spec-72) | F7 |
| HTTPS/TLS | Infrastructure configuration (reverse proxy) | F7+ |

---

## Resolved Questions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| F6-63-Q1 | Security scope? | **SQL injection + input validation only** | No auth in the system. Rate limiting and CORS are for F7+. Timing attacks require infrastructure out of scope |
| F6-63-Q2 | Use `sqlmap`? | **No** — manual tests with pytest | `sqlmap` requires a running server and is non-deterministic. pytest tests are deterministic, reproducible, and integrate into CI |
| F6-63-Q3 | Timing attack tests? | **No** | Require thousands of samples, statistical analysis, and execution environment control. Out of F6 scope |
| F6-63-Q4 | Verify movement immutability? | **Yes** — HTTP 405 tests | Movements are immutable Source of Truth. Verifying that modification endpoints do not exist is a security test |
| F6-63-Q5 | Error leakage as security test? | **Yes** — pattern verification in error responses | Exposing stack traces or SQL in errors is an information vulnerability that facilitates attacks |
