"""Tests unitarios para ICategoryRepository Protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.category import Category


class TestICategoryRepository:
    """Tests para ICategoryRepository Protocol."""

    def test_protocol_has_required_methods(self) -> None:
        """Verifica que el Protocol tiene los 3 metodos esperados."""
        from src.domain.ports.category_repository import ICategoryRepository

        assert hasattr(ICategoryRepository, "create")
        assert hasattr(ICategoryRepository, "get_by_id")
        assert hasattr(ICategoryRepository, "list_all")

    def test_mock_satisfies_protocol_at_runtime(self) -> None:
        """Verifica que una implementacion mock satisface el Protocol."""
        from src.domain.ports.category_repository import ICategoryRepository

        class MockCategoryRepository:
            async def create(self, category: Category) -> Category:
                return category

            async def get_by_id(self, category_id: int) -> Category | None:
                return None

            async def list_all(self) -> list[Category]:
                return []

        mock = MockCategoryRepository()
        assert isinstance(mock, ICategoryRepository)
