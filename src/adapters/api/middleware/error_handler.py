"""Mapeo de excepciones de dominio a respuestas HTTP.

Registra handlers de excepcion en la app FastAPI para capturar errores
del dominio y convertirlos en respuestas JSON estructuradas.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from src.application.dtos.error_dtos import ErrorDetail, ErrorResponse
from src.domain.exceptions.category_not_found import CategoryNotFoundError
from src.domain.exceptions.concurrency_conflict import ConcurrencyConflictError
from src.domain.exceptions.domain_error import DomainError
from src.domain.exceptions.immutability_violation import ImmutabilityViolationError
from src.domain.exceptions.insufficient_stock import InsufficientStockError
from src.domain.exceptions.invalid_quantity import InvalidQuantityError
from src.domain.exceptions.invalid_sku import InvalidSKUError
from src.domain.exceptions.product_not_found import ProductNotFoundError

if TYPE_CHECKING:
    import asyncpg
    from fastapi import FastAPI, Request


def register_error_handlers(app: FastAPI) -> None:
    """Registra los handlers de excepcion en la app FastAPI.

    Args:
        app: Instancia de FastAPI donde registrar los handlers.
    """

    @app.exception_handler(InsufficientStockError)
    async def handle_insufficient_stock(
        request: Request, exc: InsufficientStockError
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
    async def handle_invalid_sku(
        request: Request, exc: InvalidSKUError
    ) -> JSONResponse:
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
        request: Request, exc: InvalidQuantityError
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
        request: Request, exc: ImmutabilityViolationError
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

    @app.exception_handler(ConcurrencyConflictError)
    async def handle_concurrency_conflict(
        request: Request, exc: ConcurrencyConflictError
    ) -> JSONResponse:
        """Mapea ConcurrencyConflictError a HTTP 409 Conflict."""
        details: dict[str, str | int] = {"operation": exc.operation}
        if exc.detail is not None:
            details["detail"] = exc.detail

        return JSONResponse(
            status_code=409,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="CONCURRENCY_CONFLICT",
                    message=str(exc),
                    details=details,
                )
            ).model_dump(),
        )

    @app.exception_handler(ProductNotFoundError)
    async def handle_product_not_found(
        request: Request, exc: ProductNotFoundError
    ) -> JSONResponse:
        """Mapea ProductNotFoundError a HTTP 400 Bad Request."""
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="PRODUCT_NOT_FOUND",
                    message=str(exc),
                    details={"product_id": exc.product_id},
                )
            ).model_dump(),
        )

    @app.exception_handler(CategoryNotFoundError)
    async def handle_category_not_found(
        request: Request, exc: CategoryNotFoundError
    ) -> JSONResponse:
        """Mapea CategoryNotFoundError a HTTP 400 Bad Request."""
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="CATEGORY_NOT_FOUND",
                    message=str(exc),
                    details={"category_id": exc.category_id},
                )
            ).model_dump(),
        )

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
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
    async def handle_value_error(
        request: Request, exc: ValueError
    ) -> JSONResponse:
        """Mapea ValueError a HTTP 400 Bad Request.

        Solo captura errores de validacion de input (metadata inconsistente
        en DTOs, domain value objects). Errores internos de programacion
        se delegan al handler de Exception (HTTP 500).
        """
        _validation_modules = (
            "src/application/dtos",
            "src/domain/value_objects",
            "src/domain/entities",
            "src/domain/rules",
        )
        is_validation_error = False
        if exc.__traceback__:
            tb = exc.__traceback__
            while tb is not None:
                fname = tb.tb_frame.f_code.co_filename
                if any(mod in fname for mod in _validation_modules):
                    is_validation_error = True
                    break
                tb = tb.tb_next

        if not is_validation_error:
            # Error interno de programacion — no enmascarar como 400
            raise exc

        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=str(exc),
                )
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """Mapea cualquier excepcion no manejada a HTTP 500.

        Captura errores de infraestructura (asyncpg, etc.) que no tienen
        handlers especificos. Nunca expone stack traces ni detalles internos.
        """
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An unexpected error occurred.",
                )
            ).model_dump(),
        )

    import asyncpg

    @app.exception_handler(asyncpg.DataError)
    async def handle_asyncpg_data_error(
        request: Request, exc: asyncpg.DataError
    ) -> JSONResponse:
        """Mapea asyncpg.DataError a HTTP 500.

        Captura errores de codificacion de datos (overflow, encoding)
        que ocurren en el nivel de protocolo asyncpg.
        """
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An unexpected error occurred.",
                )
            ).model_dump(),
        )

    @app.exception_handler(asyncpg.PostgresError)
    async def handle_asyncpg_postgres_error(
        request: Request, exc: asyncpg.PostgresError
    ) -> JSONResponse:
        """Mapea asyncpg.PostgresError a HTTP 500.

        Captura todos los errores de PostgreSQL (FK violations, null bytes,
        etc.) que no tienen handlers especificos.
        """
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An unexpected error occurred.",
                )
            ).model_dump(),
        )
