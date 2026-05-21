"""Tests unitarios para la configuracion centralizada (Settings)."""

from __future__ import annotations

import pytest

from src.core.config import Settings

VALID_URL = "postgresql+asyncpg://user:pass@localhost:5432/testdb"


class TestSettingsDatabaseUrlRequired:
    """Verifica que DATABASE_URL sea requerida y fail-fast al startup."""

    def test_raises_when_database_url_is_empty(self):
        """Settings() sin DATABASE_URL debe elevar ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Settings(database_url="")

        assert "DATABASE_URL is required" in str(exc_info.value)

    def test_raises_when_database_url_not_set(self, monkeypatch):
        """Sin env var ni .env, DATABASE_URL es empty string → ValueError."""
        # Asegurar que ninguna variable de entorno interfiera
        monkeypatch.delenv("DATABASE_URL", raising=False)
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

        with pytest.raises(ValueError) as exc_info:
            Settings(_env_file=None, database_url="")

        assert "DATABASE_URL is required" in str(exc_info.value)

    def test_accepts_valid_database_url(self):
        """DATABASE_URL con DSN valido debe crear Settings sin error."""
        settings = Settings(database_url=VALID_URL)
        assert settings.database_url == VALID_URL

    def test_accepts_valid_database_url_via_env(self, monkeypatch):
        """DATABASE_URL via variable de entorno debe ser leida correctamente."""
        monkeypatch.setenv("DATABASE_URL", VALID_URL)
        settings = Settings()
        assert settings.database_url == VALID_URL

    def test_error_message_includes_example(self):
        """El mensaje de error debe incluir un ejemplo de DSN."""
        with pytest.raises(ValueError) as exc_info:
            Settings(database_url="")

        assert "postgresql+asyncpg://" in str(exc_info.value)

    def test_other_defaults_unchanged(self):
        """Los demas defaults deben permanecer intactos con URL valida."""
        settings = Settings(database_url=VALID_URL)
        assert settings.app_name == "Stock Historial"
        assert settings.app_host == "0.0.0.0"
        assert settings.app_port == 8000
        assert settings.log_level == "info"
        assert settings.environment == "development"
        assert settings.scheduler_enabled is True
