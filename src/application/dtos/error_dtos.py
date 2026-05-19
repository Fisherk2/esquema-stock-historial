"""DTOs de error — formato consistente para respuestas de error."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detalle de un error de API.

    Ejemplo::

        {
            "code": "INSUFFICIENT_STOCK",
            "message": "Insufficient stock for product 1: requested 10, available 3",
            "details": {"product_id": 1, "requested": 10, "available": 3}
        }
    """

    code: str = Field(
        description="Codigo de error machine-readable (UPPER_SNAKE_CASE)."
    )
    message: str = Field(description="Mensaje legible para humanos.")
    details: dict[str, str | int | float] | None = Field(
        default=None,
        description="Contexto adicional del error (opcional).",
    )


class ErrorResponse(BaseModel):
    """Envoltura de respuesta de error.

    Todos los endpoints retornan este formato en caso de error.

    Ejemplo::

        {
            "error": {
                "code": "NOT_FOUND",
                "message": "Product 999 not found"
            }
        }
    """

    error: ErrorDetail = Field(description="Detalle del error.")
