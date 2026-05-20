"""Tests unitarios para las reglas de negocio del dominio.

Valida las 4 funciones puras:
- ``calculate_stock_delta`` — calcula el delta de stock segun tipo
- ``validate_stock_not_negative`` — valida que no haya stock negativo
- ``enforce_immutability`` — valida que no se intente modificar
- ``validate_movement_type_consistency`` — valida metadata consistente

Ejemplo::

    pytest tests/unit/domain/test_rules.py -v
"""

from __future__ import annotations

import pytest
from hypothesis import given
from tests.unit.strategies import (
    current_stock_strategy,
    movement_type_strategy,
    product_id_strategy,
    valid_quantity_strategy,
)

from src.domain.exceptions.immutability_violation import (
    ImmutabilityViolationError,
)
from src.domain.exceptions.insufficient_stock import InsufficientStockError
from src.domain.rules.immutability import enforce_immutability
from src.domain.rules.movement_consistency import (
    validate_movement_type_consistency,
)
from src.domain.rules.stock_validation import (
    calculate_stock_delta,
    validate_stock_not_negative,
)
from src.domain.value_objects.movement_type import MovementType


class TestCalculateStockDelta:
    """Tests para calculate_stock_delta."""

    def test_in_adds_stock(self) -> None:
        """Verifica que IN produce delta positivo."""
        assert calculate_stock_delta(MovementType.IN, 10) == 10

    def test_out_subtracts_stock(self) -> None:
        """Verifica que OUT produce delta negativo."""
        assert calculate_stock_delta(MovementType.OUT, 10) == -10

    def test_adjustment_adds_stock(self) -> None:
        """Verifica que ADJUSTMENT produce delta positivo."""
        assert calculate_stock_delta(MovementType.ADJUSTMENT, 10) == 10

    def test_transfer_subtracts_stock(self) -> None:
        """Verifica que TRANSFER produce delta negativo (sale de origen)."""
        assert calculate_stock_delta(MovementType.TRANSFER, 10) == -10

    def test_with_float_quantity(self) -> None:
        """Verifica que funciona con cantidades decimales."""
        assert calculate_stock_delta(MovementType.IN, 1.5) == 1.5


class TestValidateStockNotNegative:
    """Tests para validate_stock_not_negative."""

    def test_out_with_sufficient_stock_passes(self) -> None:
        """Verifica que OUT con stock suficiente no lanza excepcion."""
        validate_stock_not_negative(MovementType.OUT, 5, 10, product_id=1)

    def test_out_with_insufficient_stock_raises(self) -> None:
        """Verifica que OUT con stock insuficiente lanza excepcion."""
        with pytest.raises(InsufficientStockError) as exc_info:
            validate_stock_not_negative(MovementType.OUT, 10, 5, product_id=1)
        assert exc_info.value.product_id == 1
        assert exc_info.value.requested == 10
        assert exc_info.value.available == 5

    def test_out_with_exact_stock_passes(self) -> None:
        """Verifica que OUT con stock exacto no lanza excepcion."""
        validate_stock_not_negative(MovementType.OUT, 10, 10, product_id=1)

    def test_in_never_raises(self) -> None:
        """Verifica que IN nunca lanza excepcion."""
        validate_stock_not_negative(MovementType.IN, 10, 0, product_id=1)

    def test_adjustment_never_raises(self) -> None:
        """Verifica que ADJUSTMENT nunca lanza excepcion."""
        validate_stock_not_negative(MovementType.ADJUSTMENT, 10, 0, product_id=1)

    def test_error_carries_product_id(self) -> None:
        """Verifica que InsufficientStockError lleva el product_id correcto."""
        with pytest.raises(InsufficientStockError) as exc_info:
            validate_stock_not_negative(MovementType.OUT, 10, 5, product_id=42)
        assert exc_info.value.product_id == 42


class TestEnforceImmutability:
    """Tests para enforce_immutability."""

    def test_valid_operation_passes(self) -> None:
        """Verifica que una operacion valida no lanza excepcion."""
        enforce_immutability(entity_type="Movement", entity_id=1, operation="create")

    def test_update_on_movement_raises(self) -> None:
        """Verifica que update en Movement lanza excepcion."""
        with pytest.raises(ImmutabilityViolationError) as exc_info:
            enforce_immutability(
                entity_type="Movement", entity_id=1, operation="update"
            )
        assert exc_info.value.entity_type == "Movement"
        assert exc_info.value.entity_id == 1

    def test_delete_on_movement_raises(self) -> None:
        """Verifica que delete en Movement lanza excepcion."""
        with pytest.raises(ImmutabilityViolationError) as exc_info:
            enforce_immutability(
                entity_type="Movement", entity_id=1, operation="delete"
            )
        assert exc_info.value.entity_type == "Movement"
        assert exc_info.value.entity_id == 1


class TestValidateMovementTypeConsistency:
    """Tests para validate_movement_type_consistency."""

    def test_transfer_with_origin_and_destination_passes(self) -> None:
        """Verifica que TRANSFER con metadata valido pasa."""
        validate_movement_type_consistency(
            MovementType.TRANSFER, {"origin": "A", "destination": "B"}
        )

    def test_transfer_without_origin_raises(self) -> None:
        """Verifica que TRANSFER sin origin lanza ValueError."""
        with pytest.raises(ValueError):
            validate_movement_type_consistency(
                MovementType.TRANSFER, {"destination": "B"}
            )

    def test_transfer_without_destination_raises(self) -> None:
        """Verifica que TRANSFER sin destination lanza ValueError."""
        with pytest.raises(ValueError):
            validate_movement_type_consistency(MovementType.TRANSFER, {"origin": "A"})

    def test_adjustment_with_reason_passes(self) -> None:
        """Verifica que ADJUSTMENT con reason pasa."""
        validate_movement_type_consistency(MovementType.ADJUSTMENT, {"reason": "count"})

    def test_adjustment_without_reason_raises(self) -> None:
        """Verifica que ADJUSTMENT sin reason lanza ValueError."""
        with pytest.raises(ValueError):
            validate_movement_type_consistency(MovementType.ADJUSTMENT, {})

    def test_in_with_empty_metadata_passes(self) -> None:
        """Verifica que IN con metadata vacio pasa."""
        validate_movement_type_consistency(MovementType.IN, {})

    def test_out_with_empty_metadata_passes(self) -> None:
        """Verifica que OUT con metadata vacio pasa."""
        validate_movement_type_consistency(MovementType.OUT, {})


# ── Property-Based Tests (Hypothesis) ─────────────────────────────────────


class TestCalculateStockDeltaPropertyBased:
    """Property-based tests para calculate_stock_delta con Hypothesis."""

    @given(
        mtype=movement_type_strategy,
        qty=valid_quantity_strategy,
    )
    def test_delta_sign_matches_movement_type(
        self, mtype: MovementType, qty: int
    ) -> None:
        """Property: IN/ADJUSTMENT -> delta positivo, OUT/TRANSFER -> negativo."""
        delta = calculate_stock_delta(mtype, qty)
        if mtype in (MovementType.IN, MovementType.ADJUSTMENT):
            assert delta > 0
            assert delta == qty
        else:
            assert delta < 0
            assert delta == -qty

    @given(qty=valid_quantity_strategy)
    def test_delta_never_zero_for_valid_quantity(self, qty: int) -> None:
        """Property: con cantidad valida (>0), el delta nunca es cero."""
        for mtype in MovementType:
            delta = calculate_stock_delta(mtype, qty)
            assert delta != 0


class TestValidateStockNotNegativePropertyBased:
    """Property-based tests para validate_stock_not_negative."""

    @given(
        mtype=movement_type_strategy,
        qty=valid_quantity_strategy,
        current=current_stock_strategy,
        pid=product_id_strategy,
    )
    def test_in_and_adjustment_never_raise(
        self, mtype: MovementType, qty: int, current: int, pid: int
    ) -> None:
        """Property: IN y ADJUSTMENT nunca lanzan InsufficientStockError."""
        if mtype in (MovementType.IN, MovementType.ADJUSTMENT):
            validate_stock_not_negative(mtype, qty, current, pid)

    @given(
        qty=valid_quantity_strategy,
        current=current_stock_strategy,
        pid=product_id_strategy,
    )
    def test_out_raises_when_quantity_exceeds_stock(
        self, qty: int, current: int, pid: int
    ) -> None:
        """Property: OUT con qty > current_stock siempre lanza error."""
        if qty > current:
            with pytest.raises(InsufficientStockError):
                validate_stock_not_negative(MovementType.OUT, qty, current, pid)
