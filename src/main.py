"""Entrypoint y factory de la aplicación FastAPI.

Este módulo implementa el patrón Factory Method para construir la instancia
de FastAPI con sus routers, middleware y ciclo de vida configurados.
La función ``create_app()`` es el punto de entrada para el servidor uvicorn
y para los tests.

Ejemplo::

    from src.main import create_app

    app = create_app()
    # uvicorn src.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.adapters.api.routers.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook para inicialización y limpieza de recursos.

    Se ejecuta al arrancar y al apagar la aplicación. Aquí se integrará
    la inicialización del pool de conexiones (F1) y el scheduler (F5).
    """
    yield


def create_app() -> FastAPI:
    """Construye y configura la instancia de FastAPI.

    Aplica el patrón Factory Method para componer la aplicación a partir
    de routers modulares. Cada router se registra con su prefijo y tag
    de OpenAPI.

    Returns:
        FastAPI: Instancia configurada con lifespan y routers registrados.

    Ejemplo::

        app = create_app()
        # GET /v1/health -> {"status": "ok"}
    """
    app = FastAPI(
        title="Stock Historial",
        description="Sistema de gestión de inventario con Source of Truth Inmutable",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Composición modular: cada router se registra con su prefijo /v1
    app.include_router(health_router, prefix="/v1")

    return app


app = create_app()
