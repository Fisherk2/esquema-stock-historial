"""Integration tests for movements API endpoints.

Valida los endpoints de movimientos contra un PostgreSQL real mediante
testcontainers. Cubre IN/OUT/ADJUSTMENT/TRANSFER, validacion de stock,
metadata condicional y paginacion.

Ejemplo de ejecución::

    pytest tests/integration/api/test_movements_api.py -v
"""

from __future__ import annotations

import httpx


async def _get_product_with_stock(api_client: httpx.AsyncClient) -> int:
    """Obtiene un producto del seed que tenga stock positivo."""
    products_resp = await api_client.get("/v1/products")
    products = products_resp.json()["items"]

    for product in products:
        stock_resp = await api_client.get(f"/v1/stock/{product['id']}/current")
        if stock_resp.status_code == 200 and stock_resp.json()["current_stock"] > 0:
            return product["id"]

    return products[0]["id"]


async def _create_product_for_test(
    api_client: httpx.AsyncClient,
    qty: int = 100,
) -> int:
    """Crea un producto nuevo con stock inicial de qty unidades vía IN movement."""
    categories_resp = await api_client.get("/v1/categories")
    category_id = categories_resp.json()[0]["id"]

    # Create product
    product_resp = await api_client.post(
        "/v1/products",
        json={
            "sku": f"MOV-TEST-{qty}",
            "name": f"Movement Test Product {qty}",
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
            "metadata": {"supplier": "Test Supplier"},
        },
    )
    assert in_resp.status_code == 201

    return product_id


async def test_create_in_movement_returns_201(api_client: httpx.AsyncClient) -> None:
    """POST /v1/movements con tipo IN crea movimiento exitosamente."""
    product_id = await _create_product_for_test(api_client)

    response = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 50,
            "metadata": {"supplier": "ACME"},
            "reference": "PO-TEST-001",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["product_id"] == product_id
    assert body["movement_type"] == "IN"
    assert body["quantity"] == 50
    assert body["reference"] == "PO-TEST-001"


async def test_create_out_movement_with_stock_returns_201(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/movements OUT con stock suficiente retorna 201."""
    product_id = await _create_product_for_test(api_client, qty=100)

    response = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "OUT",
            "quantity": 10,
            "metadata": {"destination": "Test Project"},
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["movement_type"] == "OUT"


async def test_create_out_movement_insufficient_stock_returns_409(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/movements OUT sin stock suficiente retorna 409."""
    product_id = await _create_product_for_test(api_client, qty=5)

    response = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "OUT",
            "quantity": 100,
            "metadata": {"destination": "Nowhere"},
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "INSUFFICIENT_STOCK"


async def test_create_transfer_requires_metadata_returns_422(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/movements TRANSFER sin origin/destination retorna 422."""
    product_id = await _create_product_for_test(api_client)

    response = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "TRANSFER",
            "quantity": 5,
            "metadata": {},
        },
    )

    assert response.status_code == 422


async def test_create_adjustment_requires_reason_returns_422(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/movements ADJUSTMENT sin reason retorna 422."""
    product_id = await _create_product_for_test(api_client)

    response = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "ADJUSTMENT",
            "quantity": 5,
            "metadata": {},
        },
    )

    assert response.status_code == 422


async def test_create_movement_invalid_product_returns_400(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/movements con producto inexistente retorna 400."""
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


async def test_get_movement_by_id_returns_200(api_client: httpx.AsyncClient) -> None:
    """GET /v1/movements/{id} retorna movimiento creado."""
    product_id = await _create_product_for_test(api_client)

    # Create movement
    create_resp = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 25,
            "metadata": {"note": "test"},
            "reference": "GET-TEST",
        },
    )
    movement_id = create_resp.json()["id"]

    # Get by ID
    get_resp = await api_client.get(f"/v1/movements/{movement_id}")

    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["id"] == movement_id
    assert body["quantity"] == 25
    assert body["reference"] == "GET-TEST"


async def test_get_movement_not_found_returns_404(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/movements/999999 retorna 404."""
    response = await api_client.get("/v1/movements/999999")

    assert response.status_code == 404


async def test_list_movements_by_product_returns_200(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/movements?product_id= retorna lista paginada con total."""
    product_id = await _create_product_for_test(api_client, qty=100)

    response = await api_client.get(f"/v1/movements?product_id={product_id}")

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
    assert body["total"] >= 1  # At least the IN movement we created
    assert len(body["items"]) >= 1


async def test_list_movements_pagination(api_client: httpx.AsyncClient) -> None:
    """GET /v1/movements con limit/offset paginacion funciona."""
    product_id = await _create_product_for_test(api_client, qty=100)

    # Add 3 more movements
    for i in range(3):
        resp = await api_client.post(
            "/v1/movements",
            json={
                "product_id": product_id,
                "movement_type": "IN",
                "quantity": 1,
                "metadata": {"batch": str(i)},
            },
        )
        assert resp.status_code == 201

    # Get first page
    resp1 = await api_client.get(
        f"/v1/movements?product_id={product_id}&limit=2&offset=0",
    )
    assert resp1.status_code == 200
    page1 = resp1.json()
    assert len(page1["items"]) == 2
    assert page1["limit"] == 2

    # Get second page
    resp2 = await api_client.get(
        f"/v1/movements?product_id={product_id}&limit=2&offset=2",
    )
    assert resp2.status_code == 200
    page2 = resp2.json()
    assert len(page2["items"]) >= 1
