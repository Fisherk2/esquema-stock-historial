"""Tests unitarios para el value object MovementType.

Valida que ``MovementType`` es un Enum con los 4 valores esperados
que mapean 1:1 al ENUM de PostgreSQL.

Ejemplo::

    pytest tests/unit/domain/test_movement_type.py -v
"""

from __future__ import annotations


def test_movement_type_has_four_values() -> None:
    """Verifica que MovementType tiene exactamente 4 valores."""
    from src.domain.value_objects.movement_type import MovementType

    assert len(MovementType) == 4


def test_movement_type_in_value() -> None:
    """Verifica que MovementType.IN.value == 'IN'."""
    from src.domain.value_objects.movement_type import MovementType

    assert MovementType.IN.value == "IN"


def test_movement_type_out_value() -> None:
    """Verifica que MovementType.OUT.value == 'OUT'."""
    from src.domain.value_objects.movement_type import MovementType

    assert MovementType.OUT.value == "OUT"


def test_movement_type_adjustment_value() -> None:
    """Verifica que MovementType.ADJUSTMENT.value == 'ADJUSTMENT'."""
    from src.domain.value_objects.movement_type import MovementType

    assert MovementType.ADJUSTMENT.value == "ADJUSTMENT"


def test_movement_type_transfer_value() -> None:
    """Verifica que MovementType.TRANSFER.value == 'TRANSFER'."""
    from src.domain.value_objects.movement_type import MovementType

    assert MovementType.TRANSFER.value == "TRANSFER"


def test_movement_type_is_enum() -> None:
    """Verifica que MovementType es una subclase de Enum."""
    from enum import Enum

    from src.domain.value_objects.movement_type import MovementType

    assert issubclass(MovementType, Enum)
