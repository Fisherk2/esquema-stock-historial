"""Tests unitarios para la configuracion de logging (SPEC-52)."""

from __future__ import annotations

from src.core.config import Settings


class TestLoggingSettings:
    """Verifica campos de configuracion de logging y timeout de API."""

    def test_log_format_default_is_text(self):
        """El formato de log por defecto debe ser 'text'."""
        settings = Settings()
        assert settings.log_format == "text"

    def test_api_statement_timeout_seconds_default_is_5(self):
        """El statement timeout de API por defecto debe ser 5 segundos."""
        settings = Settings()
        assert settings.api_statement_timeout_seconds == 5

    def test_logging_settings_can_be_overridden_via_env(self, monkeypatch):
        """Los campos deben poder sobreescribirse via variables de entorno."""
        monkeypatch.setenv("LOG_FORMAT", "json")
        monkeypatch.setenv("API_STATEMENT_TIMEOUT_SECONDS", "10")

        settings = Settings()

        assert settings.log_format == "json"
        assert settings.api_statement_timeout_seconds == 10
