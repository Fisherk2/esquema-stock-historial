"""Mapeo de excepciones de dominio a respuestas HTTP.

Registra handlers de excepcion en la app FastAPI para capturar errores
del dominio y convertirlos en respuestas JSON estructuradas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from src.application.dtos.error_dtos import ErrorDetail, ErrorResponse
from src.domain.exceptions.domain_error import DomainError
from src.domain.exceptions.immutability_violation import ImmutabilityViolationError
from src.domain.exceptions.insufficient_stock import InsufficientStockError

if TYPE_CHECKING:
    from fastapi import FastAPI
from src.domain.exceptions.invalid_quantity import InvalidQuantityError
from src.domain.exceptions.invalid_sku import InvalidSKUError


def register_error_handlers(app: FastAPI) -> None:
    """Registra los handlers de excepcion en la app FastAPI.

    Args:
        app: Instancia de FastAPI donde registrar los handlers.
    """

    @app.exception_handler(InsufficientStockError)
    async def handle_insufficient_stock(
        request, exc: InsufficientStockError
    ) -> JSONResponse:
        """Mapea InsufficientStockError a HTTP 409 Conflict."""
        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INSUFFICIENT_STOCK",
                    message=str(exc),
                    details={
                        "product_id": exc.product_id,
                        "requested": exc.requested,
                        "available": exc.available,
                    },
                )
            ).model_dump(),
        )

    @app.exception_handler(InvalidSKUError)
    async def handle_invalid_sku(request, exc: InvalidSKUError) -> JSONResponse:
        """Mapea InvalidSKUError a HTTP 422 Unprocessable Entity."""
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_SKU",
                    message=str(exc),
                )
            ).model_dump(),
        )

    @app.exception_handler(InvalidQuantityError)
    async def handle_invalid_quantity(
        request, exc: InvalidQuantityError
    ) -> JSONResponse:
        """Mapea InvalidQuantityError a HTTP 422 Unprocessable Entity."""
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_QUANTITY",
                    message=str(exc),
                )
            ).model_dump(),
        )

    @app.exception_handler(ImmutabilityViolationError)
    async def handle_immutability_violation(
        request, exc: ImmutabilityViolationError
    ) -> JSONResponse:
        """Mapea ImmutabilityViolationError a HTTP 403 Forbidden."""
        return JSONResponse(
            status_code=403,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="IMMUTABILITY_VIOLATION",
                    message=str(exc),
                )
            ).model_dump(),
        )

    @app.exception_handler(DomainError)
    async def handle_domain_error(request, exc: DomainError) -> JSONResponse:
        """Mapea DomainError (base) a HTTP 500 Internal Server Error.

        Este handler captura cualquier DomainError no manejado por los
        handlers especificos de arriba (fall-through).
        """
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="DOMAIN_ERROR",
                    message=str(exc),
                )
            ).model_dump(),
        )

    @app.exception_handler(ValueError)
    async def handle_value_error(request, exc: ValueError) -> JSONResponse:
        """Mapea ValueError a HTTP 400 Bad Request.

        Se usa para errores de validacion de input (metadata inconsistente,
        producto/categoria no encontrado, etc.).
        """
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=str(exc),
                )
            ).model_dump(),
        )
