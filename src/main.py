from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.adapters.api.routers.health import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Stock Historial",
        description="Sistema de gestión de inventario con Source of Truth Inmutable",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health_router, prefix="/v1")

    return app


app = create_app()
