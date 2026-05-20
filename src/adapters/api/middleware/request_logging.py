"""Middleware de logging de requests.

Genera un ``request_id`` unico por request HTTP y lo propaga
a todos los logs del request via ``contextvars``. Loggea el
inicio y fin de cada request con metodo, path, status code y
duracion.

Ejemplo::

    from src.adapters.api.middleware.request_logging import RequestLoggingMiddleware

    app.add_middleware(RequestLoggingMiddleware)
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from typing import TYPE_CHECKING, ClassVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

if TYPE_CHECKING:
    from starlette.requests import Request
    from starlette.responses import Response

logger = logging.getLogger(__name__)

# Request ID propagado via contextvar para correlacion de logs
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware que loggea cada request con request_id y duracion.

    Excluye rutas de health check para reducir ruido en logs.
    """

    EXCLUDED_PATHS: ClassVar[set[str]] = {"/v1/health", "/health"}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """Procesa el request con logging y request_id.

        Args:
            request: El request HTTP entrante.
            call_next: La siguiente funcion en la cadena de middleware.

        Returns:
            La respuesta HTTP del endpoint con X-Request-ID header.
        """
        # Excluir health checks del logging
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        start_time = time.monotonic()
        req_id = str(uuid.uuid4())
        request_id_ctx.set(req_id)

        # Log request start
        logger.info(
            "Request started: %s %s",
            request.method,
            request.url.path,
            extra={"request_id": req_id},
        )

        response = await call_next(request)

        # Log request end with duration
        duration_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "Request completed: %s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={"request_id": req_id},
        )

        # Anadir request_id a los headers de respuesta para debugging
        response.headers["X-Request-ID"] = req_id

        return response


def get_request_id() -> str | None:
    """Obtiene el request_id actual del contexto.

    Returns:
        El request_id del request actual, o None si no hay request.
    """
    return request_id_ctx.get()
