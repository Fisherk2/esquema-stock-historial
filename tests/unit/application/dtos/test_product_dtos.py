"""Tests para DTOs de productos."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.application.dtos.product_dtos import (
    CreateProductInput,
    ProductListOutput,
    ProductOutput,
)


class TestCreateProductInput:
    """Tests para CreateProductInput."""

    def test_valid_product_input(self) -> None:
        """Verifica que crea un input valido."""
        body = CreateProductInput(
            sku="PROD-001",
            name="Widget",
            unit_of_measure="unit",
            category_id=1,
        )
        assert body.sku == "PROD-001"
        assert body.name == "Widget"

    def test_rejects_invalid_sku(self) -> None:
        """Verifica que rechaza SKU con caracteres invalidos."""
        with pytest.raises(ValidationError):
            CreateProductInput(
                sku="PROD@001",
                name="Widget",
                unit_of_measure="unit",
                category_id=1,
            )

    def test_rejects_empty_name(self) -> None:
        """Verifica que rechaza nombre vacio."""
        with pytest.raises(ValidationError):
            CreateProductInput(
                sku="PROD-001",
                name="",
                unit_of_measure="unit",
                category_id=1,
            )

    def test_rejects_zero_category_id(self) -> None:
        """Verifica que rechaza category_id=0."""
        with pytest.raises(ValidationError):
            CreateProductInput(
                sku="PROD-001",
                name="Widget",
                unit_of_measure="unit",
                category_id=0,
            )

    def test_rejects_negative_threshold(self) -> None:
        """Verifica que rechaza min_stock_threshold negativo."""
        with pytest.raises(ValidationError):
            CreateProductInput(
                sku="PROD-001",
                name="Widget",
                unit_of_measure="unit",
                category_id=1,
                min_stock_threshold=-1,
            )


class TestProductOutput:
    """Tests para ProductOutput."""

    def test_serializes_to_json(self) -> None:
        """Verifica serializacion JSON."""
        output = ProductOutput(
            id=1,
            sku="PROD-001",
            name="Widget",
            description=None,
            unit_of_measure="unit",
            category_id=1,
            min_stock_threshold=10,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        json_str = output.model_dump_json()
        assert '"sku":"PROD-001"' in json_str


class TestProductListOutput:
    """Tests para ProductListOutput."""

    def test_contains_pagination(self) -> None:
        """Verifica campos de paginacion."""
        output = ProductListOutput(items=[], total=50, limit=25, offset=0)
        assert output.total == 50
        assert output.limit == 25
