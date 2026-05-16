"""Tests unitarios para la entidad Movement.

Valida que ``Movement`` es una dataclass frozen con los campos esperados,
validacion de metadata para TRANSFER/ADJUSTMENT, y ``__hash__ = None``.

Ejemplo::

    pytest tests/unit/domain/test_movement.py -v
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.domain.value_objects.movement_type import MovementType
from src.domain.value_objects.quantity import Quantity

_NOW = datetime.now(tz=UTC)


def _make_movement(**overrides: object) -> object:
    """Helper para crear un Movement con valores por defecto."""
    from src.domain.entities.movement import Movement

    defaults: dict[str, object] = {
        "id": None,
        "product_id": 1,
        "movement_type": MovementType.IN,
        "quantity": Quantity(10),
        "metadata": {},
        "created_at": _NOW,
        "reference": None,
    }
    defaults.update(overrides)
    return Movement(**defaults)  # type: ignore[arg-type]


class TestMovementConstruction:
    """Tests para la construccion de Movement."""

    def test_creates_movement_with_minimal_fields(self) -> None:
        """Verifica que Movement se crea con campos minimos."""
        m = _make_movement()
        assert m.product_id == 1  # type: ignore[attr-defined]
        assert m.movement_type == MovementType.IN  # type: ignore[attr-defined]
        assert m.quantity.value == 10  # type: ignore[attr-defined]

    def test_movement_has_all_required_fields(self) -> None:
        """Verifica que Movement tiene todos los campos requeridos."""
        m = _make_movement()
        assert hasattr(m, "id")  # type: ignore[attr-defined]
        assert hasattr(m, "product_id")  # type: ignore[attr-defined]
        assert hasattr(m, "movement_type")  # type: ignore[attr-defined]
        assert hasattr(m, "quantity")  # type: ignore[attr-defined]
        assert hasattr(m, "metadata")  # type: ignore[attr-defined]
        assert hasattr(m, "created_at")  # type: ignore[attr-defined]
        assert hasattr(m, "reference")  # type: ignore[attr-defined]

    def test_movement_accepts_optional_reference(self) -> None:
        """Verifica que Movement acepta reference opcional."""
        m = _make_movement(reference="REF-001")
        assert m.reference == "REF-001"  # type: ignore[attr-defined]

    def test_movement_accepts_metadata(self) -> None:
        """Verifica que Movement acepta metadata arbitrario."""
        m = _make_movement(metadata={"note": "test"})
        assert m.metadata == {"note": "test"}  # type: ignore[attr-defined]


class TestMovementMetadataValidation:
    """Tests para la validacion de metadata en Movement."""

    def test_transfer_requires_origin_and_destination(self) -> None:
        """Verifica que TRANSFER requiere origin y destination en metadata."""
        with pytest.raises(ValueError):
            _make_movement(
                movement_type=MovementType.TRANSFER,
                metadata={},
            )

    def test_transfer_with_valid_metadata_succeeds(self) -> None:
        """Verifica que TRANSFER con metadata valido se crea correctamente."""
        m = _make_movement(
            movement_type=MovementType.TRANSFER,
            metadata={"origin": "A", "destination": "B"},
        )
        assert m.movement_type == MovementType.TRANSFER  # type: ignore[attr-defined]

    def test_adjustment_requires_reason(self) -> None:
        """Verifica que ADJUSTMENT requiere reason en metadata."""
        with pytest.raises(ValueError):
            _make_movement(
                movement_type=MovementType.ADJUSTMENT,
                metadata={},
            )

    def test_adjustment_with_valid_metadata_succeeds(self) -> None:
        """Verifica que ADJUSTMENT con metadata valido se crea correctamente."""
        m = _make_movement(
            movement_type=MovementType.ADJUSTMENT,
            metadata={"reason": "inventory count"},
        )
        assert m.movement_type == MovementType.ADJUSTMENT  # type: ignore[attr-defined]

    def test_in_movement_does_not_require_metadata(self) -> None:
        """Verifica que IN no requiere metadata especial."""
        m = _make_movement(movement_type=MovementType.IN, metadata={})
        assert m.movement_type == MovementType.IN  # type: ignore[attr-defined]

    def test_out_movement_does_not_require_metadata(self) -> None:
        """Verifica que OUT no requiere metadata especial."""
        m = _make_movement(movement_type=MovementType.OUT, metadata={})
        assert m.movement_type == MovementType.OUT  # type: ignore[attr-defined]


class TestMovementImmutability:
    """Tests para la inmutabilidad de Movement."""

    def test_movement_is_frozen(self) -> None:
        """Verifica que Movement es inmutable (frozen dataclass)."""
        from dataclasses import FrozenInstanceError

        m = _make_movement()
        with pytest.raises(FrozenInstanceError):
            m.quantity = Quantity(5)  # type: ignore[misc]

    def test_movement_hash_is_none(self) -> None:
        """Verifica que Movement no es hashable (__hash__ = None)."""
        m = _make_movement()
        assert m.__hash__ is None  # type: ignore[attr-defined]


class TestMovementEquality:
    """Tests para la igualdad de Movement."""

    def test_movements_with_same_fields_are_equal(self) -> None:
        """Verifica que dos Movement con mismos campos son iguales."""
        m1 = _make_movement()
        m2 = _make_movement()
        assert m1 == m2  # type: ignore[attr-defined]

    def test_movements_with_different_id_are_not_equal(self) -> None:
        """Verifica que Movement con diferente id no son iguales."""
        m1 = _make_movement(id=1)
        m2 = _make_movement(id=2)
        assert m1 != m2  # type: ignore[attr-defined]
