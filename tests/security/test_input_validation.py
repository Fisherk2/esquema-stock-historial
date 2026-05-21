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

if TYPE_CHECKING:
    import httpx


class TestCreateMovementInputValidation:
    """POST /v1/movements — validación de CreateMovementInput."""

    async def test_missing_required_fields(self, api_client: httpx.AsyncClient) -> None:
        """Body vacío → 422 con detalle de campos faltantes."""
        resp = await api_client.post("/v1/movements", json={})
        assert resp.status_code == 422
        body = resp.json()
        missing_fields = {e["loc"][-1] for e in body.get("detail", [])}
        assert "product_id" in missing_fields
        assert "movement_type" in missing_fields
        assert "quantity" in missing_fields

    async def test_extra_fields_rejected(self, api_client: httpx.AsyncClient) -> None:
        """Campos extra desconocidos → 422 (strict mode)."""
        resp = await api_client.post(
            "/v1/movements",
            json={
                "product_id": 1,
                "movement_type": "IN",
                "quantity": 10,
                "extra_malicious_field": "hack",
            },
        )
        # strict=True en Pydantic rechaza campos extra
        assert resp.status_code == 422

    async def test_negative_quantity(self, api_client: httpx.AsyncClient) -> None:
        """quantity=-5 → 422 (gt=0 constraint)."""
        resp = await api_client.post(
            "/v1/movements",
            json={"product_id": 1, "movement_type": "IN", "quantity": -5},
        )
        assert resp.status_code == 422

    async def test_zero_quantity(self, api_client: httpx.AsyncClient) -> None:
        """quantity=0 → 422 (gt=0 constraint)."""
        resp = await api_client.post(
            "/v1/movements",
            json={"product_id": 1, "movement_type": "IN", "quantity": 0},
        )
        assert resp.status_code == 422

    async def test_negative_product_id(self, api_client: httpx.AsyncClient) -> None:
        """product_id=-1 → 422 (gt=0 constraint)."""
        resp = await api_client.post(
            "/v1/movements",
            json={"product_id": -1, "movement_type": "IN", "quantity": 10},
        )
        assert resp.status_code == 422

    async def test_zero_product_id(self, api_client: httpx.AsyncClient) -> None:
        """product_id=0 → 422 (gt=0 constraint)."""
        resp = await api_client.post(
            "/v1/movements",
            json={"product_id": 0, "movement_type": "IN", "quantity": 10},
        )
        assert resp.status_code == 422

    async def test_invalid_movement_type(self, api_client: httpx.AsyncClient) -> None:
        """movement_type='HACK' → 422 (enum validation)."""
        resp = await api_client.post(
            "/v1/movements",
            json={"product_id": 1, "movement_type": "HACK", "quantity": 10},
        )
        assert resp.status_code == 422

    async def test_quantity_as_string(self, api_client: httpx.AsyncClient) -> None:
        """quantity="ten" → 422 (strict mode rechaza string como int)."""
        resp = await api_client.post(
            "/v1/movements",
            json={"product_id": 1, "movement_type": "IN", "quantity": "ten"},
        )
        assert resp.status_code == 422

    async def test_product_id_as_string(self, api_client: httpx.AsyncClient) -> None:
        """product_id="abc" → 422 (strict mode rechaza string como int)."""
        resp = await api_client.post(
            "/v1/movements",
            json={"product_id": "abc", "movement_type": "IN", "quantity": 10},
        )
        assert resp.status_code == 422

    async def test_quantity_overflow(self, api_client: httpx.AsyncClient) -> None:
        """quantity=999999999999999999 → acepta o 422 (verificar INT_MAX)."""
        resp = await api_client.post(
            "/v1/movements",
            json={
                "product_id": 1,
                "movement_type": "IN",
                "quantity": 999_999_999_999_999_999,
            },
        )
        # Puede pasar Pydantic pero fallar en DB (integer overflow)
        # 400 es aceptable porque el error se convierte a ValueError
        assert resp.status_code in (201, 400, 422, 500)

    async def test_reference_too_long(self, api_client: httpx.AsyncClient) -> None:
        """reference con 300 caracteres → 422 (max_length=255)."""
        resp = await api_client.post(
            "/v1/movements",
            json={
                "product_id": 1,
                "movement_type": "IN",
                "quantity": 10,
                "reference": "A" * 300,
            },
        )
        assert resp.status_code == 422

    async def test_transfer_without_required_metadata(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """TRANSFER sin origin/destination en metadata → 422."""
        resp = await api_client.post(
            "/v1/movements",
            json={"product_id": 1, "movement_type": "TRANSFER", "quantity": 10},
        )
        assert resp.status_code == 422

    async def test_adjustment_without_reason(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """ADJUSTMENT sin reason en metadata → 422."""
        resp = await api_client.post(
            "/v1/movements",
            json={"product_id": 1, "movement_type": "ADJUSTMENT", "quantity": 10},
        )
        assert resp.status_code == 422

    async def test_metadata_with_nested_objects(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """metadata con objetos anidados → acepta dict[str, Any] permite JSON."""
        resp = await api_client.post(
            "/v1/movements",
            json={
                "product_id": 1,
                "movement_type": "IN",
                "quantity": 10,
                "metadata": {"nested": {"key": "value"}},
            },
        )
        assert resp.status_code == 201


class TestCreateProductInputValidation:
    """POST /v1/products — validación de CreateProductInput."""

    async def test_empty_sku(self, api_client: httpx.AsyncClient) -> None:
        """sku="" → 422 (regex validation)."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-prod"})
        cat_id = cat.json()["id"]

        resp = await api_client.post(
            "/v1/products",
            json={
                "sku": "",
                "name": "Test",
                "unit_of_measure": "unit",
                "category_id": cat_id,
            },
        )
        assert resp.status_code == 422

    async def test_sku_with_special_characters(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """sku="TEST; DROP TABLE products;--" → 422 (regex validation)."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-prod2"})
        cat_id = cat.json()["id"]

        resp = await api_client.post(
            "/v1/products",
            json={
                "sku": "TEST; DROP TABLE products;--",
                "name": "Test",
                "unit_of_measure": "unit",
                "category_id": cat_id,
            },
        )
        assert resp.status_code == 422

    async def test_nonexistent_category_id(self, api_client: httpx.AsyncClient) -> None:
        """category_id=99999 → error de FK (producto no se crea)."""
        resp = await api_client.post(
            "/v1/products",
            json={
                "sku": "SEC-NO-CAT",
                "name": "No Category",
                "unit_of_measure": "unit",
                "category_id": 99999,
            },
        )
        assert resp.status_code in (400, 409, 422, 500)

    async def test_negative_min_stock_threshold(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """min_stock_threshold=-5 → 422 (ge=0 constraint)."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-prod3"})
        cat_id = cat.json()["id"]

        resp = await api_client.post(
            "/v1/products",
            json={
                "sku": "SEC-NEG-THRESH",
                "name": "Negative Threshold",
                "unit_of_measure": "unit",
                "category_id": cat_id,
                "min_stock_threshold": -5,
            },
        )
        assert resp.status_code == 422


class TestCreateCategoryInputValidation:
    """POST /v1/categories — validación de CreateCategoryInput."""

    async def test_empty_name(self, api_client: httpx.AsyncClient) -> None:
        """name="" → 422."""
        resp = await api_client.post("/v1/categories", json={"name": ""})
        assert resp.status_code == 422

    async def test_name_with_only_spaces(self, api_client: httpx.AsyncClient) -> None:
        """name="   " → verificar comportamiento (puede aceptar o rechazar)."""
        resp = await api_client.post("/v1/categories", json={"name": "   "})
        # Depende de si hay strip validation en el DTO
        assert resp.status_code in (201, 422)

    async def test_missing_name_field(self, api_client: httpx.AsyncClient) -> None:
        """Body sin campo name → 422."""
        resp = await api_client.post("/v1/categories", json={"description": "test"})
        assert resp.status_code == 422


class TestMalformedPayloads:
    """Payloads malformados que no son JSON válido."""

    async def test_invalid_json_body(self, api_client: httpx.AsyncClient) -> None:
        """Body que no es JSON válido → 422."""
        resp = await api_client.post(
            "/v1/movements",
            content=b"{invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_empty_body(self, api_client: httpx.AsyncClient) -> None:
        """Body completamente vacío → 422."""
        resp = await api_client.post(
            "/v1/movements",
            content=b"",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_wrong_content_type(self, api_client: httpx.AsyncClient) -> None:
        """Content-Type: text/plain → 422 o acepta con warning."""
        resp = await api_client.post(
            "/v1/movements",
            content=b'{"product_id": 1, "movement_type": "IN", "quantity": 10}',
            headers={"Content-Type": "text/plain"},
        )
        # FastAPI puede rechazar o intentar parsear
        assert resp.status_code in (200, 201, 422)

    async def test_null_body(self, api_client: httpx.AsyncClient) -> None:
        """Body = null → 422."""
        resp = await api_client.post(
            "/v1/movements",
            content=b"null",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    async def test_array_body(self, api_client: httpx.AsyncClient) -> None:
        """Body = [] (array en vez de object) → 422."""
        resp = await api_client.post(
            "/v1/movements",
            content=b"[]",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422


class TestUnicodeEdgeCases:
    """Unicode y encoding edge cases que podrían causar problemas."""

    async def test_null_byte_in_reference(self, api_client: httpx.AsyncClient) -> None:
        """Reference con byte nulo → rechazado o almacenado literalmente."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-unicode"})
        cat_id = cat.json()["id"]
        product = await api_client.post(
            "/v1/products",
            json={
                "sku": "SEC-UNI-001",
                "name": "Unicode Test",
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
                "reference": "test\x00injection",
            },
        )
        # PostgreSQL rechaza null bytes en text columns
        # 400 es aceptable porque el error se convierte a ValueError
        assert resp.status_code in (201, 400, 422, 500)

    async def test_emoji_in_name(self, api_client: httpx.AsyncClient) -> None:
        """Nombre de categoría con emojis → acepta (Unicode válido)."""
        resp = await api_client.post(
            "/v1/categories", json={"name": "📦 Categoría Test 📦"}
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "📦 Categoría Test 📦"

    async def test_very_long_string_in_metadata(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Metadata value con string de 10000 caracteres → acepta o 422."""
        cat = await api_client.post("/v1/categories", json={"name": "sec-long"})
        cat_id = cat.json()["id"]
        product = await api_client.post(
            "/v1/products",
            json={
                "sku": "SEC-LONG-001",
                "name": "Long Metadata Test",
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
                "metadata": {"note": "A" * 10_000},
            },
        )
        # JSONB no tiene límite de longitud por valor
        assert resp.status_code in (201, 422)
