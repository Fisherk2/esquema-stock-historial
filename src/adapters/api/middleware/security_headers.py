"""Security headers middleware.

Agrega cabeceras de seguridad HTTP a todas las respuestas para
reforzar la defensa en profundidad.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware que agrega cabeceras de seguridad a cada respuesta.

    Cabeceras aplicadas:
        - X-Content-Type-Options: nosniff
        - X-Frame-Options: DENY
        - Cache-Control: no-store (API responses no deben cachearse)
        - Referrer-Policy: strict-origin-when-cross-origin
    """

    async def dispatch(self, request, call_next) -> Response:  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response
