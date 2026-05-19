"""Entrypoint y factory de la aplicación FastAPI.

Este módulo implementa el patrón Factory Method para construir la instancia
de FastAPI con sus routers, middleware y ciclo de vida configurados.
La función ``create_app()`` es el punto de entrada para el servidor uvicorn
y para los tests.

El lifespan gestiona el ciclo de vida del pool de conexiones asyncpg:
inicialización al arranque y cierre al apagar la aplicación.

Ejemplo::

    from src.main import create_app

    app = create_app()
    # uvicorn src.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.adapters.api.routers.health import router as health_router
from src.core.config import Settings
from src.infrastructure.db.connection import close_pool, init_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle hook para inicialización y limpieza de recursos.

    Inicializa el pool de conexiones asyncpg al arrancar y lo cierra
    al apagar la aplicación. En F5 se integrará también el scheduler.
    """
    settings = Settings()
    await init_pool(settings)
    yield
    await close_pool()


def create_app() -> FastAPI:
    """Construye y configura la instancia de FastAPI.

    Aplica el patron Factory Method para componer la aplicacion a partir
    de routers modulares. Cada router se registra con su prefijo y tag
    de OpenAPI.

    Returns:
        FastAPI: Instancia configurada con lifespan, routers y error
            handlers registrados.

    Ejemplo::

        app = create_app()
        # GET /v1/health -> {"status": "ok"}
    """
    app = FastAPI(
        title="Stock Historial",
        description="Sistema de gestion de inventario con Source of Truth Inmutable",
        version="0.4.0",
        lifespan=lifespan,
    )

    # Composicion modular: cada router se registra con su prefijo /v1
    app.include_router(health_router, prefix="/v1")

    # F4: Routers de dominio
    from src.adapters.api.middleware.error_handler import register_error_handlers
    from src.adapters.api.routers.categories import router as categories_router
    from src.adapters.api.routers.movements import router as movements_router
    from src.adapters.api.routers.products import router as products_router
    from src.adapters.api.routers.stock import router as stock_router

    app.include_router(movements_router, prefix="/v1")
    app.include_router(stock_router, prefix="/v1")
    app.include_router(products_router, prefix="/v1")
    app.include_router(categories_router, prefix="/v1")

    # F4: Mapeo de excepciones de dominio a respuestas HTTP
    register_error_handlers(app)

    return app


app = create_app()
