"""Tests para SecurityHeadersMiddleware.

Verifica que todas las respuestas de la API incluyen las cabeceras
de seguridad configuradas:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- Cache-Control: no-store
- Referrer-Policy: strict-origin-when-cross-origin
"""

from __future__ import annotations

import httpx


async def test_health_response_has_security_headers(
    api_client: httpx.AsyncClient,
) -> None:
    """El health check debe incluir todas las cabeceras de seguridad."""
    response = await api_client.get("/v1/health")

    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


async def test_categories_get_has_security_headers(
    api_client: httpx.AsyncClient,
) -> None:
    """GET /v1/categories debe incluir cabeceras de seguridad."""
    response = await api_client.get("/v1/categories")

    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


async def test_error_response_has_security_headers(
    api_client: httpx.AsyncClient,
) -> None:
    """Errores 4xx/5xx deben incluir cabeceras de seguridad."""
    response = await api_client.get("/v1/products/999999")

    assert response.status_code == 404
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


async def test_post_response_has_security_headers(
    api_client: httpx.AsyncClient,
) -> None:
    """Respuestas POST 201 deben incluir cabeceras de seguridad."""
    await api_client.get("/v1/categories")

    response = await api_client.post(
        "/v1/categories",
        json={"name": "Security Headers Test", "description": "Test"},
    )

    assert response.status_code == 201
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
