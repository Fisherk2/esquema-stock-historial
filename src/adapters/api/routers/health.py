"""Endpoint de healthcheck para orquestación y monitoring.

Router que expone ``GET /v1/health`` para verificar que la aplicación
está operativa y conectada a la base de datos. Usado por Docker Compose
y Kubernetes para healthchecks y readiness probes.

Patrón aplicado: KISS — el endpoint más simple posible. Separation of
Concerns — solo maneja HTTP, sin reglas de negocio.

Ejemplo de respuesta con DB conectada::

    GET /v1/health
    HTTP 200
    {"status": "ok", "db": "connected"}

Ejemplo de respuesta sin DB::

    GET /v1/health
    HTTP 200
    {"status": "degraded", "db": "unavailable"}
"""

from __future__ import annotations

import logging

from fastapi import APIRouter

from src.infrastructure.db.connection import get_pool

logger = logging.getLogger(__name__)

# Tag "health" agrupa este endpoint en la documentación OpenAPI
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Verifica el estado operativo de la aplicación y conectividad DB.

    Ejecuta ``SELECT 1`` contra PostgreSQL para validar que el pool de
    conexiones está activo. Si la DB no está disponible, retorna estado
    ``degraded`` (no error HTTP) para indicar que la app funciona pero
    sin acceso a datos.

    Returns:
        dict: Respuesta con ``status`` (ok|degraded) y ``db``
            (connected|unavailable). Código HTTP 200 en ambos casos.

    Ejemplo::

        >>> response = client.get("/v1/health")
        >>> response.json()
        {"status": "ok", "db": "connected"}
    """
    pool = await get_pool()

    if pool is None:
        return {"status": "degraded", "db": "unavailable"}

    try:
        await pool.execute("SELECT 1")
        return {"status": "ok", "db": "connected"}
    except Exception:
        logger.warning("Health check: database query failed")
        return {"status": "degraded", "db": "unavailable"}
