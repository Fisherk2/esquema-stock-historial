"""Tests unitarios para los ports de repositorio.

Valida que las clases mock satisfacen los Protocolos ``IMovementRepository``
e ``IStockQueryRepository`` en runtime (runtime_checkable).

Ejemplo::

    pytest tests/unit/domain/test_ports.py -v
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from src.domain.entities.movement import Movement


class TestIMovementRepository:
    """Tests para IMovementRepository Protocol."""

    def test_protocol_has_required_methods(self) -> None:
        """Verifica que el Protocol tiene los metodos esperados."""
        from src.domain.ports.movement_repository import IMovementRepository

        assert hasattr(IMovementRepository, "create")
        assert hasattr(IMovementRepository, "get_by_id")
        assert hasattr(IMovementRepository, "list_by_product")

    def test_protocol_has_no_update_or_delete(self) -> None:
        """Verifica que el Protocol NO tiene update ni delete."""
        from src.domain.ports.movement_repository import IMovementRepository

        assert not hasattr(IMovementRepository, "update")
        assert not hasattr(IMovementRepository, "delete")

    def test_mock_satisfies_protocol_at_runtime(self) -> None:
        """Verifica que una implementacion mock satisface el Protocol."""
        from src.domain.ports.movement_repository import IMovementRepository

        class MockMovementRepository:
            async def create(self, movement: Movement) -> Movement:
                return movement

            async def get_by_id(self, movement_id: int) -> Movement | None:
                return None

            async def list_by_product(
                self,
                product_id: int,
                limit: int = 100,
                offset: int = 0,
            ) -> list[Movement]:
                return []

        mock = MockMovementRepository()
        assert isinstance(mock, IMovementRepository)


class TestIStockQueryRepository:
    """Tests para IStockQueryRepository Protocol."""

    def test_protocol_has_required_methods(self) -> None:
        """Verifica que el Protocol tiene los metodos esperados."""
        from src.domain.ports.stock_query_repository import IStockQueryRepository

        assert hasattr(IStockQueryRepository, "get_current_stock")
        assert hasattr(IStockQueryRepository, "get_stock_at_date")

    def test_mock_satisfies_protocol_at_runtime(self) -> None:
        """Verifica que una implementacion mock satisface el Protocol."""
        from datetime import datetime  # noqa: F401 — used in annotation

        from src.domain.ports.stock_query_repository import IStockQueryRepository

        class MockStockQueryRepository:
            async def get_current_stock(self, product_id: int) -> float:
                return 0.0

            async def get_stock_at_date(self, product_id: int, date: datetime) -> float:
                return 0.0

        mock = MockStockQueryRepository()
        assert isinstance(mock, IStockQueryRepository)
