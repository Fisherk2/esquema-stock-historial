"""Tests unitarios para el value object Quantity y su excepcion.

Valida que ``Quantity`` es una dataclass frozen que rechazca valores <= 0
y que ``InvalidQuantityError`` hereda de ``DomainError``.

Ejemplo::

    pytest tests/unit/domain/test_quantity.py -v
"""

from __future__ import annotations

import pytest


class TestQuantity:
    """Tests para el value object Quantity."""

    def test_valid_positive_quantity(self) -> None:
        """Verifica que Quantity acepta valores positivos."""
        from src.domain.value_objects.quantity import Quantity

        q = Quantity(10)
        assert q.value == 10

    def test_quantity_with_decimal(self) -> None:
        """Verifica que Quantity acepta valores decimales positivos."""
        from src.domain.value_objects.quantity import Quantity

        q = Quantity(1.5)
        assert q.value == 1.5

    def test_zero_raises_invalid_quantity_error(self) -> None:
        """Verifica que Quantity(0) lanza InvalidQuantityError."""
        from src.domain.exceptions.invalid_quantity import InvalidQuantityError
        from src.domain.value_objects.quantity import Quantity

        with pytest.raises(InvalidQuantityError):
            Quantity(0)

    def test_negative_raises_invalid_quantity_error(self) -> None:
        """Verifica que Quantity(-1) lanza InvalidQuantityError."""
        from src.domain.exceptions.invalid_quantity import InvalidQuantityError
        from src.domain.value_objects.quantity import Quantity

        with pytest.raises(InvalidQuantityError):
            Quantity(-1)

    def test_quantity_is_frozen(self) -> None:
        """Verifica que Quantity es inmutable (frozen dataclass)."""
        from dataclasses import FrozenInstanceError

        from src.domain.value_objects.quantity import Quantity

        q = Quantity(10)
        with pytest.raises(FrozenInstanceError):
            q.value = 20  # type: ignore[misc]


class TestInvalidQuantityError:
    """Tests para la excepcion InvalidQuantityError."""

    def test_inherits_from_domain_error(self) -> None:
        """Verifica que InvalidQuantityError hereda de DomainError."""
        from src.domain.exceptions.domain_error import DomainError
        from src.domain.exceptions.invalid_quantity import InvalidQuantityError

        assert issubclass(InvalidQuantityError, DomainError)

    def test_can_be_raised_and_caught(self) -> None:
        """Verifica que InvalidQuantityError se puede lanzar y capturar."""
        from src.domain.exceptions.domain_error import DomainError
        from src.domain.exceptions.invalid_quantity import InvalidQuantityError

        with pytest.raises(DomainError):
            raise InvalidQuantityError("test")


# ── Property-Based Tests (Hypothesis) ─────────────────────────────────────

from hypothesis import given

from tests.unit.strategies import (
    invalid_quantity_strategy,
    valid_quantity_strategy,
)


class TestQuantityPropertyBased:
    """Property-based tests para Quantity con Hypothesis."""

    @given(qty=valid_quantity_strategy)
    def test_quantity_accepts_all_positive_integers(self, qty: int) -> None:
        """Property: todo entero positivo crea un Quantity válido."""
        from src.domain.value_objects.quantity import Quantity

        q = Quantity(value=qty)
        assert q.value == qty

    @given(qty=invalid_quantity_strategy)
    def test_quantity_rejects_all_non_positive_integers(self, qty: int) -> None:
        """Property: ningún entero ≤ 0 debe crear un Quantity válido."""
        from src.domain.exceptions.invalid_quantity import InvalidQuantityError
        from src.domain.value_objects.quantity import Quantity

        with pytest.raises(InvalidQuantityError):
            Quantity(value=qty)
