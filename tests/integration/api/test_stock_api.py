"""Integration tests for stock API endpoints.

Valida los endpoints ``GET /v1/stock/{id}/current`` y
``GET /v1/stock/{id}/at-date`` contra un PostgreSQL real mediante
testcontainers.

Ejemplo de ejecución::

    pytest tests/integration/api/test_stock_api.py -v
"""

from __future__ import annotations

import httpx


async def _create_product_for_test(api_client: httpx.AsyncClient, qty: int = 50) -> int:
    """Crea un producto nuevo con stock inicial de qty unidades."""
    categories_resp = await api_client.get("/v1/categories")
    category_id = categories_resp.json()[0]["id"]

    product_resp = await api_client.post(
        "/v1/products",
        json={
            "sku": f"STOCK-TEST-{qty}",
            "name": f"Stock Test Product {qty}",
            "unit_of_measure": "unit",
            "category_id": category_id,
        },
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]

    # Add stock via IN movement
    in_resp = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": qty,
            "metadata": {"supplier": "Test"},
        },
    )
    assert in_resp.status_code == 201

    return product_id


async def test_get_current_stock_returns_200(api_client: httpx.AsyncClient) -> None:
    """GET /v1/stock/{id}/current retorna stock actual."""
    product_id = await _create_product_for_test(api_client, qty=50)

    response = await api_client.get(f"/v1/stock/{product_id}/current")

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == product_id
    assert body["current_stock"] >= 50.0


async def test_get_current_stock_reflects_out_movements(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/stock/{id}/current refleja stock despues de OUT."""
    product_id = await _create_product_for_test(api_client, qty=100)

    # Check initial stock
    initial_resp = await api_client.get(f"/v1/stock/{product_id}/current")
    initial_stock = initial_resp.json()["current_stock"]

    # Create OUT movement
    out_resp = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "OUT",
            "quantity": 30,
            "metadata": {"destination": "Test"},
        },
    )
    assert out_resp.status_code == 201

    # Check stock decreased
    final_resp = await api_client.get(f"/v1/stock/{product_id}/current")
    final_stock = final_resp.json()["current_stock"]

    assert final_stock == initial_stock - 30.0


async def test_get_current_stock_no_movements_returns_zero(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/stock/{id}/current para producto sin movimientos retorna 0.0."""
    categories_resp = await api_client.get("/v1/categories")
    category_id = categories_resp.json()[0]["id"]

    # Create product WITHOUT any movements
    product_resp = await api_client.post(
        "/v1/products",
        json={
            "sku": "STOCK-ZERO-TEST",
            "name": "Zero Stock Product",
            "unit_of_measure": "unit",
            "category_id": category_id,
        },
    )
    product_id = product_resp.json()["id"]

    response = await api_client.get(f"/v1/stock/{product_id}/current")

    assert response.status_code == 200
    body = response.json()
    assert body["current_stock"] == 0.0


async def test_get_stock_at_date_returns_200(api_client: httpx.AsyncClient) -> None:
    """GET /v1/stock/{id}/at-date con fecha valida retorna stock historico."""
    product_id = await _create_product_for_test(api_client, qty=75)

    response = await api_client.get(
        f"/v1/stock/{product_id}/at-date",
        params={"date": "2030-01-01T00:00:00Z"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == product_id
    assert body["stock"] >= 75.0


async def test_get_stock_at_date_with_iso8601_format(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/stock/{id}/at-date acepta formato ISO 8601."""
    product_id = await _create_product_for_test(api_client)

    response = await api_client.get(
        f"/v1/stock/{product_id}/at-date",
        params={"date": "2026-05-19T12:00:00+00:00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == product_id
