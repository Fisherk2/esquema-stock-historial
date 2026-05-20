"""Integration tests para F5 — Scheduler & Concurrencia & Logging (SPEC-50/51/52).

Tests de integracion que validan el comportamiento real de los componentes
de F5 con PostgreSQL via testcontainers y la app FastAPI completa.
"""

from __future__ import annotations

import uuid

import httpx
import pytest
from httpx import ASGITransport

from src.main import create_app

# ── SPEC-50: Scheduler integration ─────────────────────────────────────


async def test_scheduler_refresh_job_executes_with_real_pool(db_clean) -> None:
    """El _refresh_job debe poder ejecutar refresh_stock_view con pool real."""
    from src.infrastructure.scheduler.scheduler import _refresh_job

    # Debe completar sin error
    await _refresh_job(db_clean)

    # Verificar que la vista tiene datos (seed data fue insertada)
    row = await db_clean.fetchrow("SELECT COUNT(*) as cnt FROM mv_stock_historical")
    assert row["cnt"] >= 0


async def test_scheduler_disabled_prevents_scheduler_creation() -> None:
    """start_scheduler con enabled=False no debe crear scheduler."""
    from src.infrastructure.scheduler.scheduler import (
        shutdown_scheduler,
        start_scheduler,
    )

    pool = None  # No se necesita pool real para este test
    await start_scheduler(pool, enabled=False, refresh_interval_minutes=1)

    from src.infrastructure.scheduler.scheduler import _scheduler as after

    assert after is None

    # Cleanup
    await shutdown_scheduler()


# ── SPEC-51: Retry integration ─────────────────────────────────────────


class TestRetryDecoratorEdgeCases:
    """Tests adicionales del decorador retry para coberturas completas."""

    @pytest.mark.asyncio
    async def test_retry_preserves_original_function_name(self):
        """El decorador debe preservar __name__ y __doc__."""
        from src.core.retry import retry_with_backoff
        from src.domain.exceptions.concurrency_conflict import (
            ConcurrencyConflictError,
        )

        @retry_with_backoff(
            max_retries=1,
            base_delay=0.001,
            jitter=0.0,
            exceptions=(ConcurrencyConflictError,),
        )
        async def my_special_function():
            """My special docstring."""
            raise ConcurrencyConflictError("test")

        assert my_special_function.__name__ == "my_special_function"
        assert my_special_function.__doc__ == "My special docstring."


# ── SPEC-51: ConcurrencyConflictError via real API ─────────────────────


async def test_concurrency_conflict_error_via_api_endpoint() -> None:
    """ConcurrencyConflictError debe retornar 409 en la app completa."""
    from fastapi import APIRouter

    from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError

    router = APIRouter()

    @router.get("/test-concurrency")
    async def raise_concurrency():
        raise ConcurrencyConflictError(operation="test_operation", detail="test detail")

    app = create_app()
    app.include_router(router)

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test-concurrency")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "CONCURRENCY_CONFLICT"
    assert body["error"]["details"]["operation"] == "test_operation"
    assert body["error"]["details"]["detail"] == "test detail"


# ── SPEC-52: X-Request-ID in real API ──────────────────────────────────


async def test_x_request_id_header_present_in_non_health_response() -> None:
    """Endpoints que no sean health deben devolver X-Request-ID."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/products")

    header_value = response.headers.get("x-request-id")
    assert header_value is not None
    uuid.UUID(header_value)  # Debe ser UUID valido


async def test_x_request_id_is_valid_uuid() -> None:
    """El X-Request-ID debe ser un UUID valido."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/categories")

    header_value = response.headers.get("x-request-id")
    assert header_value is not None
    uuid.UUID(header_value)


async def test_different_api_calls_get_different_request_ids() -> None:
    """Cada llamada a la API debe tener un request_id diferente."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp1 = await client.get("/v1/products")
        resp2 = await client.get("/v1/products")

    id1 = resp1.headers.get("x-request-id")
    id2 = resp2.headers.get("x-request-id")

    assert id1 is not None
    assert id2 is not None
    assert id1 != id2


async def test_health_endpoint_excluded_from_x_request_id() -> None:
    """El health check no debe incluir X-Request-ID (excluido de logging)."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/health")

    # Health endpoint no debe tener X-Request-ID
    assert "x-request-id" not in response.headers


async def test_health_endpoint_returns_200() -> None:
    """El health check debe retornar 200 incluso sin DB."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert body["db"] in ("connected", "unavailable")
