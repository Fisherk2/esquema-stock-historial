"""Tests E2E de validacion de contratos OpenAPI.

Verifica que las respuestas JSON de los endpoints coinciden con
los esquemas Pydantic definidos en src/application/dtos/.
Usa model_validate() para validar cada respuesta contra su DTO.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx


class TestOpenAPIContracts:
    """Las respuestas de la API deben validar contra sus DTOs Pydantic."""

    async def test_movement_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """POST /v1/movements retorna MovementOutput valido."""
        from src.application.dtos.movement_dtos import MovementOutput

        # Setup
        cat = await api_client.post("/v1/categories", json={"name": "E2E-Contract"})
        product = await api_client.post(
            "/v1/products",
            json={
                "sku": "E2E-CONTRACT-001",
                "name": "Contract Test",
                "unit_of_measure": "unit",
                "category_id": cat.json()["id"],
            },
        )
        product_id = product.json()["id"]

        resp = await api_client.post(
            "/v1/movements",
            json={
                "product_id": product_id,
                "movement_type": "IN",
                "quantity": 25,
                "metadata": {"supplier": "test"},
            },
        )
        assert resp.status_code == 201
        # Validar contra Pydantic model
        movement = MovementOutput.model_validate(resp.json())
        assert movement.id > 0
        assert movement.product_id == product_id
        assert movement.movement_type == "IN"
        assert movement.quantity == 25

    async def test_current_stock_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """GET /v1/stock/{id}/current retorna CurrentStockOutput valido."""
        from src.application.dtos.stock_dtos import CurrentStockOutput

        # Setup
        cat = await api_client.post("/v1/categories", json={"name": "E2E-Stock"})
        product = await api_client.post(
            "/v1/products",
            json={
                "sku": "E2E-STOCK-CONTRACT",
                "name": "Stock Contract",
                "unit_of_measure": "unit",
                "category_id": cat.json()["id"],
            },
        )
        product_id = product.json()["id"]

        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.status_code == 200
        stock = CurrentStockOutput.model_validate(resp.json())
        assert stock.product_id == product_id

    async def test_product_list_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """GET /v1/products retorna ProductListOutput valido."""
        from src.application.dtos.product_dtos import ProductListOutput

        resp = await api_client.get("/v1/products")
        assert resp.status_code == 200
        product_list = ProductListOutput.model_validate(resp.json())
        assert isinstance(product_list.items, list)
        assert product_list.total >= 0

    async def test_category_response_contract(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """POST /v1/categories retorna CategoryOutput valido."""
        from src.application.dtos.category_dtos import CategoryOutput

        resp = await api_client.post(
            "/v1/categories", json={"name": "E2E-Contract Category"}
        )
        assert resp.status_code == 201
        category = CategoryOutput.model_validate(resp.json())
        assert category.id > 0
        assert category.name == "E2E-Contract Category"
