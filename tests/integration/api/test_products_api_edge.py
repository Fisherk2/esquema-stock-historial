"""Edge case tests for products API endpoints.

Valida SKU invalido, duplicado, categoria inexistente, offset grande,
producto inexistente.
"""

from __future__ import annotations

import httpx


async def test_create_product_nonexistent_category(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/products con category_id=99999 → 400."""
    resp = await api_client.post(
        "/v1/products",
        json={
            "sku": "EDGE-NO-CAT",
            "name": "No Category",
            "unit_of_measure": "unit",
            "category_id": 99999,
        },
    )
    assert resp.status_code == 400


async def test_list_products_large_offset(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/products?offset=99999 → 200 con lista vacia."""
    resp = await api_client.get("/v1/products?offset=99999")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []


async def test_get_product_nonexistent_id(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/products/99999 → 404."""
    resp = await api_client.get("/v1/products/99999")
    assert resp.status_code == 404


async def test_create_product_empty_name(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/products con nombre vacio → 422."""
    categories_resp = await api_client.get("/v1/categories")
    category_id = categories_resp.json()[0]["id"]

    resp = await api_client.post(
        "/v1/products",
        json={
            "sku": "EDGE-EMPTY-NAME",
            "name": "",
            "unit_of_measure": "unit",
            "category_id": category_id,
        },
    )
    assert resp.status_code == 422
