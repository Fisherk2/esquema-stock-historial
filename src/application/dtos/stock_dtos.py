"""DTOs de stock — output para consultas actuales e historicas."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003 — Pydantic needs runtime datetime

from pydantic import BaseModel, Field


class CurrentStockOutput(BaseModel):
    """Stock actual de un producto.

    Ejemplo::

        {
            "product_id": 1,
            "current_stock": 42.0
        }
    """

    product_id: int = Field(description="ID del producto.")
    current_stock: float = Field(description="Stock actual (puede ser decimal).")


class StockAtDateOutput(BaseModel):
    """Stock de un producto en una fecha historica.

    Ejemplo::

        {
            "product_id": 1,
            "stock": 15.0,
            "date": "2025-01-01T00:00:00Z"
        }
    """

    product_id: int = Field(description="ID del producto.")
    stock: float = Field(description="Stock en la fecha especificada.")
    date: datetime = Field(description="Fecha de consulta.")
