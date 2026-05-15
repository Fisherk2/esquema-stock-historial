from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Stock Historial"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"
    environment: str = "development"
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/stock_historial"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
