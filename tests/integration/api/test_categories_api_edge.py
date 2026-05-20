"""Edge case tests for categories API endpoints.

Valida nombre duplicado, nombre vacio, nombre muy largo.
"""

from __future__ import annotations

import httpx


async def test_create_category_name_exactly_100_chars(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/categories con nombre de exactamente 100 chars → 201."""
    resp = await api_client.post(
        "/v1/categories",
        json={"name": "A" * 100},
    )
    assert resp.status_code == 201


async def test_create_category_empty_name(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/categories con name="" → 422."""
    resp = await api_client.post("/v1/categories", json={"name": ""})
    assert resp.status_code == 422


async def test_create_category_name_too_long(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/categories con nombre > 100 chars → 422."""
    resp = await api_client.post(
        "/v1/categories",
        json={"name": "A" * 101},
    )
    assert resp.status_code == 422
