"""Tests para DTOs de stock."""
from __future__ import annotations

from datetime import UTC, datetime

from src.application.dtos.stock_dtos import CurrentStockOutput, StockAtDateOutput


class TestCurrentStockOutput:
    """Tests para CurrentStockOutput."""

    def test_serializes(self) -> None:
        """Verifica serializacion."""
        output = CurrentStockOutput(product_id=1, current_stock=42.5)
        assert output.product_id == 1
        assert output.current_stock == 42.5


class TestStockAtDateOutput:
    """Tests para StockAtDateOutput."""

    def test_serializes(self) -> None:
        """Verifica serializacion."""
        target_date = datetime(2025, 1, 1, tzinfo=UTC)
        output = StockAtDateOutput(product_id=1, stock=15.0, date=target_date)
        assert output.product_id == 1
        assert output.stock == 15.0
        assert output.date == target_date
