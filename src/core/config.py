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

from pydantic import model_validator
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
        database_url: DSN de conexión asyncpg a PostgreSQL. REQUERIDO — la app
            falla al startup si no está configurado.

    Note:
        Los campos ``postgres_user``, ``postgres_password``, ``postgres_db``
        y ``demo_base_url`` NO son leídos por la aplicación — solo sirven
        como fuente de variables de entorno para ``docker-compose.prod.yml``
        y ``scripts/demo.sh``.
    """

    app_name: str = "Stock Historial"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "info"
    environment: str = "development"
    database_url: str = ""

    # F5: Scheduler settings
    scheduler_enabled: bool = True
    scheduler_refresh_interval_minutes: int = 5
    scheduler_misfire_grace_time_seconds: int = 60
    scheduler_statement_timeout_seconds: int = 30

    # F5: Logging settings
    log_format: str = "text"
    api_statement_timeout_seconds: int = 5

    # F3: Database pool settings
    db_pool_min_size: int = 2
    db_pool_max_size: int = 10

    # F7: Docker Compose Prod — SOLO usadas por docker-compose.prod.yml
    # (inyectadas como env vars al contenedor, no leídas por la app)
    postgres_user: str = "stock_user"
    postgres_password: str = ""  # docker-compose.prod.yml → POSTGRES_PASSWORD
    postgres_db: str = "stock_historial"  # docker-compose.prod.yml → POSTGRES_DB

    # F7: Demo Script — SOLO usada por scripts/demo.sh (no por la app)
    demo_base_url: str = "http://localhost:8000"

    # Estrategia de carga: .env → env vars del sistema → defaults de la clase
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @model_validator(mode="after")
    def _validate_database_url(self) -> Settings:
        """Valida que DATABASE_URL esté configurada."""
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL is required. "
                "Set it via environment variable or .env file. "
                "Example: postgresql+asyncpg://user:pass@host:5432/dbname"
            )
        return self
