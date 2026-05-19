"""Integration tests for products API endpoints.

Valida los endpoints ``POST /v1/products``, ``GET /v1/products``, y
``GET /v1/products/{id}`` contra un PostgreSQL real mediante testcontainers.

Ejemplo de ejecución::

    pytest tests/integration/api/test_products_api.py -v
"""

from __future__ import annotations

import httpx


async def test_create_product_returns_201(api_client: httpx.AsyncClient) -> None:
    """POST /v1/products crea un producto y retorna 201."""
    # First, get a category ID from seed data
    categories_resp = await api_client.get("/v1/categories")
    assert categories_resp.status_code == 200
    category_id = categories_resp.json()[0]["id"]

    response = await api_client.post(
        "/v1/products",
        json={
            "sku": "PROD-INTEGRATION-001",
            "name": "Integration Test Product",
            "unit_of_measure": "unit",
            "category_id": category_id,
            "description": "For testing",
            "min_stock_threshold": 10,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["sku"] == "PROD-INTEGRATION-001"
    assert body["name"] == "Integration Test Product"
    assert body["category_id"] == category_id
    assert body["min_stock_threshold"] == 10
    assert body["created_at"] is not None


async def test_create_product_invalid_sku_returns_422(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/products con SKU invalido (caracteres especiales) retorna 422."""
    categories_resp = await api_client.get("/v1/categories")
    category_id = categories_resp.json()[0]["id"]

    response = await api_client.post(
        "/v1/products",
        json={
            "sku": "INVALID SKU!@#",
            "name": "Bad SKU",
            "unit_of_measure": "unit",
            "category_id": category_id,
        },
    )

    assert response.status_code == 422


async def test_create_product_nonexistent_category_returns_400(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/products con category_id inexistente retorna 400."""
    response = await api_client.post(
        "/v1/products",
        json={
            "sku": "PROD-99999",
            "name": "No Category",
            "unit_of_measure": "unit",
            "category_id": 99999,
        },
    )

    assert response.status_code == 400


async def test_list_products_returns_200_with_pagination(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/products retorna lista paginada con total."""
    response = await api_client.get("/v1/products")

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body
    # Seed data tiene 10 productos
    assert body["total"] >= 10
    assert len(body["items"]) >= 10


async def test_get_product_by_id_returns_200(api_client: httpx.AsyncClient) -> None:
    """GET /v1/products/{id} retorna un producto existente."""
    # Get a product from the list
    products_resp = await api_client.get("/v1/products")
    product_id = products_resp.json()["items"][0]["id"]

    response = await api_client.get(f"/v1/products/{product_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == product_id
    assert body["sku"] is not None
    assert body["name"] is not None


async def test_get_product_by_id_not_found_returns_404(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/products/99999 retorna 404."""
    response = await api_client.get("/v1/products/99999")

    assert response.status_code == 404


async def test_list_products_pagination_works(api_client: httpx.AsyncClient) -> None:
    """GET /v1/products con limit/offset retorna pagina correcta."""
    # Get first page
    resp1 = await api_client.get("/v1/products?limit=3&offset=0")
    assert resp1.status_code == 200
    page1 = resp1.json()
    assert len(page1["items"]) == 3
    assert page1["limit"] == 3
    assert page1["offset"] == 0

    # Get second page
    resp2 = await api_client.get("/v1/products?limit=3&offset=3")
    assert resp2.status_code == 200
    page2 = resp2.json()
    assert len(page2["items"]) == 3
    assert page2["offset"] == 3

    # Products should be in different pages
    ids1 = [p["id"] for p in page1["items"]]
    ids2 = [p["id"] for p in page2["items"]]
    assert set(ids1).isdisjoint(set(ids2))
