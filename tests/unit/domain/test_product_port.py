"""Tests unitarios para IProductRepository Protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.product import Product


class TestIProductRepository:
    """Tests para IProductRepository Protocol."""

    def test_protocol_has_required_methods(self) -> None:
        """Verifica que el Protocol tiene los 5 metodos esperados."""
        from src.domain.ports.product_repository import IProductRepository

        assert hasattr(IProductRepository, "create")
        assert hasattr(IProductRepository, "get_by_id")
        assert hasattr(IProductRepository, "get_by_sku")
        assert hasattr(IProductRepository, "list_all")
        assert hasattr(IProductRepository, "list_below_threshold")

    def test_mock_satisfies_protocol_at_runtime(self) -> None:
        """Verifica que una implementacion mock satisface el Protocol."""
        from src.domain.ports.product_repository import IProductRepository

        class MockProductRepository:
            async def create(self, product: Product) -> Product:
                return product

            async def get_by_id(self, product_id: int) -> Product | None:
                return None

            async def get_by_sku(self, sku: str) -> Product | None:
                return None

            async def list_all(
                self, *, limit: int = 100, offset: int = 0
            ) -> list[Product]:
                return []

            async def count_all(self) -> int:
                return 0

            async def list_below_threshold(self, *, limit: int = 100) -> list[Product]:
                return []

        mock = MockProductRepository()
        assert isinstance(mock, IProductRepository)
