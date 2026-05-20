"""Tests unitarios para ListProductsUseCase."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from src.application.use_cases.list_products import ListProductsUseCase


class TestListProductsUseCase:
    """Tests para ListProductsUseCase."""

    async def test_returns_items_and_total(self) -> None:
        """Verifica que retorna tupla (items, total)."""
        product_repo = AsyncMock()
        product_repo.list_all = AsyncMock(return_value=[MagicMock(), MagicMock()])
        product_repo.count_all = AsyncMock(return_value=85)

        use_case = ListProductsUseCase(product_repo)
        items, total = await use_case.execute(limit=50, offset=0)

        assert len(items) == 2
        assert total == 85
        product_repo.list_all.assert_awaited_once_with(limit=50, offset=0)
        product_repo.count_all.assert_awaited_once()

    async def test_returns_empty_list(self) -> None:
        """Verifica que retorna lista vacia cuando no hay productos."""
        product_repo = AsyncMock()
        product_repo.list_all = AsyncMock(return_value=[])
        product_repo.count_all = AsyncMock(return_value=0)

        use_case = ListProductsUseCase(product_repo)
        items, total = await use_case.execute()

        assert items == []
        assert total == 0

    async def test_returns_empty_list_when_offset_exceeds_total(self) -> None:
        """Edge case: offset mayor al total de productos retorna lista vacia."""
        product_repo = AsyncMock()
        product_repo.list_all = AsyncMock(return_value=[])
        product_repo.count_all = AsyncMock(return_value=5)

        use_case = ListProductsUseCase(product_repo)
        items, total = await use_case.execute(limit=10, offset=100)

        assert items == []
        assert total == 5

    async def test_returns_empty_list_when_limit_is_one(self) -> None:
        """Edge case: limit=1 retorna un solo producto."""
        product_repo = AsyncMock()
        product_repo.list_all = AsyncMock(return_value=[MagicMock()])
        product_repo.count_all = AsyncMock(return_value=50)

        use_case = ListProductsUseCase(product_repo)
        items, total = await use_case.execute(limit=1, offset=0)

        assert len(items) == 1
        assert total == 50
