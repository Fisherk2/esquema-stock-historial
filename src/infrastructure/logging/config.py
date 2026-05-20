"""Configuracion de logging estructurado.

Configura los handlers, formatters y niveles de log de la aplicacion.
En desarrollo usa formato legible con colores; en produccion usa
formato JSON para parseo automatico por herramientas de monitoreo.

Ejemplo::

    from src.infrastructure.logging.config import setup_logging

    setup_logging(log_level="info", log_format="json")
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    """Formatter que produce JSON para cada log entry."""

    def format(self, record: logging.LogRecord) -> str:
        """Formatea un LogRecord como JSON con campos estandarizados.

        Args:
            record: El registro de log a formatear.

        Returns:
            Cadena JSON con timestamp, level, logger, message y extras.
        """
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Anadir request_id si existe en el record
        if hasattr(record, "request_id"):
            log_entry["request_id"] = record.request_id

        # Anadir exception info si existe
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(
    log_level: str = "info",
    log_format: str = "text",
) -> None:
    """Configura el logging de la aplicacion.

    Configura el handler de stdout con el formato especificado
    y silencia los loggers verbosos de terceros.

    Args:
        log_level: Nivel de logging (debug, info, warning, error).
        log_format: Formato de salida ("text" o "json").
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Handler: stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    if log_format == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    # Root logger
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    # Silenciar loggers verbosos de terceros
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
