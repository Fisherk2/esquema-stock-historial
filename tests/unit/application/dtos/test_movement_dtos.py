"""Tests para DTOs de movimientos."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.application.dtos.movement_dtos import (
    CreateMovementInput,
    MovementListOutput,
    MovementOutput,
)
from src.domain.value_objects.movement_type import MovementType


class TestCreateMovementInput:
    """Tests para CreateMovementInput."""

    def test_valid_in_movement(self) -> None:
        """Verifica que crea un input IN valido."""
        body = CreateMovementInput(
            product_id=1,
            movement_type=MovementType.IN,
            quantity=10,
            metadata={"supplier": "ACME"},
        )
        assert body.product_id == 1
        assert body.movement_type == MovementType.IN
        assert body.quantity == 10

    def test_valid_out_movement(self) -> None:
        """Verifica que crea un input OUT valido."""
        body = CreateMovementInput(
            product_id=1,
            movement_type=MovementType.OUT,
            quantity=5,
        )
        assert body.quantity == 5

    def test_transfer_requires_origin_destination(self) -> None:
        """Verifica que TRANSFER requiere origin y destination."""
        with pytest.raises(ValidationError):
            CreateMovementInput(
                product_id=1,
                movement_type=MovementType.TRANSFER,
                quantity=5,
                metadata={"origin": "A"},
            )

    def test_transfer_with_origin_destination_passes(self) -> None:
        """Verifica que TRANSFER con origin y destination pasa."""
        body = CreateMovementInput(
            product_id=1,
            movement_type=MovementType.TRANSFER,
            quantity=5,
            metadata={"origin": "A", "destination": "B"},
        )
        assert body.metadata["origin"] == "A"

    def test_adjustment_requires_reason(self) -> None:
        """Verifica que ADJUSTMENT requiere reason."""
        with pytest.raises(ValidationError):
            CreateMovementInput(
                product_id=1,
                movement_type=MovementType.ADJUSTMENT,
                quantity=5,
                metadata={},
            )

    def test_adjustment_with_reason_passes(self) -> None:
        """Verifica que ADJUSTMENT con reason pasa."""
        body = CreateMovementInput(
            product_id=1,
            movement_type=MovementType.ADJUSTMENT,
            quantity=5,
            metadata={"reason": "inventory count"},
        )
        assert body.metadata["reason"] == "inventory count"

    def test_rejects_zero_quantity(self) -> None:
        """Verifica que rechaza quantity=0."""
        with pytest.raises(ValidationError):
            CreateMovementInput(
                product_id=1,
                movement_type=MovementType.IN,
                quantity=0,
            )

    def test_rejects_negative_quantity(self) -> None:
        """Verifica que rechaza quantity negativa."""
        with pytest.raises(ValidationError):
            CreateMovementInput(
                product_id=1,
                movement_type=MovementType.IN,
                quantity=-5,
            )

    def test_rejects_zero_product_id(self) -> None:
        """Verifica que rechaza product_id=0."""
        with pytest.raises(ValidationError):
            CreateMovementInput(
                product_id=0,
                movement_type=MovementType.IN,
                quantity=10,
            )

    def test_default_metadata_is_empty_dict(self) -> None:
        """Verifica que metadata por defecto es dict vacio."""
        body = CreateMovementInput(
            product_id=1,
            movement_type=MovementType.IN,
            quantity=10,
        )
        assert body.metadata == {}


class TestMovementOutput:
    """Tests para MovementOutput."""

    def test_serializes_to_json(self) -> None:
        """Verifica que serializa a JSON valido."""
        output = MovementOutput(
            id=1,
            product_id=2,
            movement_type="IN",
            quantity=10,
            metadata={"supplier": "ACME"},
            reference="PO-123",
            created_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        )
        json_str = output.model_dump_json()
        assert '"id":1' in json_str
        assert '"product_id":2' in json_str


class TestMovementListOutput:
    """Tests para MovementListOutput."""

    def test_contains_pagination_fields(self) -> None:
        """Verifica que contiene campos de paginacion."""
        output = MovementListOutput(
            items=[],
            total=100,
            limit=50,
            offset=0,
        )
        assert output.total == 100
        assert output.limit == 50
        assert output.offset == 0
