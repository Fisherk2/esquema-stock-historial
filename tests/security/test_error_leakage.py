"""Tests de seguridad: Error Leakage.

Valida que las respuestas de error NO exponen información sensible:
1. Stack traces de Python
2. SQL queries o fragments
3. Nombres de tablas o columnas (más allá de lo esperado en ErrorResponse)
4. Rutas de archivos del servidor
5. Versiones de software interno
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import httpx


LEAKAGE_PATTERNS = [
    "traceback",
    "stack trace",
    'file "',
    "line ",
    '.py"',  # Python file paths
    "asyncpg",
    "psycopg",
    "sqlalchemy",
    "internal server error",  # Generic 500 without detail
]

SQL_LEAKAGE_PATTERNS = [
    "select ",
    "insert ",
    "update ",
    "delete ",
    "drop ",
    "from movements",
    "from products",
    "where ",
    "syntax error",
    "unterminated string",
]


class TestNoErrorLeakage:
    """Las respuestas de error no deben exponer información interna."""

    @pytest.mark.parametrize(
        "payload",
        [
            {"product_id": -1, "movement_type": "IN", "quantity": 10},
            {"product_id": 1, "movement_type": "HACK", "quantity": 10},
            {"product_id": 1, "movement_type": "IN", "quantity": -5},
        ],
    )
    async def test_validation_errors_no_leakage(
        self, api_client: httpx.AsyncClient, payload: dict
    ) -> None:
        """Errores de validación 422 no exponen stack traces ni SQL."""
        resp = await api_client.post("/v1/movements", json=payload)
        body_str = str(resp.json()).lower()

        for pattern in LEAKAGE_PATTERNS:
            assert pattern.lower() not in body_str, f"Leakage detected: '{pattern}'"

        for pattern in SQL_LEAKAGE_PATTERNS:
            assert pattern.lower() not in body_str, f"SQL leakage: '{pattern}'"

    async def test_404_errors_no_leakage(self, api_client: httpx.AsyncClient) -> None:
        """Errores 404 no exponen información interna."""
        resp = await api_client.get("/v1/products/99999")
        if resp.status_code == 404:
            body_str = str(resp.json()).lower()
            for pattern in LEAKAGE_PATTERNS:
                assert pattern.lower() not in body_str

    async def test_server_errors_no_stack_trace(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Errores 500 no exponen stack traces.

        Nota: Este test verifica el comportamiento en producción.
        En desarrollo, FastAPI puede incluir tracebacks.
        """
        # Intentar crear un movimiento con product_id que causa FK error
        resp = await api_client.post(
            "/v1/movements",
            json={"product_id": 99999, "movement_type": "IN", "quantity": 10},
        )
        body_str = str(resp.json()).lower()
        # Verificar que no hay stack trace detallado
        assert "traceback" not in body_str


class TestImmutabilityEnforcement:
    """Los movimientos no deben poder modificarse ni eliminarse via API."""

    async def test_no_update_endpoint(self, api_client: httpx.AsyncClient) -> None:
        """PUT /v1/movements/1 → 405 Method Not Allowed."""
        resp = await api_client.put("/v1/movements/1", json={"quantity": 999})
        assert resp.status_code == 405

    async def test_no_patch_endpoint(self, api_client: httpx.AsyncClient) -> None:
        """PATCH /v1/movements/1 → 405 Method Not Allowed."""
        resp = await api_client.patch("/v1/movements/1", json={"quantity": 999})
        assert resp.status_code == 405

    async def test_no_delete_endpoint(self, api_client: httpx.AsyncClient) -> None:
        """DELETE /v1/movements/1 → 405 Method Not Allowed."""
        resp = await api_client.delete("/v1/movements/1")
        assert resp.status_code == 405
