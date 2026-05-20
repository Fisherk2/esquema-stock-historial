"""Tests unitarios para el middleware de request logging (SPEC-52)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.api.middleware.request_logging import (
    RequestLoggingMiddleware,
    get_request_id,
)


@pytest.fixture()
def logging_app() -> FastAPI:
    """App FastAPI con middleware de request logging."""
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.get("/v1/health")
    async def health():
        return {"status": "ok"}

    @app.get("/v1/products")
    async def products():
        return {"request_id": get_request_id()}

    return app


class TestRequestLoggingMiddleware:
    """Verifica comportamientos del middleware."""

    def test_returns_request_id_in_header(self, logging_app: FastAPI) -> None:
        """Debe incluir X-Request-ID en los headers de respuesta."""
        client = TestClient(logging_app)
        response = client.get("/v1/products")

        assert "X-Request-ID" in response.headers

    def test_request_id_is_valid_uuid(self, logging_app: FastAPI) -> None:
        """El X-Request-ID debe ser un UUID valido."""
        import uuid

        client = TestClient(logging_app)
        response = client.get("/v1/products")

        # No debe lanzar excepcion si es UUID valido
        uuid.UUID(response.headers["X-Request-ID"])

    def test_different_requests_get_different_ids(self, logging_app: FastAPI) -> None:
        """Cada request debe tener un request_id unico."""
        client = TestClient(logging_app)
        resp1 = client.get("/v1/products")
        resp2 = client.get("/v1/products")

        assert resp1.headers["X-Request-ID"] != resp2.headers["X-Request-ID"]

    def test_excludes_health_from_logging(
        self, logging_app: FastAPI, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Los health checks no deben generar logs del middleware."""
        client = TestClient(logging_app)

        with caplog.at_level("INFO"):
            client.get("/v1/health")

        # No debe haber logs del request_logging para /v1/health
        health_logs = [
            r
            for r in caplog.records
            if "request_logging" in r.name and "/v1/health" in r.getMessage()
        ]
        assert len(health_logs) == 0

    def test_get_request_id_returns_none_outside_request(self) -> None:
        """get_request_id debe retornar None fuera de un request."""
        # En un contexto sin request, no hay request
        from src.adapters.api.middleware.request_logging import request_id_ctx

        assert request_id_ctx.get() is None
