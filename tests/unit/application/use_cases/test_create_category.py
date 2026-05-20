"""Tests unitarios para CreateCategoryUseCase."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.use_cases.create_category import CreateCategoryUseCase


class TestCreateCategoryUseCase:
    """Tests para CreateCategoryUseCase."""

    async def test_creates_category(self) -> None:
        """Verifica que crea una categoria correctamente."""
        category_repo = AsyncMock()
        category_repo.create = AsyncMock(return_value=MagicMock(id=1))

        use_case = CreateCategoryUseCase(category_repo)
        result = await use_case.execute(
            name="Electronics",
            description="Electronic products",
        )

        assert result is not None
        category_repo.create.assert_awaited_once()

    async def test_raises_on_empty_name(self) -> None:
        """Verifica que lanza ValueError con nombre vacio."""
        category_repo = AsyncMock()

        use_case = CreateCategoryUseCase(category_repo)

        with pytest.raises(ValueError, match="Category name cannot be empty"):
            await use_case.execute(name="")
