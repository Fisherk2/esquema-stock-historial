"""Tests E2E de flujos HTTP completos.

Valida las secuencias de operaciones que un usuario real ejecutaria:
1. Crear categoria → producto → movimiento → consultar stock
2. Registrar OUT cuando hay stock insuficiente → error
3. Consultar stock en multiples fechas → consistencia historica
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx


class TestFullInventoryFlow:
    """Flujo completo: categoria → producto → movimiento → stock."""

    async def test_create_and_query_stock(self, api_client: httpx.AsyncClient) -> None:
        """Flujo feliz: crear categoria, producto, movimiento, consultar stock."""
        # 1. Crear categoria
        resp = await api_client.post(
            "/v1/categories",
            json={"name": "E2E-Electronicos", "description": "Dispositivos"},
        )
        assert resp.status_code == 201
        cat_id = resp.json()["id"]

        # 2. Crear producto
        resp = await api_client.post(
            "/v1/products",
            json={
                "sku": "E2E-MONITOR-001",
                "name": 'Monitor 27"',
                "unit_of_measure": "unit",
                "category_id": cat_id,
                "min_stock_threshold": 5,
            },
        )
        assert resp.status_code == 201
        product_id = resp.json()["id"]

        # 3. Registrar entrada de stock
        resp = await api_client.post(
            "/v1/movements",
            json={
                "product_id": product_id,
                "movement_type": "IN",
                "quantity": 100,
                "reference": "E2E-PO-001",
            },
        )
        assert resp.status_code == 201
        movement_id = resp.json()["id"]
        assert movement_id > 0

        # 4. Consultar stock actual
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.status_code == 200
        assert resp.json()["current_stock"] == 100.0

        # 5. Registrar salida
        resp = await api_client.post(
            "/v1/movements",
            json={
                "product_id": product_id,
                "movement_type": "OUT",
                "quantity": 30,
                "reference": "E2E-SO-001",
            },
        )
        assert resp.status_code == 201

        # 6. Verificar stock actualizado
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.status_code == 200
        assert resp.json()["current_stock"] == 70.0

    async def test_insufficient_stock_flow(self, api_client: httpx.AsyncClient) -> None:
        """Flujo de error: OUT con stock insuficiente → 409."""
        # Setup: categoria + producto con 10 unidades
        cat = await api_client.post("/v1/categories", json={"name": "E2E-InsufTest"})
        product = await api_client.post(
            "/v1/products",
            json={
                "sku": "E2E-INSUF-001",
                "name": "Insufficient Test",
                "unit_of_measure": "unit",
                "category_id": cat.json()["id"],
            },
        )
        product_id = product.json()["id"]

        await api_client.post(
            "/v1/movements",
            json={
                "product_id": product_id,
                "movement_type": "IN",
                "quantity": 10,
                "metadata": {"supplier": "test"},
            },
        )

        # Intentar OUT de 20 (solo hay 10)
        resp = await api_client.post(
            "/v1/movements",
            json={
                "product_id": product_id,
                "movement_type": "OUT",
                "quantity": 20,
                "metadata": {"destination": "nowhere"},
            },
        )
        assert resp.status_code == 409
        body = resp.json()
        assert "INSUFFICIENT_STOCK" in body["error"]["code"]

    async def test_historical_stock_consistency(
        self, api_client: httpx.AsyncClient
    ) -> None:
        """Flujo historico: stock en diferentes fechas es consistente."""
        # Setup
        cat = await api_client.post("/v1/categories", json={"name": "E2E-HistTest"})
        product = await api_client.post(
            "/v1/products",
            json={
                "sku": "E2E-HIST-001",
                "name": "Historical Test",
                "unit_of_measure": "unit",
                "category_id": cat.json()["id"],
            },
        )
        product_id = product.json()["id"]

        # Stock actual = 0
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.json()["current_stock"] == 0.0

        # Registrar entrada
        await api_client.post(
            "/v1/movements",
            json={
                "product_id": product_id,
                "movement_type": "IN",
                "quantity": 50,
                "metadata": {"supplier": "test"},
            },
        )

        # Stock actual ahora = 50
        resp = await api_client.get(f"/v1/stock/{product_id}/current")
        assert resp.json()["current_stock"] == 50.0

        # Stock en fecha pasada (antes del movimiento) = 0
        past_date = (datetime.now(tz=UTC) - timedelta(days=365)).isoformat()
        resp = await api_client.get(
            f"/v1/stock/{product_id}/at-date",
            params={"date": past_date},
        )
        assert resp.status_code == 200, f"Unexpected response: {resp.json()}"
        body = resp.json()
        # StockAtDateOutput uses 'stock' key
        assert body["stock"] == 0.0
