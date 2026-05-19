"""Integration tests for categories API endpoints.

Valida los endpoints ``POST /v1/categories`` y ``GET /v1/categories``
contra un PostgreSQL real mediante testcontainers.

Ejemplo de ejecución::

    pytest tests/integration/api/test_categories_api.py -v
"""

from __future__ import annotations

import httpx

# ── Tests ────────────────────────────────────────────────────────────────


async def test_create_category_returns_201(api_client: httpx.AsyncClient) -> None:
    """POST /v1/categories crea una categoria y retorna 201 con id y created_at."""
    response = await api_client.post(
        "/v1/categories",
        json={"name": "Test Category", "description": "For testing"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["name"] == "Test Category"
    assert body["description"] == "For testing"
    assert body["created_at"] is not None


async def test_create_category_empty_name_returns_422(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/categories con nombre vacío retorna 422."""
    response = await api_client.post(
        "/v1/categories",
        json={"name": ""},
    )

    assert response.status_code == 422


async def test_list_categories_returns_200(api_client: httpx.AsyncClient) -> None:
    """GET /v1/categories retorna lista de categorias (seed data)."""
    response = await api_client.get("/v1/categories")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    # Seed data tiene 3 categorias
    assert len(body) >= 3


async def test_list_categories_after_create(api_client: httpx.AsyncClient) -> None:
    """POST seguido de GET muestra la nueva categoria en la lista."""
    # Create a new category
    create_response = await api_client.post(
        "/v1/categories",
        json={"name": "Integration Test Category"},
    )
    assert create_response.status_code == 201
    created_id = create_response.json()["id"]

    # List and verify it appears
    list_response = await api_client.get("/v1/categories")
    assert list_response.status_code == 200
    categories = list_response.json()
    ids = [c["id"] for c in categories]
    assert created_id in ids


async def test_get_category_output_has_correct_fields(
    api_client: httpx.AsyncClient,
) -> None:
    """La respuesta de POST /v1/categories tiene la estructura esperada."""
    response = await api_client.post(
        "/v1/categories",
        json={"name": "Field Check"},
    )

    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert "name" in body
    assert "description" in body
    assert "created_at" in body
    # No extra unexpected fields
    assert set(body.keys()) == {"id", "name", "description", "created_at"}


async def test_create_category_name_too_long_returns_422(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/categories con nombre mayor a 100 caracteres retorna 422."""
    response = await api_client.post(
        "/v1/categories",
        json={"name": "A" * 101},
    )

    assert response.status_code == 422


async def test_create_category_without_description_returns_201(
    api_client: httpx.AsyncClient,
) -> None:
    """POST /v1/categories sin descripcion opcional retorna 201."""
    response = await api_client.post(
        "/v1/categories",
        json={"name": "No Description"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "No Description"
    assert body["description"] is None
