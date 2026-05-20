"""Tests unitarios para el value object SKU y su excepcion.

Valida que ``SKU`` es una dataclass frozen con validacion regex
y que ``InvalidSKUError`` hereda de ``DomainError``.

Ejemplo::

    pytest tests/unit/domain/test_sku.py -v
"""

from __future__ import annotations

import pytest


class TestSKU:
    """Tests para el value object SKU."""

    def test_valid_sku_with_hyphens(self) -> None:
        """Verifica que SKU acepta formato con guiones."""
        from src.domain.value_objects.sku import SKU

        sku = SKU("PROD-001")
        assert sku.value == "PROD-001"

    def test_valid_sku_with_underscores(self) -> None:
        """Verifica que SKU acepta formato con guiones bajos."""
        from src.domain.value_objects.sku import SKU

        sku = SKU("ITEM_42")
        assert sku.value == "ITEM_42"

    def test_valid_sku_alphanumeric(self) -> None:
        """Verifica que SKU acepta solo alfanumerico."""
        from src.domain.value_objects.sku import SKU

        sku = SKU("ABC123")
        assert sku.value == "ABC123"

    def test_empty_string_raises(self) -> None:
        """Verifica que SKU('') lanza InvalidSKUError."""
        from src.domain.exceptions.invalid_sku import InvalidSKUError
        from src.domain.value_objects.sku import SKU

        with pytest.raises(InvalidSKUError):
            SKU("")

    def test_too_long_raises(self) -> None:
        """Verifica que SKU de 51+ chars lanza InvalidSKUError."""
        from src.domain.exceptions.invalid_sku import InvalidSKUError
        from src.domain.value_objects.sku import SKU

        with pytest.raises(InvalidSKUError):
            SKU("a" * 51)

    def test_invalid_chars_raises(self) -> None:
        """Verifica que SKU con chars invalidos lanza InvalidSKUError."""
        from src.domain.exceptions.invalid_sku import InvalidSKUError
        from src.domain.value_objects.sku import SKU

        with pytest.raises(InvalidSKUError):
            SKU("invalid sku!")

    def test_sku_is_frozen(self) -> None:
        """Verifica que SKU es inmutable."""
        from dataclasses import FrozenInstanceError

        from src.domain.value_objects.sku import SKU

        sku = SKU("PROD-001")
        with pytest.raises(FrozenInstanceError):
            sku.value = "OTHER"  # type: ignore[misc]

    def test_max_length_50_accepted(self) -> None:
        """Verifica que SKU de 50 chars es valido."""
        from src.domain.value_objects.sku import SKU

        sku = SKU("a" * 50)
        assert sku.value == "a" * 50


class TestInvalidSKUError:
    """Tests para InvalidSKUError."""

    def test_inherits_from_domain_error(self) -> None:
        """Verifica que hereda de DomainError."""
        from src.domain.exceptions.domain_error import DomainError
        from src.domain.exceptions.invalid_sku import InvalidSKUError

        assert issubclass(InvalidSKUError, DomainError)


# ── Property-Based Tests (Hypothesis) ─────────────────────────────────────

from hypothesis import given

from tests.unit.strategies import invalid_sku_strategy, valid_sku_strategy


class TestSKUPropertyBased:
    """Property-based tests para SKU con Hypothesis."""

    @given(raw=valid_sku_strategy)
    def test_sku_accepts_all_valid_format_strings(self, raw: str) -> None:
        """Property: todo string que cumpla el regex crea un SKU válido."""
        from src.domain.value_objects.sku import SKU

        sku = SKU(value=raw)
        assert sku.value == raw

    @given(raw=invalid_sku_strategy)
    def test_sku_rejects_all_invalid_format_strings(self, raw: str) -> None:
        """Property: strings fuera del regex son rechazados."""
        from src.domain.exceptions.invalid_sku import InvalidSKUError
        from src.domain.value_objects.sku import SKU

        with pytest.raises(InvalidSKUError):
            SKU(value=raw)
