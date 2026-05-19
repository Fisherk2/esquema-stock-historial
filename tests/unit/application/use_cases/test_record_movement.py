"""Tests unitarios para RecordMovementUseCase."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.use_cases.record_movement import RecordMovementUseCase
from src.domain.exceptions.insufficient_stock import InsufficientStockError
from src.domain.value_objects.movement_type import MovementType


@pytest.fixture
def movement_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.create = AsyncMock()
    return repo


@pytest.fixture
def product_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def stock_query_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def unit_of_work() -> AsyncMock:
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    return uow


@pytest.fixture
def use_case(
    movement_repo: AsyncMock,
    product_repo: AsyncMock,
    stock_query_repo: AsyncMock,
    unit_of_work: AsyncMock,
) -> RecordMovementUseCase:
    return RecordMovementUseCase(
        movement_repo, product_repo, stock_query_repo, unit_of_work
    )


class TestRecordMovementUseCase:
    """Tests para RecordMovementUseCase."""

    async def test_in_creates_movement_without_stock_check(
        self,
        use_case: RecordMovementUseCase,
        movement_repo: AsyncMock,
        product_repo: AsyncMock,
        stock_query_repo: AsyncMock,
    ) -> None:
        """Verifica que IN crea movimiento sin validar stock."""
        product = MagicMock()
        product_repo.get_by_id = AsyncMock(return_value=product)
        movement_repo.create = AsyncMock(
            return_value=MagicMock(
                id=1, product_id=1, movement_type=MovementType.IN, metadata={}
            )
        )

        result = await use_case.execute(
            product_id=1,
            movement_type=MovementType.IN,
            quantity=10,
            metadata={"supplier": "ACME"},
            reference="PO-123",
        )

        assert result is not None
        stock_query_repo.get_current_stock.assert_not_called()
        product_repo.get_by_id.assert_awaited_once_with(1)
        movement_repo.create.assert_awaited_once()

    async def test_out_validates_stock(
        self,
        use_case: RecordMovementUseCase,
        movement_repo: AsyncMock,
        product_repo: AsyncMock,
        stock_query_repo: AsyncMock,
    ) -> None:
        """Verifica que OUT valida stock suficiente."""
        product_repo.get_by_id = AsyncMock(return_value=MagicMock())
        stock_query_repo.get_current_stock = AsyncMock(return_value=20)

        await use_case.execute(
            product_id=1,
            movement_type=MovementType.OUT,
            quantity=5,
            metadata={},
        )

        assert stock_query_repo.get_current_stock.await_count >= 1

    async def test_out_raises_insufficient_stock(
        self,
        use_case: RecordMovementUseCase,
        product_repo: AsyncMock,
        stock_query_repo: AsyncMock,
    ) -> None:
        """Verifica que OUT lanza InsufficientStockError si no hay stock."""
        product_repo.get_by_id = AsyncMock(return_value=MagicMock())
        stock_query_repo.get_current_stock = AsyncMock(return_value=3)

        with pytest.raises(InsufficientStockError) as exc_info:
            await use_case.execute(
                product_id=1,
                movement_type=MovementType.OUT,
                quantity=10,
                metadata={},
            )
        assert exc_info.value.product_id == 1
        assert exc_info.value.requested == 10
        assert exc_info.value.available == 3

    async def test_product_not_found_raises_value_error(
        self, use_case: RecordMovementUseCase, product_repo: AsyncMock
    ) -> None:
        """Verifica que lanza ValueError si el producto no existe."""
        product_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match=r"Product .* not found"):
            await use_case.execute(
                product_id=999,
                movement_type=MovementType.IN,
                quantity=10,
                metadata={},
            )

    async def test_transfer_requires_origin_and_destination(
        self,
        use_case: RecordMovementUseCase,
        product_repo: AsyncMock,
        stock_query_repo: AsyncMock,
    ) -> None:
        """Verifica que TRANSFER requiere origin y destination en metadata."""
        product_repo.get_by_id = AsyncMock(return_value=MagicMock())
        stock_query_repo.get_current_stock = AsyncMock(return_value=100)

        with pytest.raises(ValueError, match=r"TRANSFER.*origin.*destination"):
            await use_case.execute(
                product_id=1,
                movement_type=MovementType.TRANSFER,
                quantity=5,
                metadata={"origin": "A"},
            )

    async def test_adjustment_requires_reason(
        self, use_case: RecordMovementUseCase, product_repo: AsyncMock
    ) -> None:
        """Verifica que ADJUSTMENT requiere reason en metadata."""
        product_repo.get_by_id = AsyncMock(return_value=MagicMock())

        with pytest.raises(ValueError, match=r"ADJUSTMENT.*reason"):
            await use_case.execute(
                product_id=1,
                movement_type=MovementType.ADJUSTMENT,
                quantity=5,
                metadata={},
            )

    async def test_uses_unit_of_work_for_out(
        self,
        use_case: RecordMovementUseCase,
        movement_repo: AsyncMock,
        product_repo: AsyncMock,
        stock_query_repo: AsyncMock,
        unit_of_work: AsyncMock,
    ) -> None:
        """Verifica que OUT usa UoW para atomicidad."""
        product_repo.get_by_id = AsyncMock(return_value=MagicMock())
        stock_query_repo.get_current_stock = AsyncMock(return_value=20)

        await use_case.execute(
            product_id=1,
            movement_type=MovementType.OUT,
            quantity=5,
            metadata={},
        )

        unit_of_work.__aenter__.assert_awaited_once()
        unit_of_work.__aexit__.assert_awaited_once()

    async def test_transfer_validates_stock(
        self,
        use_case: RecordMovementUseCase,
        product_repo: AsyncMock,
        stock_query_repo: AsyncMock,
    ) -> None:
        """Verifica que TRANSFER valida stock (como OUT)."""
        product_repo.get_by_id = AsyncMock(return_value=MagicMock())
        stock_query_repo.get_current_stock = AsyncMock(return_value=2)

        with pytest.raises(InsufficientStockError):
            await use_case.execute(
                product_id=1,
                movement_type=MovementType.TRANSFER,
                quantity=10,
                metadata={"origin": "A", "destination": "B"},
            )
