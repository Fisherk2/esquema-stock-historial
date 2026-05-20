"""Tests unitarios para la configuración del scheduler (SPEC-50)."""

from __future__ import annotations

from src.core.config import Settings


class TestSchedulerSettings:
    """Verifica campos de configuración del scheduler (SPEC-50)."""

    def test_scheduler_enabled_default_is_true(self):
        """El scheduler debe estar habilitado por defecto."""
        settings = Settings()
        assert settings.scheduler_enabled is True

    def test_scheduler_refresh_interval_minutes_default_is_5(self):
        """El intervalo de refresh por defecto debe ser 5 minutos."""
        settings = Settings()
        assert settings.scheduler_refresh_interval_minutes == 5

    def test_scheduler_misfire_grace_time_seconds_default_is_60(self):
        """El misfire grace time por defecto debe ser 60 segundos."""
        settings = Settings()
        assert settings.scheduler_misfire_grace_time_seconds == 60

    def test_scheduler_statement_timeout_seconds_default_is_30(self):
        """El statement timeout para refresh por defecto debe ser 30 segundos."""
        settings = Settings()
        assert settings.scheduler_statement_timeout_seconds == 30

    def test_scheduler_settings_can_be_overridden_via_env(self, monkeypatch):
        """Los campos del scheduler deben sobreescribirse via variables de entorno."""
        monkeypatch.setenv("SCHEDULER_ENABLED", "false")
        monkeypatch.setenv("SCHEDULER_REFRESH_INTERVAL_MINUTES", "10")
        monkeypatch.setenv("SCHEDULER_MISFIRE_GRACE_TIME_SECONDS", "120")
        monkeypatch.setenv("SCHEDULER_STATEMENT_TIMEOUT_SECONDS", "60")

        settings = Settings()

        assert settings.scheduler_enabled is False
        assert settings.scheduler_refresh_interval_minutes == 10
        assert settings.scheduler_misfire_grace_time_seconds == 120
        assert settings.scheduler_statement_timeout_seconds == 60
