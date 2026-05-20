"""Tests unitarios para el error handler de ConcurrencyConflictError (SPEC-51)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.adapters.api.middleware.error_handler import register_error_handlers
from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError


@pytest.fixture()
def error_app() -> FastAPI:
    """App FastAPI con solo handlers de error registrados."""
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/raise-concurrency")
    async def raise_concurrency():
        raise ConcurrencyConflictError(
            operation="refresh_view", detail="serialization error"
        )

    @app.get("/raise-concurrency-no-detail")
    async def raise_concurrency_no_detail():
        raise ConcurrencyConflictError(operation="some_operation")

    return app


def test_concurrency_conflict_returns_409(error_app: FastAPI) -> None:
    """ConcurrencyConflictError debe mapearse a HTTP 409."""
    client = TestClient(error_app)
    response = client.get("/raise-concurrency")

    assert response.status_code == 409


def test_concurrency_conflict_returns_correct_error_code(error_app: FastAPI) -> None:
    """El codigo de error debe ser CONCURRENCY_CONFLICT."""
    client = TestClient(error_app)
    response = client.get("/raise-concurrency")

    body = response.json()
    assert body["error"]["code"] == "CONCURRENCY_CONFLICT"


def test_concurrency_conflict_includes_operation_in_details(
    error_app: FastAPI,
) -> None:
    """Los details deben incluir la operacion en conflicto."""
    client = TestClient(error_app)
    response = client.get("/raise-concurrency")

    body = response.json()
    assert body["error"]["details"]["operation"] == "refresh_view"


def test_concurrency_conflict_includes_detail_when_provided(
    error_app: FastAPI,
) -> None:
    """Los details deben incluir el detalle adicional si se proporciona."""
    client = TestClient(error_app)
    response = client.get("/raise-concurrency")

    body = response.json()
    assert body["error"]["details"]["detail"] == "serialization error"


def test_concurrency_conflict_detail_omitted_when_not_provided(
    error_app: FastAPI,
) -> None:
    """El campo detail no debe estar en details cuando no se proporciona."""
    client = TestClient(error_app)
    response = client.get("/raise-concurrency-no-detail")

    body = response.json()
    assert "detail" not in body["error"]["details"]
