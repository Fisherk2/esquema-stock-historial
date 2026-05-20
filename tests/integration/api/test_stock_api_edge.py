"""Edge case tests for stock API endpoints.

Valida producto inexistente, fecha invalida, parametro date ausente.
"""

from __future__ import annotations

import httpx


async def test_current_stock_nonexistent_product(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/stock/99999/current retorna stock 0 (producto inexistente
    no causa error)."""
    resp = await api_client.get("/v1/stock/99999/current")
    # The stock endpoint returns 0.0 for nonexistent products
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_stock"] == 0.0


async def test_stock_at_date_invalid_date_format(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/stock/1/at-date?date=not-a-date → 422."""
    resp = await api_client.get(
        "/v1/stock/1/at-date",
        params={"date": "not-a-date"},
    )
    assert resp.status_code == 422


async def test_stock_at_date_no_query_param(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/stock/1/at-date sin ?date= → 422 (missing required)."""
    resp = await api_client.get("/v1/stock/1/at-date")
    assert resp.status_code == 422


async def test_stock_at_date_nonexistent_product(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/stock/99999/at-date?date=... retorna 0.0 (producto
    inexistente no causa error)."""
    resp = await api_client.get(
        "/v1/stock/99999/at-date",
        params={"date": "2025-01-01T00:00:00Z"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["stock"] == 0.0
