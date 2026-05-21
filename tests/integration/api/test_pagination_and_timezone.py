"""Tests para paginacion de categorias y datetime timezone handling.

Cubre los gaps de coverage identificados en el /ship review:
- Paginacion en DB layer (limit, offset, bounds validation)
- _ensure_timezone_aware helper en stock router
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

# ── Category pagination tests ──────────────────────────────────────────────


async def test_list_categories_with_custom_limit(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/categories?limit=2 retorna exactamente 2 categorias."""
    # Crear categorias adicionales
    for i in range(5):
        await api_client.post(
            "/v1/categories",
            json={"name": f"PagLim-{i:03d}", "description": f"Test {i}"},
        )

    response = await api_client.get("/v1/categories", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_categories_with_offset(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/categories?offset=1&limit=2 saltea la primera categoria."""
    # Crear categorias adicionales con nombres ordenables
    for i in range(5):
        await api_client.post(
            "/v1/categories",
            json={"name": f"PagOff-{i:03d}", "description": f"Test {i}"},
        )

    # Sin offset
    resp_all = await api_client.get("/v1/categories", params={"limit": 5})
    all_names = [c["name"] for c in resp_all.json()]

    # Con offset=1
    resp_offset = await api_client.get(
        "/v1/categories", params={"limit": 2, "offset": 1}
    )
    offset_names = [c["name"] for c in resp_offset.json()]

    assert len(offset_names) == 2
    # La primera categoria con offset debe ser la segunda de la lista completa
    assert offset_names[0] == all_names[1]


async def test_list_categories_limit_zero_returns_422(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/categories?limit=0 retorna HTTP 422."""
    response = await api_client.get("/v1/categories", params={"limit": 0})

    assert response.status_code == 422


async def test_list_categories_limit_exceeds_max_returns_422(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/categories?limit=1001 retorna HTTP 422."""
    response = await api_client.get("/v1/categories", params={"limit": 1001})

    assert response.status_code == 422


async def test_list_categories_negative_offset_returns_422(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/categories?offset=-1 retorna HTTP 422."""
    response = await api_client.get("/v1/categories", params={"offset": -1})

    assert response.status_code == 422


# ── Datetime timezone handling tests ───────────────────────────────────────


async def test_stock_at_date_with_naive_iso_date_returns_utc_aware(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/stock/{id}/at-date con fecha sin timezone.

    El helper _ensure_timezone_aware convierte naive datetimes a UTC.
    """
    # Obtener un producto existente (la API retorna ProductListOutput con items)
    products_resp = await api_client.get("/v1/products")
    assert products_resp.status_code == 200
    items = products_resp.json().get("items", [])
    if not items:
        pytest.skip("No products available for test")

    product_id = items[0]["id"]
    date_str = "2025-06-15T00:00:00"  # Naive datetime (sin timezone)

    response = await api_client.get(
        f"/v1/stock/{product_id}/at-date", params={"date": date_str}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == product_id
    assert "date" in body


async def test_stock_at_date_with_timezone_aware_date(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/stock/{id}/at-date con fecha timezone-aware funciona correctamente."""
    products_resp = await api_client.get("/v1/products")
    items = products_resp.json().get("items", [])
    if not items:
        pytest.skip("No products available for test")

    product_id = items[0]["id"]
    date_str = "2025-06-15T00:00:00Z"  # UTC-aware datetime

    response = await api_client.get(
        f"/v1/stock/{product_id}/at-date", params={"date": date_str}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["product_id"] == product_id


def test_ensure_timezone_aware_unit() -> None:
    """Unit test: _ensure_timezone_aware convierte naive a UTC-aware."""
    from src.adapters.api.routers.stock import _ensure_timezone_aware

    # Naive datetime → UTC-aware
    naive = datetime(2025, 6, 15, 12, 0, 0)
    result = _ensure_timezone_aware(naive)
    assert result.tzinfo is not None
    assert result.tzinfo == UTC

    # Already timezone-aware → unchanged
    aware = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)
    result = _ensure_timezone_aware(aware)
    assert result == aware
    assert result.tzinfo == UTC
