"""Configuración centralizada del sistema.

Centraliza todas las variables de entorno y valores por defecto mediante
pydantic-settings. Sigue el principio SRP: una sola responsabilidad
(configuración), sin mezclar lógica de negocio ni infraestructura.

Los valores se resuelven en este orden: variables de entorno > archivo .env >
valores por defecto en la clase.

Ejemplo::

    from src.core.config import Settings

    settings = Settings()  # lee .env automáticamente
    print(settings.database_url)
"""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Variables de configuración de la aplicación.

    Cada campo se mapea a una variable de entorno en MAYÚSCULAS
    (ej: ``app_name`` → ``APP_NAME``).

    Attributes:
        app_name: Nombre de la aplicación para logs y metadata.
        app_host: Interfaz de red donde escucha el servidor (0.0.0.0 para Docker).
        app_port: Puerto de escucha del servidor HTTP.
        log_level: Nivel de logging (debug, info, warning, error).
        environment: Entorno de ejecución (development, staging, production).
        database_url: DSN de conexión asyncpg a PostgreSQL.

    Ejemplo de uso con archivo .env::

        # .env
        APP_NAME=Mi App
        APP_PORT=9000
        DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

        settings = Settings()
        settings.app_port  # 9000 (sobreescribe el default 8000)
    """

    app_name: str = "Stock Historial"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"
    environment: str = "development"
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/stock_historial"
    )

    # F5: Scheduler settings
    scheduler_enabled: bool = True
    scheduler_refresh_interval_minutes: int = 5
    scheduler_misfire_grace_time_seconds: int = 60
    scheduler_statement_timeout_seconds: int = 30

    # F5: Logging settings
    log_format: str = "text"
    api_statement_timeout_seconds: int = 5

    # F7: Docker Compose Prod (solo para docker-compose, no usadas directamente por la app)
    postgres_user: str = "stock_user"
    postgres_password: str = ""
    postgres_db: str = "stock_historial"

    # F7: Demo Script
    demo_base_url: str = "http://localhost:8000"

    # Estrategia de carga: .env → env vars del sistema → defaults de la clase
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}
