"""Tests unitarios para el modulo del scheduler (SPEC-50)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.infrastructure.scheduler.scheduler import (
    create_scheduler,
    shutdown_scheduler,
    start_scheduler,
)


class TestCreateScheduler:
    """Verifica que create_scheduler configura el AsyncIOScheduler correctamente."""

    def test_create_scheduler_registers_job(self):
        """El scheduler debe registrar un job con id 'refresh_stock_view'."""
        pool = MagicMock()
        scheduler = create_scheduler(
            pool,
            refresh_interval_minutes=10,
            misfire_grace_time=30,
            statement_timeout=45,
        )

        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        job = jobs[0]
        assert job.id == "refresh_stock_view"
        assert job.max_instances == 1

    def test_create_scheduler_job_has_correct_trigger(self):
        """El job debe usar un trigger de intervalo con los minutos configurados."""
        pool = MagicMock()
        scheduler = create_scheduler(pool, refresh_interval_minutes=7)

        jobs = scheduler.get_jobs()
        assert len(jobs) == 1
        job = jobs[0]
        # Verificar que el trigger es de tipo interval
        assert job.trigger is not None
        assert "interval" in str(job.trigger).lower()


class TestStartScheduler:
    """Verifica que start_scheduler arranca o no el scheduler según enabled."""

    @pytest.mark.asyncio
    async def test_start_scheduler_disabled_does_not_create_scheduler(self):
        """Con enabled=False, no se debe crear ningun scheduler."""
        pool = MagicMock()
        await start_scheduler(pool, enabled=False)

        from src.infrastructure.scheduler.scheduler import _scheduler

        assert _scheduler is None

    @pytest.mark.asyncio
    async def test_start_scheduler_enabled_creates_and_starts_scheduler(self):
        """Con enabled=True, se debe crear y arrancar el scheduler."""
        pool = MagicMock()
        await start_scheduler(pool, enabled=True, refresh_interval_minutes=1)

        from src.infrastructure.scheduler.scheduler import _scheduler

        assert _scheduler is not None
        assert _scheduler.running is True

        # Cleanup
        await shutdown_scheduler()


class TestShutdownScheduler:
    """Verifica que shutdown_scheduler detiene el scheduler gracefulmente."""

    @pytest.mark.asyncio
    async def test_shutdown_scheduler_stops_running_scheduler(self):
        """shutdown_scheduler debe detener un scheduler en ejecución."""
        pool = MagicMock()
        await start_scheduler(pool, enabled=True)

        from src.infrastructure.scheduler.scheduler import _scheduler

        assert _scheduler is not None
        assert _scheduler.running is True

        await shutdown_scheduler()

        # Después de shutdown, el modulo debe ser None
        from src.infrastructure.scheduler.scheduler import _scheduler as post_shutdown

        assert post_shutdown is None

    @pytest.mark.asyncio
    async def test_shutdown_scheduler_when_none_does_not_raise(self):
        """shutdown_scheduler no debe fallar si no hay scheduler."""
        # Asegurar que no hay scheduler previo
        from src.infrastructure.scheduler.scheduler import _scheduler

        assert _scheduler is None

        # No debe lanzar excepcion
        await shutdown_scheduler()
