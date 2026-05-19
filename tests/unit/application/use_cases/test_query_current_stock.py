"""Tests unitarios para QueryCurrentStockUseCase."""
from __future__ import annotations

from unittest.mock import AsyncMock

from src.application.use_cases.query_current_stock import QueryCurrentStockUseCase


class TestQueryCurrentStockUseCase:
    """Tests para QueryCurrentStockUseCase."""

    async def test_returns_stock_value(self) -> None:
        """Verifica que retorna el valor del repositorio."""
        stock_repo = AsyncMock()
        stock_repo.get_current_stock = AsyncMock(return_value=42.5)

        use_case = QueryCurrentStockUseCase(stock_repo)
        result = await use_case.execute(product_id=1)

        assert result == 42.5
        stock_repo.get_current_stock.assert_awaited_once_with(1)

    async def test_returns_zero_for_no_movements(self) -> None:
        """Verifica que retorna 0 si no hay movimientos."""
        stock_repo = AsyncMock()
        stock_repo.get_current_stock = AsyncMock(return_value=0.0)

        use_case = QueryCurrentStockUseCase(stock_repo)
        result = await use_case.execute(product_id=999)

        assert result == 0.0
