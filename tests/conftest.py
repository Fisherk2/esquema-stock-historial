"""Fixtures compartidas para la suite de tests.

Proporciona fixtures reutilizables entre tests unitarios, de integración
y E2E. Cada fixture sigue el principio SRP: una responsabilidad por fixture.

Nota: Se usa ``TestClient`` síncrono (basado en httpx) por simplicidad en F0.
Para tests asíncronos reales (F6), se migrará a ``httpx.AsyncClient`` con
``pytest-asyncio``.

Ejemplo de uso::

    def test_something(client: TestClient) -> None:
        response = client.get("/v1/health")
        assert response.status_code == 200
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Crea un cliente de test para la aplicación FastAPI.

    Construye una instancia fresca de la app en cada test para garantizar
    aislamiento entre tests.

    Returns:
        TestClient: Cliente HTTP síncrono para hacer requests a la app.

    Ejemplo::

        def test_health(client: TestClient) -> None:
            resp = client.get("/v1/health")
            assert resp.status_code == 200
    """
    app = create_app()
    return TestClient(app)
