"""Tests para DTOs de categorias."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.application.dtos.category_dtos import (
    CategoryOutput,
    CreateCategoryInput,
)


class TestCreateCategoryInput:
    """Tests para CreateCategoryInput."""

    def test_valid_input(self) -> None:
        """Verifica input valido."""
        body = CreateCategoryInput(
            name="Electronics",
            description="Electronic products",
        )
        assert body.name == "Electronics"

    def test_rejects_empty_name(self) -> None:
        """Verifica que rechaza nombre vacio."""
        with pytest.raises(ValidationError):
            CreateCategoryInput(name="")

    def test_optional_description(self) -> None:
        """Verifica que description es opcional."""
        body = CreateCategoryInput(name="Electronics")
        assert body.description is None


class TestCategoryOutput:
    """Tests para CategoryOutput."""

    def test_serializes(self) -> None:
        """Verifica serializacion."""
        from datetime import UTC, datetime

        output = CategoryOutput(
            id=1,
            name="Electronics",
            description=None,
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
        )
        assert output.id == 1
        assert output.name == "Electronics"
