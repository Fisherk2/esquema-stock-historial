"""Tests unitarios para el decorador retry_with_backoff (SPEC-51).

Verifica el comportamiento del decorador: reintentos con backoff
exponencial, manejo de excepciones, logging y fallo final.
"""

from __future__ import annotations

import logging

import pytest

from src.core.retry import retry_with_backoff
from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError


class TestRetryWithBackoffSuccess:
    """Tests para el caso de exito (sin reintentos)."""

    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self):
        """Si la funcion no falla, no debe reintentar."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.001,
            jitter=0.0,
            exceptions=(ConcurrencyConflictError,),
        )
        async def always_succeeds():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = await always_succeeds()

        assert result == "ok"
        assert call_count == 1


class TestRetryWithBackoffRetries:
    """Tests para el caso de reintentos."""

    @pytest.mark.asyncio
    async def test_retries_on_configured_exception(self):
        """Debe reintentar cuando se lanza una excepcion configurada."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.001,
            jitter=0.0,
            exceptions=(ConcurrencyConflictError,),
        )
        async def fails_twice_then_succeeds():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConcurrencyConflictError("test")
            return "ok"

        result = await fails_twice_then_succeeds()

        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_fails_after_max_retries(self):
        """Debe propagar la excepcion tras agotar los reintentos."""
        call_count = 0

        @retry_with_backoff(
            max_retries=2,
            base_delay=0.001,
            jitter=0.0,
            exceptions=(ConcurrencyConflictError,),
        )
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConcurrencyConflictError("test")

        with pytest.raises(ConcurrencyConflictError):
            await always_fails()

        # Intento inicial + max_retries intentos = 3 llamadas
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_unconfigured_exceptions(self):
        """No debe reintentar excepciones no configuradas."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.001,
            jitter=0.0,
            exceptions=(ConcurrencyConflictError,),
        )
        async def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await raises_value_error()

        assert call_count == 1


class TestRetryWithBackoffLogging:
    """Tests para verificar el logging de reintentos."""

    @pytest.mark.asyncio
    async def test_logs_warning_on_retry(self, caplog):
        """Cada reintento debe registrarse con nivel WARNING."""
        call_count = 0

        @retry_with_backoff(
            max_retries=2,
            base_delay=0.001,
            jitter=0.0,
            exceptions=(ConcurrencyConflictError,),
        )
        async def fails_once():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConcurrencyConflictError("test")
            return "ok"

        with caplog.at_level(logging.WARNING):
            await fails_once()

        # Al menos un WARNING por el reintento
        warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_records) >= 1

    @pytest.mark.asyncio
    async def test_logs_error_on_final_failure(self, caplog):
        """El fallo final debe registrarse con nivel ERROR."""

        @retry_with_backoff(
            max_retries=1,
            base_delay=0.001,
            jitter=0.0,
            exceptions=(ConcurrencyConflictError,),
        )
        async def always_fails():
            raise ConcurrencyConflictError("fatal")

        with caplog.at_level(logging.ERROR), pytest.raises(ConcurrencyConflictError):
            await always_fails()

        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) >= 1


class TestRetryWithBackoffMultipleExceptions:
    """Tests para multiples tipos de excepciones configurables."""

    @pytest.mark.asyncio
    async def test_retries_on_any_configured_exception(self):
        """Debe reintentar cualquiera de las excepciones configuradas."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay=0.001,
            jitter=0.0,
            exceptions=(ValueError, TypeError),
        )
        async def fails_with_different_errors():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("first")
            if call_count == 2:
                raise TypeError("second")
            return "ok"

        result = await fails_with_different_errors()

        assert result == "ok"
        assert call_count == 3
