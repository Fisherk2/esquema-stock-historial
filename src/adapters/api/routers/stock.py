"""Router de stock — consultas de stock actual e historico.

Endpoints:
    GET    /v1/stock/{product_id}/current        — Stock actual
    GET    /v1/stock/{product_id}/at-date        — Stock en una fecha
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.adapters.api.dependencies import (
    get_query_current_stock_use_case,
    get_query_stock_at_date_use_case,
)
from src.application.dtos.stock_dtos import CurrentStockOutput, StockAtDateOutput
from src.application.use_cases.query_current_stock import QueryCurrentStockUseCase
from src.application.use_cases.query_stock_at_date import QueryStockAtDateUseCase

router = APIRouter(prefix="/stock", tags=["stock"])


def _ensure_timezone_aware(dt: datetime) -> datetime:
    """Asegura que el datetime tenga zona horaria (UTC por defecto).

    FastAPI parsea datetimes naive si el cliente no envia timezone.
    Como la DB usa TIMESTAMPTZ, un datetime naive podria producir
    resultados incorrectos dependiendo del timezone del servidor.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


@router.get(
    "/{product_id}/current",
    response_model=CurrentStockOutput,
    summary="Consultar stock actual",
    description="Obtiene el stock actual de un producto usando la vista "
    "materializada (con fallback a calculo directo).",
)
async def get_current_stock(
    product_id: int,
    use_case: Annotated[
        QueryCurrentStockUseCase, Depends(get_query_current_stock_use_case)
    ],
) -> CurrentStockOutput:
    """Obtiene el stock actual de un producto."""
    stock = await use_case.execute(product_id)
    return CurrentStockOutput(product_id=product_id, current_stock=stock)


@router.get(
    "/{product_id}/at-date",
    response_model=StockAtDateOutput,
    summary="Consultar stock historico",
    description="Calcula el stock de un producto en una fecha especifica "
    "usando calculo directo sobre la tabla de movimientos.",
)
async def get_stock_at_date(
    product_id: int,
    use_case: Annotated[
        QueryStockAtDateUseCase, Depends(get_query_stock_at_date_use_case)
    ],
    date: datetime = Query(
        description="Fecha de consulta (timezone-aware, ISO 8601). "
        "Ej: 2025-01-01T00:00:00Z",
    ),
) -> StockAtDateOutput:
    """Obtiene el stock de un producto en una fecha."""
    date_tz = _ensure_timezone_aware(date)
    stock = await use_case.execute(product_id, date_tz)
    return StockAtDateOutput(product_id=product_id, stock=stock, date=date_tz)
