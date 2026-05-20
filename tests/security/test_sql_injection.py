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
    import asyncpg
    import httpx


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
        resp = await api_client.get(
            f"/v1/stock/{payload}/at-date?date=2025-01-01T00:00:00Z"
        )
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
        product = await api_client.post(
            "/v1/products",
            json={
                "sku": "SEC-REF-001",
                "name": "Security Test Product",
                "unit_of_measure": "unit",
                "category_id": cat_id,
            },
        )
        product_id = product.json()["id"]

        resp = await api_client.post(
            "/v1/movements",
            json={
                "product_id": product_id,
                "movement_type": "IN",
                "quantity": 10,
                "reference": payload,
            },
        )
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

        resp = await api_client.post(
            "/v1/products",
            json={
                "sku": payload,
                "name": "Security Test",
                "unit_of_measure": "unit",
                "category_id": cat_id,
            },
        )
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
        """MovementRepository.get_by_id() con string → error de tipo, no SQL."""
        from src.infrastructure.repositories.movement_repository import (
            PostgresMovementRepository,
        )

        repo = PostgresMovementRepository(db_pool)
        # Si se intenta pasar un string como product_id, asyncpg lanzaría
        # TypeError o ProgrammingError (no SQL injection)
        with pytest.raises((TypeError, Exception)):
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
        """Un payload de SQL injection se almacena como string literal."""
        # Crear categoría y producto para el test
        cat_id = await db_pool.fetchval(
            "INSERT INTO categories (name) VALUES ($1) RETURNING id",
            "sec-literal-test",
        )
        product_id = await db_pool.fetchval(
            "INSERT INTO products (sku, name, unit_of_measure, category_id) "
            "VALUES ($1, $2, $3, $4) RETURNING id",
            "SEC-LIT-001",
            "Security Literal",
            "unit",
            cat_id,
        )

        # Insertar un movimiento con reference que contiene SQL
        injection = "'; DROP TABLE movements;--"
        movement_id = await db_pool.fetchval(
            "INSERT INTO movements (product_id, movement_type, quantity, "
            "metadata, reference, created_at) "
            "VALUES ($1, $2, $3, $4, $5, now()) RETURNING id",
            product_id,
            "IN",
            10,
            "{}",
            injection,
        )

        # Verificar: el movimiento se creó con el reference literal
        row = await db_pool.fetchrow(
            "SELECT reference FROM movements WHERE id = $1", movement_id
        )
        assert row["reference"] == injection

        # Verificar: la tabla movements sigue existiendo (no se ejecutó el DROP)
        exists = await db_pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'movements')"
        )
        assert exists is True
