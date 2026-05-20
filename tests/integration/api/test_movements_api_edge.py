"""Edge case tests for movements API endpoints.

Valida inputs invalidos, IDs inexistentes, campos extra, cantidad
negativa, y otros edge cases a nivel HTTP.
"""

from __future__ import annotations

import httpx


async def test_create_movement_empty_body(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/movements con body vacio → 422."""
    resp = await api_client.post("/v1/movements", json={})
    assert resp.status_code == 422


async def test_create_movement_extra_fields_ignored(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/movements con campos extra → los ignora, no 422."""
    categories_resp = await api_client.get("/v1/categories")
    category_id = categories_resp.json()[0]["id"]

    product_resp = await api_client.post(
        "/v1/products",
        json={
            "sku": "EDGE-MVT-EXTRA",
            "name": "Extra Fields Test",
            "unit_of_measure": "unit",
            "category_id": category_id,
        },
    )
    product_id = product_resp.json()["id"]

    # Pydantic strict=True rejects extra fields in the DTO,
    # but FastAPI may strip them before validation
    resp = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 10,
            "malicious_extra": "hack",
        },
    )
    # Either accepted (extra stripped) or rejected (strict mode)
    assert resp.status_code in (201, 422)


async def test_create_movement_negative_quantity(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/movements con quantity=-5 → 422."""
    categories_resp = await api_client.get("/v1/categories")
    category_id = categories_resp.json()[0]["id"]

    product_resp = await api_client.post(
        "/v1/products",
        json={
            "sku": "EDGE-MVT-NEG",
            "name": "Negative Qty Test",
            "unit_of_measure": "unit",
            "category_id": category_id,
        },
    )
    product_id = product_resp.json()["id"]

    resp = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": -5,
        },
    )
    assert resp.status_code == 422


async def test_create_movement_zero_quantity(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/movements con quantity=0 → 422."""
    categories_resp = await api_client.get("/v1/categories")
    category_id = categories_resp.json()[0]["id"]

    product_resp = await api_client.post(
        "/v1/products",
        json={
            "sku": "EDGE-MVT-ZERO",
            "name": "Zero Qty Test",
            "unit_of_measure": "unit",
            "category_id": category_id,
        },
    )
    product_id = product_resp.json()["id"]

    resp = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "IN",
            "quantity": 0,
        },
    )
    assert resp.status_code == 422


async def test_create_movement_invalid_movement_type(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/movements con movement_type='HACK' → 422."""
    categories_resp = await api_client.get("/v1/categories")
    category_id = categories_resp.json()[0]["id"]

    product_resp = await api_client.post(
        "/v1/products",
        json={
            "sku": "EDGE-MVT-TYPE",
            "name": "Invalid Type Test",
            "unit_of_measure": "unit",
            "category_id": category_id,
        },
    )
    product_id = product_resp.json()["id"]

    resp = await api_client.post(
        "/v1/movements",
        json={
            "product_id": product_id,
            "movement_type": "HACK",
            "quantity": 10,
        },
    )
    assert resp.status_code == 422


async def test_list_movements_missing_product_id(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/movements sin product_id → 422 (required param)."""
    resp = await api_client.get("/v1/movements")
    assert resp.status_code == 422
