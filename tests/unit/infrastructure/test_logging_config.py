"""Tests unitarios para el modulo de logging config (SPEC-52).

Verifica JSONFormatter, setup_logging y sus comportamientos.
"""

from __future__ import annotations

import json
import logging

from src.infrastructure.logging.config import JSONFormatter, setup_logging


class TestJSONFormatter:
    """Verifica que JSONFormatter produce JSON valido con los campos esperados."""

    def test_produces_valid_json(self):
        """La salida debe ser un JSON parseable."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Hello %s",
            args=("world",),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert isinstance(parsed, dict)

    def test_includes_required_fields(self):
        """Debe incluir timestamp, level, logger, message, module, line."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["level"] == "WARNING"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Test message"
        assert parsed["module"] == "test"
        assert parsed["line"] == 10
        assert "timestamp" in parsed

    def test_includes_request_id_when_present(self):
        """Debe incluir request_id si existe en el record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="app.request",
            level=logging.INFO,
            pathname="app.py",
            lineno=5,
            msg="Request",
            args=(),
            exc_info=None,
        )
        record.request_id = "abc-123"
        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["request_id"] == "abc-123"

    def test_excludes_request_id_when_absent(self):
        """No debe incluir request_id si no existe en el record."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="app.request",
            level=logging.INFO,
            pathname="app.py",
            lineno=5,
            msg="Request",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert "request_id" not in parsed


class TestSetupLogging:
    """Verifica que setup_logging configura correctamente el logging."""

    def setup_method(self):
        """Limpia handlers entre tests para aislamiento."""
        root = logging.getLogger()
        root.handlers.clear()

    def test_setup_logging_configures_handler(self):
        """Debe configurar al menos un handler en el root logger."""
        setup_logging(log_level="info", log_format="text")
        root = logging.getLogger()

        assert len(root.handlers) > 0

    def test_setup_logging_text_format(self):
        """Con log_format='text' el handler debe usar un formatter de texto."""
        setup_logging(log_level="info", log_format="text")
        root = logging.getLogger()
        handler = root.handlers[0]

        assert not isinstance(handler.formatter, JSONFormatter)

    def test_setup_logging_json_format(self):
        """Con log_format='json' el handler debe usar JSONFormatter."""
        setup_logging(log_level="info", log_format="json")
        root = logging.getLogger()
        handler = root.handlers[0]

        assert isinstance(handler.formatter, JSONFormatter)

    def test_setup_logging_sets_level(self):
        """Debe configurar el nivel de logging correctamente."""
        setup_logging(log_level="debug", log_format="text")
        root = logging.getLogger()

        assert root.level == logging.DEBUG

    def test_silences_third_party_loggers(self):
        """Los loggers de terceros deben estar en WARNING como minimo."""
        setup_logging(log_level="debug", log_format="text")

        assert logging.getLogger("uvicorn.access").level >= logging.WARNING
        assert logging.getLogger("asyncio").level >= logging.WARNING
