"""Tests unitarios para CreateProductUseCase."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.use_cases.create_product import CreateProductUseCase
from src.domain.exceptions.invalid_sku import InvalidSKUError


class TestCreateProductUseCase:
    """Tests para CreateProductUseCase."""

    async def test_creates_product_with_valid_category(self) -> None:
        """Verifica que crea un producto cuando la categoria existe."""
        category_repo = AsyncMock()
        category_repo.get_by_id = AsyncMock(return_value=MagicMock())
        product_repo = AsyncMock()
        product_repo.create = AsyncMock(return_value=MagicMock(id=1))

        use_case = CreateProductUseCase(product_repo, category_repo)
        result = await use_case.execute(
            sku="PROD-001",
            name="Widget",
            unit_of_measure="unit",
            category_id=1,
        )

        assert result is not None
        product_repo.create.assert_awaited_once()

    async def test_raises_when_category_not_found(self) -> None:
        """Verifica que lanza ValueError si la categoria no existe."""
        category_repo = AsyncMock()
        category_repo.get_by_id = AsyncMock(return_value=None)
        product_repo = AsyncMock()

        use_case = CreateProductUseCase(product_repo, category_repo)

        with pytest.raises(ValueError, match=r"Category .* not found"):
            await use_case.execute(
                sku="PROD-001",
                name="Widget",
                unit_of_measure="unit",
                category_id=999,
            )

    async def test_raises_on_invalid_sku(self) -> None:
        """Verifica que lanza InvalidSKUError con SKU invalido."""
        category_repo = AsyncMock()
        category_repo.get_by_id = AsyncMock(return_value=MagicMock())
        product_repo = AsyncMock()

        use_case = CreateProductUseCase(product_repo, category_repo)

        with pytest.raises(InvalidSKUError):
            await use_case.execute(
                sku="PROD@001",
                name="Widget",
                unit_of_measure="unit",
                category_id=1,
            )

    async def test_raises_on_empty_name(self) -> None:
        """Verifica que lanza ValueError con nombre vacio."""
        category_repo = AsyncMock()
        category_repo.get_by_id = AsyncMock(return_value=MagicMock())
        product_repo = AsyncMock()

        use_case = CreateProductUseCase(product_repo, category_repo)

        with pytest.raises(ValueError):
            await use_case.execute(
                sku="PROD-001",
                name="",
                unit_of_measure="unit",
                category_id=1,
            )
