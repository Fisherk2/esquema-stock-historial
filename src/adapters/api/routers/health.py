"""Endpoint de healthcheck para orquestación y monitoring.

Router mínimo que expone ``GET /v1/health`` para verificar que la
aplicación está operativa. Usado por Docker Compose y Kubernetes
para healthchecks y readiness probes.

Patrón aplicado: KISS — el endpoint más simple posible, sin lógica
innecesaria. Separation of Concerns — solo maneja HTTP, sin acceso
a datos ni reglas de negocio.

Ejemplo de respuesta::

    GET /v1/health
    HTTP 200
    {"status": "ok"}
"""

from __future__ import annotations

from fastapi import APIRouter

# Tag "health" agrupa este endpoint en la documentación OpenAPI
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Verifica el estado operativo de la aplicación.

    Returns:
        dict: Respuesta con ``{"status": "ok"}`` y código HTTP 200.

    Ejemplo::

        >>> response = client.get("/v1/health")
        >>> response.json()
        {"status": "ok"}
    """
    return {"status": "ok"}
