"""Tests unitarios del endpoint de healthcheck.

Valida que ``GET /v1/health`` responda correctamente. Estos tests
son smoke tests que verifican la infraestructura básica de la app
(routers, middleware, serialización JSON).

Ejemplo::

    pytest tests/unit/test_health.py -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# TYPE_CHECKING: regla TCH002 de ruff — TestClient solo se usa como
# anotación de tipo, no en runtime. Se importa condicionalmente para
# evitar import innecesario en tiempo de ejecución.
if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def test_health_check_returns_ok(client: TestClient) -> None:
    """Verifica que el endpoint de health responda 200 con status ok.

    Args:
        client: Fixture de conftest que proporciona TestClient configurado.
    """
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
