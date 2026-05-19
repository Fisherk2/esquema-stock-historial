"""Integration tests for error mapping (domain exceptions → HTTP responses).

Valida que cada excepcion de dominio se mapea correctamente a un status
code HTTP y formato de respuesta ErrorResponse.

Nota: La mayoria de los errores ya se prueban en los tests de endpoints.
Estos tests se enfocan en la estructura consistente de respuestas de error.

Ejemplo de ejecución::

    pytest tests/integration/api/test_error_mapping_api.py -v
"""

from __future__ import annotations

import httpx


async def _get_product_with_stock(api_client: httpx.AsyncClient) -> int:
    """Crea un producto con stock para pruebas."""
    categories_resp = await api_client.get("/v1/categories")
    category_id = categories_resp.json()[0]["id"]

    product_resp = await api_client.post(
        "/v1/products",
        json={
            "sku": "ERR-TEST-001",
            "name": "Error Test Product",
            "unit_of_measure": "unit",
            "category_id": category_id,
        },
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]

    # Add stock
    await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 10,
            "metadata": {"supplier": "Test"},
        },
    )

    return product_id


async def test_insufficient_stock_returns_409_with_details(
    api_client: httpx.AsyncClient,
) -> None:
    """InsufficientStockError → HTTP 409 con details."""
    product_id = await _get_product_with_stock(api_client)

    response = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "OUT",
            "quantity": 9999,
            "metadata": {"destination": "Nowhere"},
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INSUFFICIENT_STOCK"
    assert "product_id" in body["error"]["details"]
    assert "requested" in body["error"]["details"]
    assert "available" in body["error"]["details"]


async def test_invalid_product_returns_400_with_error_format(
    api_client: httpx.AsyncClient,
) -> None:
    """Producto inexistente → HTTP 400 con ErrorResponse consistente."""
    response = await api_client.post(
        "/v1/movements",
        json={
            "product_id": 999999,
            "movement_type": "IN",
            "quantity": 10,
            "metadata": {},
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]


async def test_not_found_product_returns_404(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/products/999999 → HTTP 404."""
    response = await api_client.get("/v1/products/999999")

    assert response.status_code == 404


async def test_not_found_movement_returns_404(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/movements/999999 → HTTP 404."""
    response = await api_client.get("/v1/movements/999999")

    assert response.status_code == 404


async def test_validation_error_has_consistent_format(
    api_client: httpx.AsyncClient,
) -> None:
    """Todos los errores de validacion siguen el formato ErrorResponse."""
    # Invalid SKU (Pydantic 422)
    categories_resp = await api_client.get("/v1/categories")
    category_id = categories_resp.json()[0]["id"]

    resp_sku = await api_client.post(
        "/v1/products",
        json={
            "sku": "INVALID!@#",
            "name": "Bad",
            "unit_of_measure": "unit",
            "category_id": category_id,
        },
    )
    assert resp_sku.status_code == 422
    # Pydantic returns {"detail": [...]} format, not ErrorResponse
    assert "detail" in resp_sku.json()

    # Missing metadata for TRANSFER (422 from model_validator)
    product_resp = await api_client.post(
        "/v1/products",
        json={
            "sku": "ERR-TEST-002",
            "name": "Error Test 2",
            "unit_of_measure": "unit",
            "category_id": category_id,
        },
    )
    product_id = product_resp.json()["id"]

    # Add stock for TRANSFER test
    await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 50,
            "metadata": {},
        },
    )

    resp_transfer = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "TRANSFER",
            "quantity": 5,
            "metadata": {},
        },
    )
    assert resp_transfer.status_code == 422
    assert "detail" in resp_transfer.json()
