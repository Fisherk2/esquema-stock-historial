"""Tests unitarios para QueryStockAtDateUseCase."""
from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

from src.application.use_cases.query_stock_at_date import QueryStockAtDateUseCase


class TestQueryStockAtDateUseCase:
    """Tests para QueryStockAtDateUseCase."""

    async def test_returns_stock_at_date(self) -> None:
        """Verifica que retorna el stock en la fecha dada."""
        stock_repo = AsyncMock()
        stock_repo.get_stock_at_date = AsyncMock(return_value=15.0)

        use_case = QueryStockAtDateUseCase(stock_repo)
        target_date = datetime(2025, 1, 1, tzinfo=UTC)
        result = await use_case.execute(product_id=1, date=target_date)

        assert result == 15.0
        stock_repo.get_stock_at_date.assert_awaited_once_with(1, target_date)

    async def test_returns_zero_for_no_movements(self) -> None:
        """Verifica que retorna 0 si no hay movimientos anteriores."""
        stock_repo = AsyncMock()
        stock_repo.get_stock_at_date = AsyncMock(return_value=0.0)

        use_case = QueryStockAtDateUseCase(stock_repo)
        target_date = datetime(2020, 1, 1, tzinfo=UTC)
        result = await use_case.execute(product_id=999, date=target_date)

        assert result == 0.0
